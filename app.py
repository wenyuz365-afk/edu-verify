"""
校招学历 AI 核验系统 v3 — 三步流 + 总表 + 详情
"""
import streamlit as st
import tempfile, zipfile, time, uuid
from pathlib import Path
from datetime import datetime
import pypdfium2 as pdfium
import pandas as pd
import shutil

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

def save_cert_copy(src_path, candidate_name, label):
    """保存证书副本到持久目录"""
    folder = UPLOAD_DIR / candidate_name
    folder.mkdir(exist_ok=True)
    ext = Path(src_path).suffix
    dst = folder / f"{label}{ext}"
    shutil.copy2(src_path, dst)
    return str(dst)

from database import create_database, save_verify_record, upsert_candidate, get_all_candidates, update_candidate_status
from ocr_engine import get_ocr_engine
from field_extractor import get_field_extractor
from verifier import verify_all_certs, AlertLevel

st.set_page_config(page_title="学历AI核验系统", page_icon="🎓", layout="wide")

@st.cache_resource
def init(): create_database(); return get_ocr_engine(), get_field_extractor()
ocr_engine, field_extractor = init()

LEVELS = ["本科", "硕士研究生", "博士研究生"]

def _level_sort(l): return {"本科":1,"硕士研究生":2,"博士研究生":3}.get(l,0)

def icon_for(level):
    if hasattr(level, 'value'): level = level.value
    return {"PASS":"✅","REVIEW":"⚠️","ALERT":"🚨"}.get(str(level),"?")

def level_is_pass(level):
    """判断是否为PASS，兼容enum和字符串"""
    if hasattr(level, 'value'): return level.value == 'PASS'
    return str(level) == 'PASS'

def pdf_to_image(p):
    pdf=pdfium.PdfDocument(p); pg=pdf[0]; b=pg.render(scale=2); img=b.to_pil()
    o=str(Path(p).with_suffix(".png")); img.save(o); pg.close(); pdf.close(); return o

def prep(p): return pdf_to_image(p) if Path(p).suffix.lower()==".pdf" else p

def ocr_and_extract(fp):
    inp=prep(fp); ocr=ocr_engine.recognize(inp); f=field_extractor.extract(ocr["full_text"], use_llm=True)
    d=f.__dict__ if hasattr(f,'__dict__') else f
    d["_ocr_text"]=ocr["full_text"]; d["_ocr_conf"]=ocr["average_confidence"]; d["_img"]=fp; return d

def _classify_file(name):
    nl=name.lower(); level="本科"
    if "硕士" in name or "master" in nl: level="硕士研究生"
    elif "博士" in name or "phd" in nl or "doctor" in nl: level="博士研究生"
    elif "专科" in name or "大专" in name: level="专科"
    return level, ("学位" in name or "degree" in nl), ("简历" in name or "resume" in nl or "cv" in nl)

