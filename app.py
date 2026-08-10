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

from database import create_database, upsert_candidate, get_all_candidates, update_candidate_status
from ocr_engine import get_ocr_engine
from field_extractor import get_field_extractor
from verifier import verify_all_certs, AlertLevel

st.set_page_config(page_title="学历AI核验系统", page_icon="⏺", layout="wide")

# ─── 全局样式注入 ───
def inject_css():
    st.markdown("""
    <style>
    /* ============================================
       ROOT: Premium warm-neutral + light-blue palette
       ============================================ */
    :root {
        --accent: #2563EB;
        --accent-hover: #1D4ED8;
        --accent-soft: #3B82F6;
        --accent-subtle: #EFF6FF;
        --accent-glow: rgba(37,99,235,0.18);
        --success: #059669;
        --success-subtle: #ECFDF5;
        --warning: #D97706;
        --warning-subtle: #FFFBEB;
        --danger: #DC2626;
        --danger-subtle: #FEF2F2;
        --text-primary: #18181B;
        --text-secondary: #3F3F46;
        --text-muted: #71717A;
        --border: #E4E4E7;
        --border-light: #F4F4F5;
        --surface: #FFFFFF;
        --surface-hover: #FAFAFA;
        --bg: #FAFAF9;
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
        --shadow-xs: 0 1px 1px rgba(0,0,0,0.03);
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md: 0 4px 6px rgba(0,0,0,0.03), 0 2px 4px rgba(0,0,0,0.04);
        --shadow-lg: 0 10px 15px rgba(0,0,0,0.04), 0 4px 6px rgba(0,0,0,0.03);
        --shadow-xl: 0 20px 40px rgba(0,0,0,0.06), 0 8px 16px rgba(0,0,0,0.04);
    }

    /* ============================================
       GLOBAL: Typography & Base
       ============================================ */
    .stApp {
        font-family: 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
        background: var(--bg);
        color: var(--text-primary);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    #MainMenu, footer, header[data-testid="stHeader"] {
        background: transparent;
    }

    /* Subtle top accent line */
    [data-testid="stAppViewContainer"]::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--accent), var(--accent-soft), #93C5FD, var(--accent));
        z-index: 99999;
        opacity: 0.7;
    }

    h1, h2, h3, h4, h5, h6 {
        font-weight: 650 !important;
        letter-spacing: -0.025em;
        color: var(--text-primary) !important;
    }
    h1 { font-size: 1.625rem !important; line-height: 1.2; }
    h2 { font-size: 1.25rem !important; line-height: 1.3; }
    h3 { font-size: 1.05rem !important; line-height: 1.35; }
    p, li, label { color: var(--text-secondary); }

    /* ============================================
       SIDEBAR: Light, matches main area
       ============================================ */
    [data-testid="stSidebar"] {
        background: #F1F5F9;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] * { color: #18181B !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #18181B !important;
    }
    [data-testid="stSidebar"] .stRadio > div {
        background: transparent;
        border-radius: var(--radius-md);
        padding: 2px;
    }
    [data-testid="stSidebar"] .stRadio label {
        border-radius: var(--radius-sm);
        padding: 9px 14px !important;
        margin: 1px 0;
        font-size: 0.875rem;
        font-weight: 500;
        transition: all 0.2s cubic-bezier(0.16,1,0.3,1);
        border: 1px solid transparent;
        color: #18181B !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #E2E8F0 !important;
        color: #18181B !important;
    }
    [data-testid="stSidebar"] .stRadio label[data-selected="true"] {
        background: #DBEAFE !important;
        border-color: rgba(37,99,235,0.3) !important;
        color: #1D4ED8 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: var(--border) !important;
        margin: 1rem 0 !important;
    }
    [data-testid="stSidebar"] .stCaption {
        color: var(--text-secondary) !important;
        font-size: 0.75rem;
    }

    /* ============================================
       BUTTONS
       ============================================ */
    .stButton > button {
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 0.45rem 1.2rem !important;
        letter-spacing: -0.01em;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
    }
    .stButton > button:active {
        transform: translateY(0) scale(0.985);
    }

    /* ============================================
       EXPANDER: Glass-surface cards
       ============================================ */
    .streamlit-expanderHeader {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
        background: var(--surface) !important;
        padding: 13px 18px !important;
        font-weight: 550 !important;
        font-size: 0.9rem !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em;
        box-shadow: var(--shadow-xs);
        transition: all 0.25s cubic-bezier(0.16,1,0.3,1);
    }
    .streamlit-expanderHeader:hover {
        border-color: #D4D4D8 !important;
        background: var(--surface-hover) !important;
        box-shadow: var(--shadow-md);
    }
    .streamlit-expanderHeader svg {
        color: var(--text-muted) !important;
        transition: transform 0.2s ease;
    }
    .streamlit-expanderHeader[aria-expanded="true"] svg {
        color: var(--accent) !important;
    }
    .streamlit-expanderContent {
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
        background: var(--surface) !important;
        padding: 20px !important;
    }

    /* ============================================
       DATAFRAME: Editorial table
       ============================================ */
    [data-testid="stDataFrame"] {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
        overflow: hidden;
        box-shadow: var(--shadow-xs);
    }
    [data-testid="stDataFrame"] thead th {
        background: var(--surface-hover) !important;
        color: var(--text-muted) !important;
        font-weight: 600 !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 11px 16px !important;
        border-bottom: 1px solid var(--border) !important;
    }
    [data-testid="stDataFrame"] tbody td {
        padding: 11px 16px !important;
        font-size: 0.85rem !important;
        border-bottom: 1px solid var(--border-light) !important;
        color: var(--text-primary);
    }
    [data-testid="stDataFrame"] tbody tr:last-child td {
        border-bottom: none;
    }
    [data-testid="stDataFrame"] tbody tr:hover {
        background: var(--surface-hover) !important;
    }

    /* ============================================
       METRIC: Stat cards
       ============================================ */
    [data-testid="stMetric"] {
        background: var(--surface) !important;
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border) !important;
        padding: 20px 24px !important;
        box-shadow: var(--shadow-xs);
        transition: box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: var(--shadow-md);
    }
    [data-testid="stMetricValue"] {
        font-size: 2.125rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        color: var(--text-muted) !important;
        font-weight: 550;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 2px;
    }

    /* ============================================
       PROGRESS: Sleek capsule
       ============================================ */
    .stProgress > div {
        background: var(--border-light) !important;
        border-radius: 99px !important;
        height: 6px !important;
    }
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--accent), var(--accent-soft)) !important;
        border-radius: 99px !important;
        transition: width 0.3s ease;
    }

    /* ============================================
       TABS: Underline indicator
       ============================================ */
    .stTabs [data-baseweb="tab"] {
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        color: var(--text-muted) !important;
        padding: 10px 20px !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.2s ease;
        letter-spacing: -0.01em;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-secondary) !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom-color: var(--accent) !important;
    }

    /* ============================================
       INPUTS: Clean & focused
       ============================================ */
    .stTextInput input, [data-testid="stSelectbox"] > div > div:first-child {
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border) !important;
        font-size: 0.875rem !important;
        background: var(--surface) !important;
        transition: all 0.2s ease;
    }
    .stTextInput input:focus, [data-testid="stSelectbox"] > div:focus-within > div:first-child {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
        outline: none !important;
    }
    .stTextInput label, [data-testid="stSelectbox"] label {
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        color: var(--text-secondary) !important;
    }

    /* ============================================
       FILE UPLOADER: Dashed dropzone
       ============================================ */
    [data-testid="stFileUploader"] {
        border-radius: var(--radius-md) !important;
        border: 1.5px dashed var(--border) !important;
        background: var(--surface) !important;
        transition: all 0.25s ease;
        padding: 8px !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #A1A1AA !important;
        background: var(--surface-hover) !important;
    }
    [data-testid="stFileUploader"]:has([data-testid="stFileUploaderDropzone"]:focus-within) {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 4px var(--accent-glow);
    }

    /* ============================================
       RADIO: Chip-style
       ============================================ */
    .stRadio [role="radiogroup"] {
        gap: 4px;
    }
    .stRadio label {
        border-radius: var(--radius-sm) !important;
        padding: 8px 16px !important;
        font-weight: 500;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }
    .stRadio label:hover {
        background: var(--surface-hover) !important;
        border-color: var(--border);
    }
    .stRadio label:has(input:checked) {
        background: var(--accent-subtle) !important;
        border-color: rgba(79,70,229,0.2) !important;
        color: var(--accent) !important;
    }

    /* ============================================
       STATUS BADGES: Pill indicators
       ============================================ */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 5px 14px;
        border-radius: 99px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }
    .status-badge.pass {
        background: var(--success-subtle);
        color: #047857;
        border: 1px solid rgba(5,150,105,0.15);
    }
    .status-badge.review {
        background: var(--warning-subtle);
        color: #B45309;
        border: 1px solid rgba(217,119,6,0.15);
    }
    .status-badge.alert {
        background: var(--danger-subtle);
        color: #B91C1C;
        border: 1px solid rgba(220,38,38,0.15);
    }
    .status-dot {
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        box-shadow: 0 0 0 2px currentColor;
        opacity: 0.7;
    }
    .status-dot.pass { background: var(--success); color: var(--success); }
    .status-dot.review { background: var(--warning); color: var(--warning); }
    .status-dot.alert { background: var(--danger); color: var(--danger); }

    /* ============================================
       ALERTS: Subtle banners
       ============================================ */
    .stAlert {
        border-radius: var(--radius-md) !important;
        border: 1px solid !important;
        font-size: 0.85rem;
        padding: 14px 18px !important;
    }
    [data-testid="stSuccess"] {
        background: var(--success-subtle) !important;
        border-color: rgba(5,150,105,0.12) !important;
        color: #047857 !important;
    }
    [data-testid="stWarning"] {
        background: var(--warning-subtle) !important;
        border-color: rgba(217,119,6,0.12) !important;
        color: #B45309 !important;
    }
    [data-testid="stError"] {
        background: var(--danger-subtle) !important;
        border-color: rgba(220,38,38,0.12) !important;
        color: #B91C1C !important;
    }
    [data-testid="stInfo"] {
        background: var(--accent-subtle) !important;
        border-color: rgba(79,70,229,0.12) !important;
    }

    /* ============================================
       DIVIDERS: Hairline rule
       ============================================ */
    hr {
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 1.75rem 0 !important;
    }

    /* ============================================
       DOWNLOAD: Subtle secondary
       ============================================ */
    .stDownloadButton > button {
        border-radius: var(--radius-sm) !important;
        font-weight: 500 !important;
        font-size: 0.825rem !important;
        border: 1px solid var(--border) !important;
        background: var(--surface) !important;
        color: var(--text-secondary) !important;
        box-shadow: var(--shadow-xs);
        transition: all 0.2s ease;
    }
    .stDownloadButton > button:hover {
        background: var(--surface-hover) !important;
        border-color: #D4D4D8 !important;
        color: var(--text-primary) !important;
        box-shadow: var(--shadow-sm);
    }

    /* ============================================
       SELECTBOX
       ============================================ */
    [data-testid="stSelectbox"] > div > div {
        border-radius: var(--radius-sm) !important;
        border-color: var(--border) !important;
        background: var(--surface) !important;
    }

    /* ============================================
       CAPTION & HELPER
       ============================================ */
    .stCaption, caption, figcaption {
        color: var(--text-muted) !important;
        font-size: 0.78rem !important;
        font-weight: 450;
        letter-spacing: 0.01em;
    }

    /* ============================================
       SCROLLBAR: Minimal
       ============================================ */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #D4D4D8; border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: #A1A1AA; }

    /* ============================================
       SPINNER: Accent tint
       ============================================ */
    .stSpinner > div { border-top-color: var(--accent) !important; }

    /* ============================================
       DATA EDITOR
       ============================================ */
    [data-testid="stDataEditor"] {
        border-radius: var(--radius-md) !important;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

inject_css()

@st.cache_resource
def init(): create_database(); return get_ocr_engine(), get_field_extractor()
ocr_engine, field_extractor = init()

LEVELS = ["本科", "硕士研究生", "博士研究生"]

def _level_sort(l): return {"本科":1,"硕士研究生":2,"博士研究生":3}.get(l,0)

def icon_for(level, severity=""):
    if hasattr(level, 'value'): level = level.value
    if str(level) == 'REVIEW':
        c = {"high": "#DC2626", "medium": "#D97706", "low": "#F59E0B"}.get(severity, "#D97706")
    else:
        c = "#059669"
    return f'<span style="color:{c}; font-weight:700; margin-right:2px;">●</span>'

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
def _process_batch(batch_zip):
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

    st.subheader(f"批量核验 - {len(candidates)}位候选人")
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
        clist=[g for g in cgroups.values() if g["degree_img"] and g["grad_img"]]
        if not clist: continue
        for cg in clist:
            if cg["degree_img"]: cg["degree_fields"]=ocr_and_extract(cg["degree_img"])
            if cg["grad_img"]: cg["grad_fields"]=ocr_and_extract(cg["grad_img"])
        re=None
        if rp:
            try: rf=ocr_and_extract(rp); re=field_extractor.extract_resume_education(rf.get("_ocr_text",""))
            except: pass
        res=verify_all_certs(clist,re)
        cn=folder; cs=""; cno=""
        for cg in clist:
            for f in [cg.get("degree_fields"),cg.get("grad_fields")]:
                if f and f.get("name"): cn=f["name"]
                if f and f.get("school"): cs=f["school"]
                if f and f.get("certificate_number"): cno=f["certificate_number"]
            if cn!=folder: break
        batch_results.append({
            "name":cn,"folder":folder,"school":cs,
            "levels":", ".join(cg["level"] for cg in clist),
            "result":res["final"].value,"summary":res["final_summary"],
            "_res":res,"_clist":clist
        })
        hi=max((cg["level"] for cg in clist),key=_level_sort,default="本科")
        fail_reasons = "\n".join([f"{c['name']}: {c['message']}" for c in res.get("all_checks",[]) if not level_is_pass(c.get('level'))])
        if res["final"]==AlertLevel.PASS:
            upsert_candidate(cn,cs,"",hi,"pass","pass","pass",cert_no=cno,reviewed=1, fail_reasons=fail_reasons)
        else:
            has_alert = any(not level_is_pass(c.get('level')) and c.get('severity','') == 'high' for c in res.get("all_checks",[]))
            ds = "fail" if has_alert else "pass"
            gs = "fail" if has_alert else "pass"
            upsert_candidate(cn,cs,"",hi,ds,gs,"",cert_no=cno,reviewed=0, fail_reasons=fail_reasons)
    prog.empty(); stat.empty()

    # 存入session_state, 在页面主体区域渲染
    st.session_state.batch_results=batch_results
    st.session_state.show_batch=True
    st.rerun()


# ═══════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 0 0 8px 0;">
        <div style="font-size:2.25rem; margin-bottom:4px; filter:grayscale(0.2);">&#x1F393;</div>
        <div style="font-weight:700; font-size:1rem; color:#18181B; letter-spacing:-0.01em;">学历AI核验系统</div>
        <div style="font-size:0.7rem; color:#A1A1AA; margin-top:2px; letter-spacing:0.04em; text-transform:uppercase;">Credential Verification</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    mode=st.radio("",["上传核验","人工核验台","数据看板"], label_visibility="collapsed")
    st.markdown("---")
    st.caption("583 国内院校 · 191 海外院校")
    st.caption("曾用名匹配 · 专业包含校验")

# ═══════════════════════════════════════════
# 模式1: 上传核验（三步流）
# ═══════════════════════════════════════════
if mode=="上传核验":
    st.title("学历证书核验")

    # ─── 批量结果展示 ───
    if st.session_state.get('show_batch') and st.session_state.get('batch_results'):
        batch_results = st.session_state.batch_results
        st.success(f"批量核验完成 — {len(batch_results)}位候选人")
        df = pd.DataFrame([{k:v for k,v in r.items() if not k.startswith('_')} for r in batch_results])
        def bclr(v):
            if v == 'PASS': return 'background-color:#ECFDF5; color:#059669; font-weight:600'
            return 'background-color:#FFFBEB; color:#D97706; font-weight:600'
        st.dataframe(df.style.map(bclr, subset=['result']), use_container_width=True, hide_index=True)
        st.download_button('导出CSV', df.to_csv(index=False).encode('utf-8-sig'),
            f"批量核验_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
        st.markdown('---')
        st.subheader('逐人详情')
        for r in batch_results:
            res = r['_res']; final = res['final']
            status_label = {"PASS":"PASS 通过","REVIEW":"REVIEW 需复核"}.get(final.value if hasattr(final,'value') else str(final),str(final))
            with st.expander(f"{status_label} — {r['name']} · {r['school']} · {r['levels']}", expanded=final != AlertLevel.PASS):
                all_checks = res.get("all_checks", [])
                l1 = [c for c in all_checks if "图片篡改" in c.get('name','')]
                l2 = [c for c in all_checks if "学信库" in c.get('name','')]
                l3 = [c for c in all_checks if c not in l1 and c not in l2]
                for layer_title, checks in [("Layer 1: 图片篡改检测", l1), ("Layer 2: 学信库核验", l2), ("Layer 3: 交叉核验", l3)]:
                    n_pass = sum(1 for c in checks if level_is_pass(c['level']))
                    n_fail = len(checks) - n_pass
                    label = f"{layer_title}（{len(checks)}项，{n_pass}通过" + (f"，{n_fail}异常）" if n_fail else "）")
                    st.caption(label)
                    if not checks:
                        st.caption("  (无)")
                    else:
                        for c in checks:
                            st.markdown(f"{icon_for(c['level'], c.get('severity',''))} {c['name']}: {c['message']}", unsafe_allow_html=True)
        if st.button('核验下一批', use_container_width=True):
            st.session_state.show_batch=False; st.session_state.batch_results=None
            st.session_state.verify_step=1; st.rerun()
        st.stop()

    if "verify_step" not in st.session_state: st.session_state.verify_step=1

    # ─── Step 1: 选择场景 ───
    if st.session_state.verify_step==1:
        st.markdown("### Step 1/2")

        um=st.radio("上传模式",["单个候选人","批量候选人"],horizontal=True)

        if um=="单个候选人":
            if "degree_groups" not in st.session_state:
                st.session_state.degree_groups=[{"id":str(uuid.uuid4()),"level":"本科"}]
            for i,g in enumerate(st.session_state.degree_groups):
                with st.expander(f"学历层次 #{i+1}",expanded=True):
                    c1,c2,c3=st.columns([2,3,3])
                    with c1: g["level"]=st.selectbox("学历层次",LEVELS,index=LEVELS.index(g["level"]) if g["level"] in LEVELS else 0,key=f"lv_{g['id']}")
                    with c2: st.file_uploader("学位证书",type=["jpg","jpeg","png","pdf"],key=f"deg_{g['id']}")
                    with c3: st.file_uploader("毕业证书",type=["jpg","jpeg","png","pdf"],key=f"grad_{g['id']}")
                    if len(st.session_state.degree_groups)>1:
                        if st.button("删除",key=f"del_{g['id']}"):
                            st.session_state.degree_groups=[gg for gg in st.session_state.degree_groups if gg["id"]!=g["id"]]; st.rerun()
            if st.button("添加学历",disabled=len(st.session_state.degree_groups)>=3):
                st.session_state.degree_groups.append({"id":str(uuid.uuid4()),"level":"硕士研究生"}); st.rerun()
            st.markdown("---")
            resume_file=st.file_uploader("简历 (必传)",type=["jpg","jpeg","png","pdf"],key="resume_single")
            batch_info=None
        else:
            st.caption("每个子文件夹=一位候选人，文件夹名=候选人姓名，文件按关键词自动分类")
            st.caption("```\n候选人材料.zip\n├── 张三/\n│   ├── 本科学位证.jpg\n│   ├── 本科毕业证.jpg\n│   └── 简历.pdf\n├── 李四/\n│   ├── 硕士学位证.jpg\n│   └── 硕士毕业证.jpg\n```")
            batch_zip=st.file_uploader("上传ZIP压缩包",type=["zip"],key="bzip")
            batch_info={"zip":batch_zip}
            resume_file=None
            if "degree_groups" not in st.session_state: st.session_state.degree_groups=[{"id":str(uuid.uuid4()),"level":"本科"}]

        if st.button("开始核验",type="primary",use_container_width=True):
            if um=="批量候选人" and batch_info and batch_info.get("zip"):
                _process_batch(batch_info["zip"]); st.stop()

            cert_groups=[]; tmp_paths=[]
            for g in st.session_state.degree_groups:
                dk=f"deg_{g['id']}"; gk=f"grad_{g['id']}"
                df=st.session_state.get(dk); gf=st.session_state.get(gk)
                if not df: st.error(f"{g['level']}: 学位证书为必传"); st.stop()
                if not gf: st.error(f"{g['level']}: 毕业证书为必传"); st.stop()
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

            with st.spinner("识别中..."):
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
            result=verify_all_certs(cert_groups,re)

            cn=""; cs=""; cno=""
            for cg in cert_groups:
                for f in [cg.get("degree_fields"),cg.get("grad_fields")]:
                    if f and f.get("name"): cn=f["name"]
                    if f and f.get("school"): cs=f["school"]
                    if f and f.get("certificate_number"): cno=f.get("certificate_number")
                if cn: break
            hi=max((cg["level"] for cg in cert_groups),key=_level_sort,default="本科")

            fail_reasons = [f"{ck['name']}: {ck['message']}" for ck in result.get("all_checks", []) if not level_is_pass(ck['level'])]

            if result["final"]==AlertLevel.PASS:
                upsert_candidate(cn,cs,"",hi,"pass","pass","pass",cert_no=cno,reviewed=1, fail_reasons="\n".join(fail_reasons))
            else:
                has_alert = any(not level_is_pass(c['level']) and c.get('severity','') == 'high' for c in result.get("all_checks", []))
                ds = "fail" if has_alert else "pass"
                gs = "fail" if has_alert else "pass"
                upsert_candidate(cn,cs,"",hi,ds,gs,"",cert_no=cno,reviewed=0, fail_reasons="\n".join(fail_reasons))

            # 重命名证书文件夹: temp名 → 候选人名
            safe_name = cn.replace("/","_").replace("\\","_")[:30] if cn else cert_save_name
            old_dir = UPLOAD_DIR / cert_save_name
            new_dir = UPLOAD_DIR / safe_name
            if old_dir.exists():
                if new_dir.exists(): shutil.rmtree(new_dir)
                old_dir.rename(new_dir)

            st.session_state.single_result={"result":result,"cert_groups":cert_groups}
            st.session_state.verify_step=2
            for tp in tmp_paths: Path(tp).unlink(missing_ok=True)
            st.rerun()

    # ─── Step 2: 核验结果（总表+详情）───
    elif st.session_state.verify_step==2:
        st.markdown("### Step 2/2")
        st.markdown("---")

        data=st.session_state.get("single_result")
        if not data: st.info("无核验结果")
        else:
            result=data["result"]; cert_groups=data["cert_groups"]
            final=result["final"]
            badge_map = {
                AlertLevel.PASS: '<span class="status-badge pass">核验通过</span>',
                AlertLevel.REVIEW: '<span class="status-badge review">需复核</span>',
            }
            status_text = {AlertLevel.PASS: "核验通过", AlertLevel.REVIEW: "需人工复核"}
            st.markdown(f"## {badge_map[final]} {status_text[final]}", unsafe_allow_html=True)
            st.caption(result["final_summary"])
            # ─── 三层核验详情 ───
            st.markdown("---"); st.subheader("核验详情")
            all_checks = result.get("all_checks", [])
            l1 = [c for c in all_checks if "图片篡改" in c.get('name','')]
            l2 = [c for c in all_checks if "学信库" in c.get('name','')]
            l3 = [c for c in all_checks if c not in l1 and c not in l2]
            for layer_title, checks in [("Layer 1: 图片篡改检测", l1), ("Layer 2: 学信库核验", l2), ("Layer 3: 交叉核验", l3)]:
                n_pass = sum(1 for c in checks if level_is_pass(c['level']))
                n_fail = len(checks) - n_pass
                label = f"{layer_title}（{len(checks)}项，{n_pass}通过" + (f"，{n_fail}异常）" if n_fail else "）")
                with st.expander(label, expanded=True):
                    if not checks:
                        st.caption("(无)")
                    else:
                        for c in checks:
                            st.markdown(f"{icon_for(c['level'], c.get('severity',''))} {c['name']}: {c['message']}", unsafe_allow_html=True)

            # ─── 证书字段摘要 ───
            st.markdown("---"); st.subheader("证书字段摘要")
            rows=[]
            for cg in cert_groups:
                for ft,fd in [("学位证",cg.get("degree_fields")),("毕业证",cg.get("grad_fields"))]:
                    if not fd: continue
                    rows.append({"学历层级":cg["level"],"类型":ft,"姓名":fd.get("name","?"),"学校":fd.get("school","?"),"专业":fd.get("major","?"),"毕业日期":fd.get("graduation_date","?"),"证书编号":fd.get("certificate_number","?")})
            if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

        if st.button("核验下一个候选人", use_container_width=True):
            st.session_state.verify_step = 1
            st.session_state.single_result = None
            st.session_state.degree_groups = [{"id": str(uuid.uuid4()), "level": "本科"}]
            st.rerun()
        st.stop()

# ═══════════════════════════════════════════
# 模式2: 人工核验台
# ═══════════════════════════════════════════
elif mode=="人工核验台":
    st.title("人工核验台")
    candidates=get_all_candidates()
    to_review=[c for c in candidates if not c.get("reviewed")]
    reviewed_list=[c for c in candidates if c.get("reviewed")]

    # ─── 待核验 ───
    st.subheader(f"待核验（{len(to_review)}人）")
    if not to_review: st.success("暂无")
    for c in to_review:
        with st.expander(f"{c['name']} · {c['school']} · {c['education_level']}", expanded=False):
            # ─── 不通过原因（详细）───
            fail_text = c.get('fail_reasons', '')
            if fail_text:
                for line in fail_text.split('\n'):
                    if line.strip():
                        st.markdown(f"● {line.strip()}")

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
    st.subheader(f"已核验（{len(reviewed_list)}人）")
    if not reviewed_list: st.info("暂无")
    else:
        for c in reviewed_list:
            status_icon = {"pass":"通过","fail":"不通过","hold":"待定"}.get(c.get('final_status',''),'')
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
                if rc1.button("改为通过", key=f"rpass_{c['id']}"): update_candidate_status(c["id"],"pass",new_note); st.rerun()
                if rc2.button("改为不通过", key=f"rfail_{c['id']}"): update_candidate_status(c["id"],"fail",new_note); st.rerun()
                if rc3.button("改为待定", key=f"rhold_{c['id']}"): update_candidate_status(c["id"],"hold",new_note); st.rerun()

# ═══════════════════════════════════════════
# 模式3: 数据看板
# ═══════════════════════════════════════════
elif mode=="数据看板":
    st.title("核验数据看板")
    candidates=get_all_candidates()
    if not candidates: st.info("暂无数据")
    else:
        passed=[c for c in candidates if c["final_status"]=="pass"]
        failed=[c for c in candidates if c["final_status"]=="fail"]
        on_hold=[c for c in candidates if c["final_status"]=="hold"]
        unreviewed=[c for c in candidates if not c.get("reviewed")]

        c1,c2,c3,c4=st.columns(4)
        c1.metric("总人数",len(candidates)); c2.metric("通过",len(passed))
        c3.metric("不通过",len(failed)); c4.metric("待定/待核验",len(on_hold)+len(unreviewed))

        tabs=st.tabs(["全部候选人","通过","不通过","待定","待核验"])
        all_data=[(tabs[0],candidates,"all"),(tabs[1],passed,"pass"),(tabs[2],failed,"fail"),(tabs[3],on_hold,"hold"),(tabs[4],unreviewed,"unreviewed")]

        for tab,data,tkey in all_data:
            with tab:
                if not data: st.caption("暂无"); continue
                df=pd.DataFrame(data)
                cols=["id","name","school","education_level","final_status","reviewer_note","updated_at"]
                ed=st.data_editor(df[cols],
                    column_config={
                        "id":st.column_config.TextColumn("ID",disabled=True,width="small"),
                        "name":st.column_config.TextColumn("姓名",disabled=True,width="small"),
                        "school":st.column_config.TextColumn("学校",disabled=True,width="medium"),
                        "education_level":st.column_config.TextColumn("学历",disabled=True,width="small"),
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
                st.download_button(f"导出{lb}名单",df.to_csv(index=False).encode("utf-8-sig"),f"核验{lb}名单_{datetime.now().strftime('%Y%m%d')}.csv",key=f"dl_{tkey}")

st.markdown("---")
st.caption("学历AI核验系统 · Demo · 583 国内院校 + 191 海外院校 · 院校曾用名匹配 · 专业包含校验")
