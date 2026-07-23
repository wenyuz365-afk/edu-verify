"""
学历核验引擎 v4 — 一层制: PASS / REVIEW / ALERT
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from database import query_school, query_chsi, check_school_major_consistency
from ela_detector import ela_analysis


class AlertLevel(Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    ALERT = "ALERT"


@dataclass
class CheckItem:
    name: str
    level: AlertLevel
    message: str
    detail: str = ""


@dataclass
class CertVerifyResult:
    alert_level: AlertLevel
    checks: list
    summary: str
    details: dict


def _norm_date(d: str) -> str:
    if not d: return ""
    m = re.search(r'(\d{4})\D+(\d{1,2})', d)
    return f"{m.group(1)}-{m.group(2).zfill(2)}" if m else d[:7]


def _compare_level(l1, l2):
    if not l1 or not l2: return True
    m = {"本科":["本科","大学本科","学士"],"硕士研究生":["硕士研究生","硕士","研究生"],
         "博士研究生":["博士研究生","博士"],"专科":["专科","大专"]}
    for k,v in m.items():
        if l1 in v: l1=k
        if l2 in v: l2=k
    return l1==l2


def _major_contains(m1: str, m2: str) -> str:
    if not m1 or not m2: return "match"
    a, b = m1.strip().replace(" ",""), m2.strip().replace(" ","")
    if a == b: return "match"
    if a in b or b in a: return "match"
    return "mismatch"


def _extract_year(d: str) -> str:
    if not d: return ""
    m = re.search(r'(\d{4})', d)
    return m.group(1) if m else ""


def _level_to_rank(l: str) -> int:
    if not l: return 0
    for k,v in {"专科":1,"本科":2,"学士":2,"硕士研究生":3,"硕士":3,"博士研究生":4,"博士":4}.items():
        if k in str(l): return v
    return 0


def verify_single_cert(ocr_fields: dict, image_path: str = "", cert_level: str = "") -> CertVerifyResult:
    """单份证书核验, 每个检查直接输出PASS/REVIEW/ALERT"""
    checks = []
    name = ocr_fields.get("name","")
    cert_no = ocr_fields.get("certificate_number","")
    id_number = ocr_fields.get("id_number")
    school_name = ocr_fields.get("school","")
    major = ocr_fields.get("major","")
    edu_level = ocr_fields.get("education_level") or cert_level or ""
    grad_date = ocr_fields.get("graduation_date","")
    cert_type = ocr_fields.get("certificate_type","")

    # ─── 教育部名单 ───
    school_info = query_school(school_name) if school_name else None
    if school_info:
        checks.append(CheckItem("教育部名单", AlertLevel.PASS,
            f"'{school_name}'在教育部名单中",
            f"代码:{school_info.get('school_code')}"))
    else:
        checks.append(CheckItem("教育部名单", AlertLevel.ALERT,
            f"'{school_name or '未知'}'不在教育部名单中，拒绝"))
        return CertVerifyResult(AlertLevel.ALERT, checks,
            f"学校不在教育部名单中", {"school_info": None})

    # ─── 学信库查询 ───
    chsi = None
    if id_number: chsi = query_chsi(name=name, id_number=id_number)
    if not chsi and cert_no: chsi = query_chsi(name=name, cert_no=cert_no)
    if not chsi: chsi = query_chsi(name=name)

    if chsi:
        f_checks = {
            "姓名": name == chsi.get("name"),
            "学校": school_name == chsi.get("school_name"),
            "专业": major == chsi.get("major"),
            "学历层次": _compare_level(edu_level, chsi.get("education_level")),
        }
        date_ok = True
        if grad_date and chsi.get("graduation_date"):
            date_ok = _norm_date(grad_date) == _norm_date(chsi["graduation_date"])
            f_checks["毕业日期"] = date_ok

        all_match = all(f_checks.values())
        if all_match:
            checks.append(CheckItem("学信库查询", AlertLevel.PASS,
                "查到匹配记录，字段一致",
                f"学校:{chsi.get('school_name')}"))
        else:
            mismatches = [k for k,v in f_checks.items() if not v]
            checks.append(CheckItem("学信库查询", AlertLevel.REVIEW,
                f"查到记录但字段不一致: {', '.join(mismatches)}",
                f"学校:{chsi.get('school_name')}"))
        for fn, fv in f_checks.items():
            checks.append(CheckItem(fn, AlertLevel.PASS if fv else AlertLevel.REVIEW,
                "一致" if fv else "不一致", ""))
    else:
        checks.append(CheckItem("学信库查询", AlertLevel.ALERT,
            f"学信库未查到: 姓名'{name}' 编号'{cert_no or '无'}'",
            ""))

    # ─── 证书状态(结业/肄业) ───
    if "结业" in str(cert_type):
        checks.append(CheckItem("证书状态", AlertLevel.REVIEW, "该证书为结业证书", ""))
    elif "肄业" in str(cert_type):
        checks.append(CheckItem("证书状态", AlertLevel.REVIEW, "该证书为肄业证书", ""))
    else:
        checks.append(CheckItem("证书状态", AlertLevel.PASS, "正常", ""))

    # ─── 毕业年龄 ───
    age_lv, age_msg = AlertLevel.PASS, ""
    if id_number and len(id_number)>=14 and grad_date:
        try:
            by, gy = int(id_number[6:10]), int(_extract_year(grad_date) or "0")
            if gy > 0:
                age = gy - by
                if "博士" in edu_level: lo, hi = 24, 45
                elif "硕士" in edu_level: lo, hi = 22, 40
                else: lo, hi = 18, 30
                if age < lo:
                    age_lv, age_msg = AlertLevel.REVIEW, f"毕业年龄{age}岁偏小(正常{lo}-{hi})"
                elif age > hi:
                    age_lv, age_msg = AlertLevel.REVIEW, f"毕业年龄{age}岁偏大(正常{lo}-{hi})"
                else:
                    age_msg = f"毕业年龄{age}岁，正常"
        except: pass
    checks.append(CheckItem("毕业年龄", age_lv, age_msg or "跳过", ""))

    # ─── 院校-专业一致性 ───
    sm = check_school_major_consistency(school_name, major)
    checks.append(CheckItem("院校-专业", AlertLevel.PASS if sm["consistent"] else AlertLevel.REVIEW,
        "一致" if sm["consistent"] else sm["message"], ""))

    # ─── ELA 图片篡改 ───
    if image_path:
        ela = ela_analysis(image_path)
        risk = ela.get("risk_level","low")
        if risk == "high":
            checks.append(CheckItem("图片篡改", AlertLevel.ALERT, ela.get("verdict",""), f"风险:{ela.get('risk_score',0):.4f}"))
        elif risk == "medium":
            checks.append(CheckItem("图片篡改", AlertLevel.REVIEW, ela.get("verdict",""), f"风险:{ela.get('risk_score',0):.4f}"))
        else:
            checks.append(CheckItem("图片篡改", AlertLevel.PASS, ela.get("verdict",""), f"风险:{ela.get('risk_score',0):.4f}"))
    else:
        checks.append(CheckItem("图片篡改", AlertLevel.PASS, "跳过", ""))

    # ─── 综合判定(单证) ───
    has_alert = any(c.level == AlertLevel.ALERT for c in checks)
    has_review = any(c.level == AlertLevel.REVIEW for c in checks)
    if has_alert:
        final, summary = AlertLevel.ALERT, "存在严重异常"
    elif has_review:
        final, summary = AlertLevel.REVIEW, "存在可疑项，需复核"
    else:
        final, summary = AlertLevel.PASS, "全部通过"

    return CertVerifyResult(final, [asdict(c) for c in checks], summary,
        {"school_info": school_info, "chsi": chsi})


def verify_all_certs(cert_groups: list, resume_education: list = None, recruitment_type: str = "校招") -> dict:
    """多层级综合核验"""
    group_results = []

    for g in cert_groups:
        level = g["level"]
        d_r = verify_single_cert(g.get("degree_fields",{}), g.get("degree_img",""), level) if g.get("degree_fields") else None
        gr_r = verify_single_cert(g.get("grad_fields",{}), g.get("grad_img",""), level) if g.get("grad_fields") else None

        cross_ok = True
        cross_items = []
        if d_r and gr_r:
            df, gf = g.get("degree_fields",{}), g.get("grad_fields",{})
            for label, k in [("姓名","name"),("学校","school"),("专业","major"),("学历层次","education_level")]:
                dv, gv = df.get(k), gf.get(k)
                ok = (dv == gv) if dv and gv else True
                cross_items.append(CheckItem(f"双证{label}", AlertLevel.PASS if ok else AlertLevel.REVIEW,
                    "一致" if ok else f"学位'{dv}' vs 毕业'{gv}'",""))
                if not ok: cross_ok = False
            dd, gd = df.get("graduation_date",""), gf.get("graduation_date","")
            if dd and gd:
                dok = _norm_date(dd) == _norm_date(gd)
                cross_items.append(CheckItem("双证日期", AlertLevel.PASS if dok else AlertLevel.REVIEW,
                    "一致" if dok else f"学位{_norm_date(dd)} vs 毕业{_norm_date(gd)}",""))

        deg_pass = d_r and d_r.alert_level == AlertLevel.PASS
        grad_pass = gr_r and gr_r.alert_level == AlertLevel.PASS

        level_pass = (deg_pass if d_r else True) and (grad_pass if gr_r else True) and cross_ok

        # 该层级判定
        has_alert = ((d_r and d_r.alert_level == AlertLevel.ALERT) or
                     (gr_r and gr_r.alert_level == AlertLevel.ALERT) or
                     any(c.level == AlertLevel.ALERT for c in cross_items))
        has_review = not has_alert and (
            (d_r and d_r.alert_level == AlertLevel.REVIEW) or
            (gr_r and gr_r.alert_level == AlertLevel.REVIEW) or
            any(c.level == AlertLevel.REVIEW for c in cross_items))

        if has_alert: lvl = AlertLevel.ALERT
        elif has_review: lvl = AlertLevel.REVIEW
        else: lvl = AlertLevel.PASS

        group_results.append({
            "level": level,
            "degree_result": d_r,
            "grad_result": gr_r,
            "degree_pass": deg_pass,
            "grad_pass": grad_pass,
            "cross_ok": cross_ok,
            "cross_items": [asdict(c) for c in cross_items],
            "level_pass": level_pass,
            "level_alert": lvl,
        })

    # ─── 简历交叉验证 ───
    resume_checks = []
    if resume_education:
        for re_item in resume_education:
            r_level = re_item.get("education_level","")
            r_school = re_item.get("school","")
            r_major = re_item.get("major","")
            r_end = re_item.get("end_year","")
            r_status = re_item.get("status","graduated")

            # dropout/exchange/minor 永远跳过
            permanent_skip = {
                "dropout": "退学/肄业，无需证书",
                "exchange": "交换/访学经历，无需证书",
                "minor": "辅修/双学位，无需独立证书",
            }
            if r_status in permanent_skip:
                resume_checks.append(CheckItem(f"简历{r_level}", AlertLevel.PASS, permanent_skip[r_status], ""))
                continue

            # ongoing: 校招也标待补证，实习跳过
            if r_status == "ongoing":
                if recruitment_type in ("校招",):
                    resume_checks.append(CheckItem(f"简历{r_level}", AlertLevel.REVIEW,
                        f"应届待取证: 简历有{r_level}在读({re_item.get('start_year','')}-{re_item.get('end_year','')})，暂未获得证书", ""))
                else:
                    resume_checks.append(CheckItem(f"简历{r_level}", AlertLevel.PASS,
                        f"在读中（预计{r_end or ''}毕业），无需证书", ""))
                continue

            # 找同层级证书
            matched = False
            for gr in group_results:
                if not _compare_level(r_level, gr["level"]): continue

                cert_school = ""
                for f in [g.get("degree_fields",{}), g.get("grad_fields",{})]:
                    cert_school = f.get("school","")
                    if cert_school: break

                school_ok = cert_school and (cert_school == r_school or r_school in cert_school or cert_school in r_school)
                cert_major = ""
                for f in [g.get("degree_fields",{}), g.get("grad_fields",{})]:
                    cert_major = f.get("major","")
                    if cert_major: break
                major_ok = _major_contains(cert_major, r_major) != "mismatch"

                cert_year = ""
                for f in [g.get("degree_fields",{}), g.get("grad_fields",{})]:
                    d = f.get("graduation_date","")
                    if d: cert_year = _extract_year(d); break
                year_ok = (r_end == cert_year) if r_end and cert_year else True

                matched = True
                msgs = []
                msgs.append("学校一致" if school_ok else f"证书'{cert_school}' vs 简历'{r_school}'")
                msgs.append("专业一致" if major_ok else f"证书'{cert_major}' vs 简历'{r_major}'")
                if r_end and cert_year: msgs.append(f"年份{'一致' if year_ok else f'证书{cert_year} vs 简历{r_end}'}")

                all_ok = school_ok and major_ok and year_ok
                resume_checks.append(CheckItem(f"简历{r_level}",
                    AlertLevel.PASS if all_ok else AlertLevel.REVIEW,
                    " | ".join(msgs), f"简历:{r_school} {r_major} {r_end}"))
                break

            if not matched:
                r_rank = _level_to_rank(r_level)
                cert_ranks = [_level_to_rank(gr["level"]) for gr in group_results]
                if r_rank >= 3 and max(cert_ranks, default=0) >= r_rank:
                    resume_checks.append(CheckItem(f"简历{r_level}", AlertLevel.PASS, "直博/硕博连读，无对应证书(C1)", ""))
                else:
                    if recruitment_type == "社招":
                        resume_checks.append(CheckItem(f"简历{r_level}", AlertLevel.ALERT, f"社招缺{r_level}证", ""))
                    elif recruitment_type == "实习":
                        resume_checks.append(CheckItem(f"简历{r_level}", AlertLevel.ALERT, f"实习-已毕业学历缺{r_level}证", ""))
                    else:
                        resume_checks.append(CheckItem(f"简历{r_level}", AlertLevel.REVIEW,
                            f"应届待取证: {r_level}({re_item.get('start_year','')}-{re_item.get('end_year','')})", ""))

    # ─── 综合结论 ───
    has_alert = any(c.level == AlertLevel.ALERT for c in resume_checks)
    has_review = any(c.level == AlertLevel.REVIEW for c in resume_checks)
    cert_alert = any(gr["level_alert"] == AlertLevel.ALERT for gr in group_results)
    cert_review = any(gr["level_alert"] == AlertLevel.REVIEW for gr in group_results)

    if cert_alert or has_alert:
        final = AlertLevel.ALERT
        final_summary = "存在严重异常，需HR判定"
    elif cert_review or has_review:
        final = AlertLevel.REVIEW
        final_summary = "存在可疑项，需HR复核"
    else:
        final = AlertLevel.PASS
        final_summary = "全部核验通过"

    return {
        "final": final,
        "final_summary": final_summary,
        "group_results": group_results,
        "group_count": len(group_results),
        "resume_checks": [asdict(c) for c in resume_checks],
        "recruitment_type": recruitment_type,
    }