# ─── 批量处理函数 ───
def _process_batch(batch_zip, recruitment_type):
    candidates={}
    if batch_zip:
        with zipfile.ZipFile(batch_zip) as zf:
            names=zf.namelist()
            # 检测是否有顶层包装文件夹，若有则跳过
            top_dirs=set()
            for name in names:
                parts=name.split("/")
                if len(parts)>1 and parts[0] and not parts[0].startswith("__"):
                    top_dirs.add(parts[0])
            has_wrapper=len(top_dirs)==1 and all(
                n.split("/")[0]==list(top_dirs)[0] for n in names if "/" in n and not n.startswith("__")
            )
            for name in names:
                ext=Path(name).suffix.lower()
                if ext not in [".jpg",".jpeg",".png",".pdf"] or name.startswith("__"): continue
                parts=name.split("/")
                if has_wrapper and len(parts)>2:
                    folder=parts[1]  # 跳过顶层wrapper
                else:
                    folder=parts[-2] if len(parts)>1 else parts[0].rsplit(".",1)[0]
                if not folder or folder.startswith("__"): continue
                if folder not in candidates: candidates[folder]=[]
                data=zf.read(name)
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(data); candidates[folder].append((name,tmp.name))

    if not candidates: st.error("未找到有效文件"); return

    st.subheader(f"📦 批量核验 — {len(candidates)}位候选人")
    prog=st.progress(0); stat=st.empty()
    batch_results=[]

    for idx,(folder,files) in enumerate(candidates.items()):
        stat.text(f"({idx+1}/{len(candidates)}) {folder}")
        prog.progress((idx+1)/len(candidates))
        cgroups={}; rp=None
        for fn,fp in files:
            lvl,is_deg,is_res=_classify_file(fn)
            if is_res: rp=fp; continue
            if lvl not in cgroups: cgroups[lvl]={"level":lvl,"degree_img":"","grad_img":"","degree_fields":None,"grad_fields":None}
            if is_deg: cgroups[lvl]["degree_img"]=fp
            else: cgroups[lvl]["grad_img"]=fp
        clist=[g for g in cgroups.values() if g["degree_img"] or g["grad_img"]]
        if not clist: continue
        for cg in clist:
            if cg["degree_img"]: cg["degree_fields"]=ocr_and_extract(cg["degree_img"])
            if cg["grad_img"]: cg["grad_fields"]=ocr_and_extract(cg["grad_img"])
        re=None
        if rp:
            try: rf=ocr_and_extract(rp); re=field_extractor.extract_resume_education(rf.get("_ocr_text",""))
            except: pass
        res=verify_all_certs(clist,re,recruitment_type)
        cn=folder; cs=""
        for cg in clist:
            for f in [cg.get("degree_fields"),cg.get("grad_fields")]:
                if f and f.get("name"): cn=f["name"]
                if f and f.get("school"): cs=f["school"]
            if cn!=folder: break
        batch_results.append({
            "name":cn,"folder":folder,"school":cs,
            "levels":", ".join(cg["level"] for cg in clist),
            "result":res["final"].value,"summary":res["final_summary"],
            "_res":res,"_clist":clist  # 保留详情用于展开
        })
        hi=max((cg["level"] for cg in clist),key=_level_sort,default="本科")
        if res["final"]==AlertLevel.PASS: upsert_candidate(cn,cs,"",hi,"pass","pass","pass",recruitment_type,reviewed=1)
        else:
            ds="pass" if all(r.get("degree_pass",True) for r in res["group_results"] if r.get("degree_result")) else "fail"
            gs="pass" if all(r.get("grad_pass",True) for r in res["group_results"] if r.get("grad_result")) else "fail"
            upsert_candidate(cn,cs,"",hi,ds,gs,"",recruitment_type,reviewed=0)
    prog.empty(); stat.empty()

    # 存入session_state, 在页面主体区域渲染
    st.session_state.batch_results=batch_results
    st.session_state.show_batch=True
    st.rerun()


# ═══════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════
with st.sidebar:
    st.title("🎓 学历核验系统")
    mode=st.radio("模式",["📤 上传核验","📋 人工核验台","📊 数据看板"])
    st.markdown("---")
    st.caption("Demo | 583国内+191海外 | 曾用名 | 包含匹配")

# ═══════════════════════════════════════════
# 模式1: 上传核验（三步流）
# ═══════════════════════════════════════════
if mode=="📤 上传核验":
    st.title("📤 学历证书核验")

    # ─── 批量结果展示 ───
    if st.session_state.get('show_batch') and st.session_state.get('batch_results'):
        batch_results = st.session_state.batch_results
        st.success(f"批量核验完成 — {len(batch_results)}位候选人")
        df = pd.DataFrame([{k:v for k,v in r.items() if not k.startswith('_')} for r in batch_results])
        def bclr(v):
            if v == 'PASS': return 'background-color:#d4edda'
            if v == 'REVIEW': return 'background-color:#fff3cd'
            return 'background-color:#f8d7da'
        st.dataframe(df.style.map(bclr, subset=['result']), use_container_width=True, hide_index=True)
        st.download_button('📥 导出CSV', df.to_csv(index=False).encode('utf-8-sig'),
            f"批量核验_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
        st.markdown('---')
        st.subheader('🔍 逐人详情')
        for r in batch_results:
            res = r['_res']; final = res['final']
            icons = {AlertLevel.PASS:'✅', AlertLevel.REVIEW:'⚠️', AlertLevel.ALERT:'🚨'}
            with st.expander(f"{icons[final]} {r['name']} | {r['school']} | {r['levels']} | {r['result']}", expanded=final != AlertLevel.PASS):
                sr = []
                for gr in res['group_results']:
                    do = gr.get('degree_result'); go = gr.get('grad_result')
                    def iok(v):
                        if v is None: return '—'
                        return '✅' if v else '❌'
                    sr.append({'学历层级': gr['level'], '学位证': iok(gr['degree_pass'] if do else None), '毕业证': iok(gr['grad_pass'] if go else None), '双证比对': '✅' if gr.get('cross_ok', True) else '❌', '判定': '✅ 通过' if gr['level_pass'] else '⚠️ 需复核'})
                if sr: st.dataframe(pd.DataFrame(sr), use_container_width=True, hide_index=True)
                for gr in res['group_results']:
                    do = gr.get('degree_result'); go = gr.get('grad_result')
                    if do:
                        st.markdown(f"🎓 学位证 — *{do.summary}*")
                        for c in do.checks: st.caption(f"  {icon_for(c['level'])} {c['name']}: {c['message']}")
                    if go:
                        st.markdown(f"📜 毕业证 — *{go.summary}*")
                        for c in go.checks: st.caption(f"  {icon_for(c['level'])} {c['name']}: {c['message']}")
                    if do and go and gr.get('cross_items'):
                        for c in gr['cross_items']: st.caption(f"  {{'PASS':'✅','REVIEW':'⚠️','ALERT':'🚨'}}.get(c['level'],'?') 🔗 {c['name']}: {c['message']}")
                if res.get('resume_checks'):
                    st.markdown('**📋 简历交叉验证**')
                    for c in res['resume_checks']: st.write(f"{icon_for(c['level'])} {c['name']}: {c['message']}")
        if st.button('🔄 核验下一批', use_container_width=True):
            st.session_state.show_batch=False; st.session_state.batch_results=None
            st.session_state.verify_step=1; st.rerun()
        st.stop()

    if "verify_step" not in st.session_state: st.session_state.verify_step=1

    # ─── Step 1: 选择场景 ───
    if st.session_state.verify_step==1:
        rt=st.session_state.get("recruitment_type","校招")
        st.markdown("### Step 1/2 — 上传材料")
        # 招聘类型选择
        rt_choice=st.radio("招聘类型",["🎓 校招","💼 社招","📝 实习"],horizontal=True,
            index=0 if rt=="校招" else (1 if rt=="社招" else 2),
            captions=["有证验真伪，无证→待取证","所有学历必须有证，缺证→不通过","已毕业学历缺证→不通过，在读→跳过"])
        st.session_state.recruitment_type="校招" if "校招" in rt_choice else ("社招" if "社招" in rt_choice else "实习")
        rt=st.session_state.recruitment_type
        st.markdown("---")

        um=st.radio("上传模式",["👤 单个候选人","📦 批量候选人"],horizontal=True)

        if um=="👤 单个候选人":
            if "degree_groups" not in st.session_state:
                st.session_state.degree_groups=[{"id":str(uuid.uuid4()),"level":"本科"}]
            for i,g in enumerate(st.session_state.degree_groups):
                with st.expander(f"学历层次 #{i+1}",expanded=True):
                    c1,c2,c3=st.columns([2,3,3])
                    with c1: g["level"]=st.selectbox("学历层次",LEVELS,index=LEVELS.index(g["level"]) if g["level"] in LEVELS else 0,key=f"lv_{g['id']}")
                    with c2: st.file_uploader("学位证书",type=["jpg","jpeg","png","pdf"],key=f"deg_{g['id']}")
                    with c3: st.file_uploader("毕业证书（可选）",type=["jpg","jpeg","png","pdf"],key=f"grad_{g['id']}")
                    if len(st.session_state.degree_groups)>1:
                        if st.button("🗑 删除",key=f"del_{g['id']}"):
                            st.session_state.degree_groups=[gg for gg in st.session_state.degree_groups if gg["id"]!=g["id"]]; st.rerun()
            if st.button("➕ 添加学历",disabled=len(st.session_state.degree_groups)>=3):
                st.session_state.degree_groups.append({"id":str(uuid.uuid4()),"level":"硕士研究生"}); st.rerun()
            st.markdown("---")
            resume_file=st.file_uploader("📋 简历 (必传)",type=["jpg","jpeg","png","pdf"],key="resume_single")
            batch_info=None
        else:
            st.caption("每个子文件夹=一位候选人，文件夹名=候选人姓名，文件按关键词自动分类")
            st.caption("```\n候选人材料.zip\n├── 张三/\n│   ├── 本科学位证.jpg\n│   ├── 本科毕业证.jpg\n│   └── 简历.pdf\n├── 李四/\n│   ├── 硕士学位证.jpg\n│   └── 硕士毕业证.jpg\n```")
            batch_zip=st.file_uploader("上传ZIP压缩包",type=["zip"],key="bzip")
            batch_info={"zip":batch_zip}
            resume_file=None
            if "degree_groups" not in st.session_state: st.session_state.degree_groups=[{"id":str(uuid.uuid4()),"level":"本科"}]

        if st.button("🚀 开始核验",type="primary",use_container_width=True):
            if um=="📦 批量候选人" and batch_info and batch_info.get("zip"):
                _process_batch(batch_info["zip"],rt); st.stop()

            cert_groups=[]; tmp_paths=[]
            for g in st.session_state.degree_groups:
                dk=f"deg_{g['id']}"; gk=f"grad_{g['id']}"
                df=st.session_state.get(dk); gf=st.session_state.get(gk)
                if not df and not gf: continue
                di=""; gi=""
                if df:
                    with tempfile.NamedTemporaryFile(delete=False,suffix=Path(df.name).suffix) as t: t.write(df.read()); di=t.name; tmp_paths.append(di)
                if gf:
                    with tempfile.NamedTemporaryFile(delete=False,suffix=Path(gf.name).suffix) as t: t.write(gf.read()); gi=t.name; tmp_paths.append(gi)
                cert_groups.append({"level":g["level"],"degree_img":di,"grad_img":gi,"degree_fields":None,"grad_fields":None})
            if not cert_groups: st.error("请至少上传一组证书"); st.stop()

            # 保存证书副本到持久目录(供人工核验台查看)
            cert_save_name = f"temp_{uuid.uuid4().hex[:8]}"
            for cg in cert_groups:
                if cg["degree_img"]: save_cert_copy(cg["degree_img"], cert_save_name, f"{cg['level']}_学位证")
                if cg["grad_img"]: save_cert_copy(cg["grad_img"], cert_save_name, f"{cg['level']}_毕业证")

            if not resume_file:
                st.error("简历为必传材料，请上传简历后重新核验")
                st.stop()

            with st.spinner("🔍 识别中..."):
                for cg in cert_groups:
                    if cg["degree_img"]: cg["degree_fields"]=ocr_and_extract(cg["degree_img"])
                    if cg["grad_img"]: cg["grad_fields"]=ocr_and_extract(cg["grad_img"])
            re=None
            with tempfile.NamedTemporaryFile(delete=False,suffix=Path(resume_file.name).suffix) as t: t.write(resume_file.read()); rp=t.name
            try: rf=ocr_and_extract(rp); re=field_extractor.extract_resume_education(rf.get("_ocr_text",""))
            except: pass
            # 保存简历副本
            save_cert_copy(rp, cert_save_name, "简历")
            Path(rp).unlink(missing_ok=True)
            result=verify_all_certs(cert_groups,re,rt)

            cn=""; cs=""
            for cg in cert_groups:
                for f in [cg.get("degree_fields"),cg.get("grad_fields")]:
                    if f and f.get("name"): cn=f["name"]
                    if f and f.get("school"): cs=f["school"]
                if cn: break
            hi=max((cg["level"] for cg in cert_groups),key=_level_sort,default="本科")

            # 收集失败原因
            fail_reasons = []
            for gr in result["group_results"]:
                level = gr["level"]
                for label, r_obj in [("学位证", gr.get("degree_result")), ("毕业证", gr.get("grad_result"))]:
                    if r_obj is None: continue
                    for ck in r_obj.checks:
                        if not level_is_pass(ck['level']):
                            fail_reasons.append(f"{level}{label}: {ck['name']} — {ck['message']}")
            for ck in result.get("resume_checks", []):
                if not level_is_pass(ck['level']):
                    fail_reasons.append(f"简历: {ck['name']} — {ck['message']}")

            if result["final"]==AlertLevel.PASS:
                upsert_candidate(cn,cs,"",hi,"pass","pass","pass",rt,reviewed=1)
            else:
                ds="pass" if all(r.get("degree_pass",True) for r in result["group_results"] if r.get("degree_result")) else "fail"
                gs="pass" if all(r.get("grad_pass",True) for r in result["group_results"] if r.get("grad_result")) else "fail"
                upsert_candidate(cn,cs,"",hi,ds,gs,"",rt,reviewed=0, fail_reasons="\n".join(fail_reasons))

            # 重命名证书文件夹: temp名 → 候选人名
            safe_name = cn.replace("/","_").replace("\\","_")[:30] if cn else cert_save_name
            old_dir = UPLOAD_DIR / cert_save_name
            new_dir = UPLOAD_DIR / safe_name
            if old_dir.exists():
                if new_dir.exists(): shutil.rmtree(new_dir)
                old_dir.rename(new_dir)

            st.session_state.single_result={"result":result,"cert_groups":cert_groups,"rt":rt}
            st.session_state.verify_step=2
            for tp in tmp_paths: Path(tp).unlink(missing_ok=True)
            st.rerun()

    # ─── Step 2: 核验结果（总表+详情）───
    elif st.session_state.verify_step==2:
        st.markdown("### Step 2/2 — 核验结果")
        st.markdown("---")

        data=st.session_state.get("single_result")
        if not data: st.info("无核验结果")
        else:
            result=data["result"]; cert_groups=data["cert_groups"]
            final=result["final"]
            colors={AlertLevel.PASS:"green",AlertLevel.REVIEW:"orange",AlertLevel.ALERT:"red"}
            icons={AlertLevel.PASS:"✅ 核验通过",AlertLevel.REVIEW:"⚠️ 需复核",AlertLevel.ALERT:"🚨 异常预警"}
            st.markdown(f"## :{colors[final]}[{icons[final]}]"); st.caption(result["final_summary"])

            # ─── 总表：学历层级总览 ───
            st.markdown("---"); st.subheader("📊 学历层级总览")
            sr=[]
            for gr in result["group_results"]:
                do=gr.get("degree_result"); go=gr.get("grad_result")
                def iok(v):
                    if v is None: return "—"
                    return "✅" if v else "❌"
                sr.append({
                    "学历层级":gr["level"],
                    "学位证":iok(gr["degree_pass"] if do else None),
                    "毕业证":iok(gr["grad_pass"] if go else None),
                    "双证比对":"✅" if gr.get("cross_ok",True) else "❌",
                    "层级判定":"✅ 通过" if gr["level_pass"] else "⚠️ 需复核",
                })
            st.dataframe(pd.DataFrame(sr),use_container_width=True,hide_index=True)

            # ─── 详情：可展开逐项查看 ───
            st.markdown("---"); st.subheader("🔍 逐项详情")
            for gr in result["group_results"]:
                do=gr.get("degree_result"); go=gr.get("grad_result")
                icon="✅" if gr["level_pass"] else "❌"
                with st.expander(f"{icon} {gr['level']} — {'通过' if gr['level_pass'] else '需复核'}",expanded=not gr["level_pass"]):
                    if do:
                        st.write("**🎓 学位证书**")
                        for c in do.checks: st.caption(f"{icon_for(c['level'])} {c['name']}: {c['message']}")
                    if go:
                        st.write("**📜 毕业证书**")
                        for c in go.checks: st.caption(f"{icon_for(c['level'])} {c['name']}: {c['message']}")
                    if do and go and gr.get("cross_items"):
                        st.write("**🔗 双证交叉比对**")
                        for c in gr["cross_items"]: st.caption(f"{icon_for(c['level'])} {c['name']}: {c['message']}")
                    if not do and not go: st.caption("未上传该层级证书")

            # ─── 简历交叉 ───
            if result.get("resume_checks"):
                st.markdown("---"); st.subheader("📋 简历交叉验证")
                for c in result["resume_checks"]: st.write(f"{icon_for(c['level'])} {c['name']}: {c['message']}")

            # ─── 证书字段摘要 ───
            st.markdown("---"); st.subheader("📋 证书字段摘要")
            rows=[]
            for cg in cert_groups:
                for ft,fd in [("学位证",cg.get("degree_fields")),("毕业证",cg.get("grad_fields"))]:
                    if not fd: continue
                    rows.append({"学历层级":cg["level"],"类型":ft,"姓名":fd.get("name","?"),"学校":fd.get("school","?"),"专业":fd.get("major","?"),"毕业日期":fd.get("graduation_date","?"),"证书编号":fd.get("certificate_number","?")})
            if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

        if st.button("🔄 核验下一个候选人", use_container_width=True):
            st.session_state.verify_step = 1
            st.session_state.single_result = None
            st.session_state.degree_groups = [{"id": str(uuid.uuid4()), "level": "本科"}]
            st.rerun()
        st.stop()

# ═══════════════════════════════════════════
# 模式2: 人工核验台
# ═══════════════════════════════════════════
elif mode=="📋 人工核验台":
    st.title("📋 人工核验台")
    candidates=get_all_candidates()
    to_review=[c for c in candidates if not c.get("reviewed")]
    reviewed_list=[c for c in candidates if c.get("reviewed")]

    # ─── 待核验 ───
    st.subheader(f"🔴 待核验（{len(to_review)}人）")
    if not to_review: st.success("暂无")
    for c in to_review:
        # 系统判定级别
        deg_s = c.get('degree_cert_status','')
        grad_s = c.get('grad_cert_status','')
        has_l1_fail = (deg_s == 'fail' or grad_s == 'fail')
        sys_level = "🚨 ALERT" if has_l1_fail else "⚠️ REVIEW"
        level_color = "red" if has_l1_fail else "orange"

        with st.expander(f":{level_color}[{sys_level}] {c['name']} | {c['school']} | {c['education_level']} | {c.get('recruitment_type','')}", expanded=False):
            # ─── 不通过原因（详细）───
            fail_text = c.get('fail_reasons', '')
            if fail_text:
                st.error("未通过详情:")
                for line in fail_text.split('\n'):
                    if line.strip():
                        st.caption(f"  - {line.strip()}")
            elif sys_level == "⚠️ REVIEW":
                st.warning("需复核: 存在可疑项，请查看材料后判定")

            # ─── 左右分栏: 材料 | 判定 ───
            mat_col, judge_col = st.columns([3, 2])

            with mat_col:
                st.caption("候选人材料（按类型分组，点击展开查看）")
                cert_dir = UPLOAD_DIR / c["name"]
                if cert_dir.exists():
                    all_files = sorted([x for x in cert_dir.glob("**/*") if x.is_file()])
                else:
                    all_files = []

                if all_files:
                    # 按类型分组
                    groups = {"学位证书": [], "毕业证书": [], "简历": [], "HR补充材料": [], "其他材料": []}
                    for fp in all_files:
                        fn = fp.name
                        rel = str(fp.relative_to(cert_dir))
                        if "学位" in fn or "degree" in fn.lower(): groups["学位证书"].append((rel, fp))
                        elif "毕业" in fn or "grad" in fn.lower(): groups["毕业证书"].append((rel, fp))
                        elif "简历" in fn or "resume" in fn.lower() or "cv" in fn.lower(): groups["简历"].append((rel, fp))
                        elif "补充" in rel or "HR补充" in rel: groups["HR补充材料"].append((rel, fp))
                        else: groups["其他材料"].append((rel, fp))

                    for gname, items in groups.items():
                        if not items: continue
                        with st.expander(f"{gname} ({len(items)}份)", expanded=(gname in ("学位证书","毕业证书"))):
                            for rel, fp in items:
                                c1, c2 = st.columns([4, 1])
                                c1.caption(rel)
                                if c2.button("查看", key=f"mat_{c['id']}_{fp.stem[:20]}"):
                                    st.session_state[f"view_{c['id']}"] = str(fp); st.rerun()

                    # 显示选中材料
                    vk = f"view_{c['id']}"
                    if vk in st.session_state and st.session_state[vk]:
                        vp = st.session_state[vk]
                        if vp and Path(vp).exists():
                            if Path(vp).suffix.lower() == '.pdf':
                                try:
                                    pg = pdfium.PdfDocument(vp)[0]
                                    bmp = pg.render(scale=1.5)
                                    st.image(bmp.to_pil(), caption=Path(vp).name, use_container_width=True)
                                    pg.close()
                                except:
                                    st.warning(f"无法预览PDF: {Path(vp).name}")
                            else:
                                st.image(vp, caption=Path(vp).name, use_container_width=True)
                            if st.button("关闭", key=f"close_{c['id']}"):
                                st.session_state[vk] = None; st.rerun()
                else:
                    st.caption("（无已保存材料）")

                # 补充上传
                sup_dir = UPLOAD_DIR / c["name"] / "HR补充"
                sup_dir.mkdir(parents=True, exist_ok=True)
                supp_file = st.file_uploader("补充材料", type=["jpg","jpeg","png","pdf"],
                    key=f"supp_{c['id']}", label_visibility="collapsed")
                if supp_file:
                    ext = Path(supp_file.name).suffix
                    (sup_dir / f"补充_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}").write_bytes(supp_file.read())
                    st.success("已保存"); st.rerun()

            with judge_col:
                st.caption("HR判定")
                note = st.text_area("审核备注", key=f"note_{c['id']}", height=68)
                if st.button("通过", key=f"pass_{c['id']}", type="primary", use_container_width=True):
                    update_candidate_status(c["id"], "pass", note); st.rerun()
                if st.button("不通过", key=f"fail_{c['id']}", use_container_width=True):
                    update_candidate_status(c["id"], "fail", note); st.rerun()
                if st.button("待定（补充材料）", key=f"hold_{c['id']}", use_container_width=True):
                    update_candidate_status(c["id"], "hold", note); st.rerun()

    # ─── 已核验 ───
    st.markdown("---")
    st.subheader(f"✅ 已核验（{len(reviewed_list)}人）")
    if not reviewed_list: st.info("暂无")
    else:
        for c in reviewed_list:
            status_icon = {"pass":"✅","fail":"❌","hold":"⏸"}.get(c.get('final_status',''),'')
            with st.expander(f"{status_icon} {c['name']} | {c['school']} | HR判定: {c.get('final_status','')}", expanded=False):
                # 材料逐项查看
                cert_dir = UPLOAD_DIR / c["name"]
                all_mats = []
                if cert_dir.exists():
                    for f in sorted([x for x in cert_dir.glob("**/*") if x.is_file()]):
                        all_mats.append(f)
                if all_mats:
                    st.caption(f"共 {len(all_mats)} 份材料（点击查看）:")
                    for i, mp in enumerate(all_mats):
                        rel_name = str(mp.relative_to(cert_dir))
                        c1, c2 = st.columns([5, 1])
                        c1.caption(f"{i+1}. {rel_name}")
                        if c2.button("查看", key=f"rv_mat_{c['id']}_{i}"):
                            st.session_state[f"rv_{c['id']}"] = str(mp); st.rerun()
                    vk = f"rv_{c['id']}"
                    if vk in st.session_state and st.session_state[vk]:
                        vp = st.session_state[vk]
                        if vp and Path(vp).exists():
                            st.image(vp, caption=Path(vp).name, use_container_width=True)
                            if st.button("关闭查看", key=f"rvclose_{c['id']}"):
                                st.session_state[vk] = None; st.rerun()

                st.caption(f"审核备注: {c.get('reviewer_note','无')} | 更新时间: {c.get('updated_at','')}")
                new_note = st.text_area("修改备注", key=f"rnote_{c['id']}")
                rc1,rc2,rc3 = st.columns(3)
                if rc1.button("✅ 改为通过", key=f"rpass_{c['id']}"): update_candidate_status(c["id"],"pass",new_note); st.rerun()
                if rc2.button("❌ 改为不通过", key=f"rfail_{c['id']}"): update_candidate_status(c["id"],"fail",new_note); st.rerun()
                if rc3.button("⏸ 改为待定", key=f"rhold_{c['id']}"): update_candidate_status(c["id"],"hold",new_note); st.rerun()

# ═══════════════════════════════════════════
# 模式3: 数据看板
# ═══════════════════════════════════════════
elif mode=="📊 数据看板":
    st.title("📊 核验数据看板")
    candidates=get_all_candidates()
    if not candidates: st.info("暂无数据")
    else:
        passed=[c for c in candidates if c["final_status"]=="pass"]
        failed=[c for c in candidates if c["final_status"]=="fail"]
        on_hold=[c for c in candidates if c["final_status"]=="hold"]
        unreviewed=[c for c in candidates if not c.get("reviewed")]

        c1,c2,c3,c4=st.columns(4)
        c1.metric("总人数",len(candidates)); c2.metric("✅ 通过",len(passed))
        c3.metric("❌ 不通过",len(failed)); c4.metric("⏸ 待定/待核验",len(on_hold)+len(unreviewed))

        tabs=st.tabs(["📋 全部候选人","✅ 通过","❌ 不通过","⏸ 待定","🔴 待核验"])
        all_data=[(tabs[0],candidates,"all"),(tabs[1],passed,"pass"),(tabs[2],failed,"fail"),(tabs[3],on_hold,"hold"),(tabs[4],unreviewed,"unreviewed")]

        for tab,data,tkey in all_data:
            with tab:
                if not data: st.caption("暂无"); continue
                df=pd.DataFrame(data)
                cols=["id","name","school","education_level","recruitment_type","final_status","reviewer_note","updated_at"]
                ed=st.data_editor(df[cols],
                    column_config={
                        "id":st.column_config.TextColumn("ID",disabled=True,width="small"),
                        "name":st.column_config.TextColumn("姓名",disabled=True,width="small"),
                        "school":st.column_config.TextColumn("学校",disabled=True,width="medium"),
                        "education_level":st.column_config.TextColumn("学历",disabled=True,width="small"),
                        "recruitment_type":st.column_config.TextColumn("招聘类型",disabled=True,width="small"),
                        "final_status":st.column_config.SelectboxColumn("状态",options=["pass","fail","hold"],width="small"),
                        "reviewer_note":st.column_config.TextColumn("备注",disabled=True,width="medium"),
                        "updated_at":st.column_config.TextColumn("更新时间",disabled=True,width="small"),
                    },hide_index=True,use_container_width=True,key=f"ed_{tkey}")
                if ed is not None and not ed.equals(df[cols]):
                    for _,row in ed.iterrows():
                        if row["final_status"]!=df.loc[df["id"]==row["id"],"final_status"].values[0]:
                            update_candidate_status(int(row["id"]),row["final_status"])
                    st.rerun()
                lb={"all":"全部","pass":"通过","fail":"不通过","pending":"待定"}.get(tkey,tkey)
                st.download_button(f"📥 导出{lb}名单",df.to_csv(index=False).encode("utf-8-sig"),f"核验{lb}名单_{datetime.now().strftime('%Y%m%d')}.csv",key=f"dl_{tkey}")

st.markdown("---")
st.caption("⚠️ Demo系统 | 583国内+191海外 | 院校曾用名 | 专业包含匹配 | 年份严格匹配")
