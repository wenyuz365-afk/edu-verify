"""
学历核验引擎 v5 — 三层递进: 图片篡改 → 学信库 → 交叉核验
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from datetime import datetime
from database import query_chsi
from ela_detector import ela_analysis


class AlertLevel(Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"


@dataclass
class CheckItem:
    name: str
    level: AlertLevel
    message: str
    detail: str = ""
    severity: str = ""  # high / medium / low，仅 REVIEW 时有效


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


# ═══════════════════════════════════════════
# Layer 1: 图片篡改检测
# ═══════════════════════════════════════════
def layer1_ela_check(labeled_images: list) -> tuple:
    """labeled_images: [(label, path), ...]  返回 (checks, blocked)"""
    checks = []
    blocked = None

    for label, fp in labeled_images:
        if not fp: continue
        ela = ela_analysis(fp)
        risk = ela.get("risk_level","low")
        score = ela.get("risk_score",0.0)
        verdict = ela.get("verdict","")

        if risk == "high":
            checks.append(CheckItem(f"{label}: 图片篡改", AlertLevel.REVIEW,
                f"高风险 — {verdict}", f"风险分:{score:.4f}", severity="high"))
            blocked = "high"
        elif risk == "medium":
            checks.append(CheckItem(f"{label}: 图片篡改", AlertLevel.REVIEW,
                f"中风险 — {verdict}", f"风险分:{score:.4f}", severity="medium"))
            blocked = "medium"
        else:
            checks.append(CheckItem(f"{label}: 图片篡改", AlertLevel.PASS,
                f"通过", f"风险分:{score:.4f}"))

    return checks, blocked


# ═══════════════════════════════════════════
# Layer 2: 学信库核验
# ═══════════════════════════════════════════
def layer2_chsi_verify(ocr_fields: dict, cert_label: str = "") -> tuple:
    """学信库多字段匹配。cert_label: "本科·学位证·张三" """
    checks = []
    name = ocr_fields.get("name","")
    school = ocr_fields.get("school","")
    major = ocr_fields.get("major","")
    grad_date = ocr_fields.get("graduation_date","")
    cert_no = ocr_fields.get("certificate_number","")
    id_number = ocr_fields.get("id_number")
    prefix = f"{cert_label}: " if cert_label else ""

    chsi = None
    if id_number: chsi = query_chsi(name=name, id_number=id_number)
    if not chsi and cert_no: chsi = query_chsi(name=name, cert_no=cert_no)
    if not chsi: chsi = query_chsi(name=name)

    if not chsi:
        checks.append(CheckItem(f"{prefix}学信库", AlertLevel.REVIEW,
            f"查无此人 — 姓名'{name}' 编号'{cert_no or '无'}'", ""))
        return checks, False

    fields = [
        ("姓名", name, chsi.get("name","")),
        ("学校", school, chsi.get("school_name","")),
        ("专业", major, chsi.get("major","")),
        ("学历层次", ocr_fields.get("education_level",""), chsi.get("education_level","")),
        ("毕业日期", _norm_date(grad_date), _norm_date(chsi.get("graduation_date",""))),
        ("证书编号", cert_no, chsi.get("cert_no","")),
    ]

    all_match = True
    mismatches = []
    for fname, cert_val, chsi_val in fields:
        if not cert_val or not chsi_val:
            continue
        if fname == "学历层次":
            ok = _compare_level(cert_val, chsi_val)
        elif fname == "毕业日期":
            ok = (cert_val == chsi_val)
        else:
            ok = (str(cert_val).strip() == str(chsi_val).strip())
        if not ok:
            all_match = False
            mismatches.append(f"{fname}不一致(证书'{cert_val}' vs 学信库'{chsi_val}')")

    if all_match:
        checks.append(CheckItem(f"{prefix}学信库", AlertLevel.PASS,
            f"全部匹配 — {chsi.get('school_name','')}", ""))
        return checks, True

    checks.append(CheckItem(f"{prefix}学信库", AlertLevel.REVIEW,
        f"{'; '.join(mismatches)}", "", severity="high"))
    return checks, False


# ═══════════════════════════════════════════
# Layer 3: 交叉核验
# ═══════════════════════════════════════════
def layer3_cross_verify(cert_groups: list, resume_education: list = None) -> list:
    """毕业状态判定 + 双证交叉比对 + 简历匹配"""
    checks = []

    for g in cert_groups:
        level = g["level"]
        df = g.get("degree_fields",{}) or {}
        gf = g.get("grad_fields",{}) or {}

        # ─── 双证交叉比对 ───
        cross_fields = [("姓名","name"),("学校","school"),("专业","major"),
                        ("学历层次","education_level")]
        for label, k in cross_fields:
            dv, gv = df.get(k), gf.get(k)
            if not dv or not gv: continue
            ok = (str(dv).strip() == str(gv).strip())
            checks.append(CheckItem(f"{level}: 双证{label}比对",
                AlertLevel.PASS if ok else AlertLevel.REVIEW,
                "一致" if ok else f"学位'{dv}' vs 毕业'{gv}'",
                "", "high" if not ok else ""))

        dd, gd = df.get("graduation_date",""), gf.get("graduation_date","")
        if dd and gd:
            dok = _norm_date(dd) == _norm_date(gd)
            checks.append(CheckItem(f"{level}: 双证日期比对",
                AlertLevel.PASS if dok else AlertLevel.REVIEW,
                "一致" if dok else f"学位{_norm_date(dd)} vs 毕业{_norm_date(gd)}",
                "", "high" if not dok else ""))

    # ─── 简历交叉验证 ───
    if resume_education:
        for re_item in resume_education:
            r_level = re_item.get("education_level","")
            r_school = re_item.get("school","")
            r_major = re_item.get("major","")
            r_end = re_item.get("end_year","")
            r_start = re_item.get("start_year","")
            r_status = re_item.get("status","")

            # 退学/交换/辅修 → 无需证书，直接跳过
            skip_map = {"dropout":"退学/肄业","exchange":"交换/访学","minor":"辅修/双学位"}
            if r_status in skip_map:
                checks.append(CheckItem(f"简历·{r_level}: 毕业状态", AlertLevel.PASS,
                    f"{skip_map[r_status]}，无需证书", ""))
                continue

            # 找同层级证书比对
            matched = False
            for gr in cert_groups:
                if not _compare_level(r_level, gr["level"]): continue
                cert_school = ""
                for f in [gr.get("degree_fields",{}), gr.get("grad_fields",{})]:
                    cert_school = f.get("school","");
                    if cert_school: break
                school_ok = cert_school and (cert_school == r_school or r_school in cert_school or cert_school in r_school)
                cert_major = ""
                for f in [gr.get("degree_fields",{}), gr.get("grad_fields",{})]:
                    cert_major = f.get("major","");
                    if cert_major: break
                major_ok = _major_contains(cert_major, r_major) != "mismatch"
                cert_year = ""
                for f in [gr.get("degree_fields",{}), gr.get("grad_fields",{})]:
                    d = f.get("graduation_date","");
                    if d: cert_year = _extract_year(d); break
                year_ok = (r_end == cert_year) if r_end and cert_year else True

                matched = True
                msgs = []
                if not school_ok: msgs.append(f"学校不一致(证书'{cert_school}' vs 简历'{r_school}')")
                if not major_ok: msgs.append(f"专业不一致(证书'{cert_major}' vs 简历'{r_major}')")
                if r_end and cert_year and not year_ok: msgs.append(f"年份不一致(证书{cert_year} vs 简历{r_end})")
                all_ok = school_ok and major_ok and year_ok
                if all_ok:
                    checks.append(CheckItem(f"简历·{r_level}: 交叉比对", AlertLevel.PASS,
                        f"全部一致 — {r_school} {r_major} {r_end}", ""))
                else:
                    checks.append(CheckItem(f"简历·{r_level}: 交叉比对", AlertLevel.REVIEW,
                        "; ".join(msgs), f"简历:{r_school} {r_major} {r_end}"))
                break

            if not matched:
                now = datetime.now().year
                if not r_end or not r_end.isdigit():
                    checks.append(CheckItem(f"简历·{r_level}: 毕业状态", AlertLevel.REVIEW,
                        f"缺证，无法判定毕业年份", f"简历:{r_start or '?'}-{r_end or '?'}"))
                elif int(r_end) < now:
                    checks.append(CheckItem(f"简历·{r_level}: 毕业状态", AlertLevel.REVIEW,
                        f"已毕业但缺证 — 应于{r_end}年毕业", "", severity="high"))
                elif int(r_end) == now:
                    checks.append(CheckItem(f"简历·{r_level}: 毕业状态", AlertLevel.REVIEW,
                        f"应届待取证 — 预计{r_end}年毕业", "", severity="low"))
                else:
                    checks.append(CheckItem(f"简历·{r_level}: 毕业状态", AlertLevel.PASS,
                        f"在读中，暂无需证书 — 预计{r_end}年毕业", ""))

    return checks


# ═══════════════════════════════════════════
# 综合核验 (三层递进)
# ═══════════════════════════════════════════
def verify_all_certs(cert_groups: list, resume_education: list = None) -> dict:
    all_checks = []

    # ─── 收集图片路径 (带标签) ───
    labeled_images = []
    for g in cert_groups:
        level = g["level"]
        for cert_type, k in [("学位证","degree_img"),("毕业证","grad_img")]:
            fp = g.get(k,"")
            if fp:
                labeled_images.append((f"{level}·{cert_type}", fp))

    # ─── Layer 1: 图片篡改检测 ───
    l1_checks, _ = layer1_ela_check(labeled_images)
    all_checks.extend(l1_checks)

    # ─── Layer 2: 学信库核验 (每个证书) ───
    for g in cert_groups:
        level = g["level"]
        for cert_type, key in [("学位证","degree_fields"),("毕业证","grad_fields")]:
            fd = g.get(key)
            if not fd: continue
            name = fd.get("name","")
            cert_label = f"{level}·{cert_type}·{name}" if name else f"{level}·{cert_type}"
            l2_checks, _ = layer2_chsi_verify(fd, cert_label)
            all_checks.extend(l2_checks)

    # ─── Layer 3: 交叉核验 ───
    l3_checks = layer3_cross_verify(cert_groups, resume_education)
    all_checks.extend(l3_checks)

    # ─── 综合判定（取三层中最严重的） ───
    has_issue = any(c.level == AlertLevel.REVIEW for c in all_checks)
    if has_issue:
        has_high = any(c.severity == "high" for c in all_checks)
        final, summary = AlertLevel.REVIEW, (
            "存在高危异常，需HR判定" if has_high else "存在可疑项，需HR复核")
    else:
        final, summary = AlertLevel.PASS, "三层核验全部通过"

    return {
        "final": final,
        "final_summary": summary,
        "all_checks": [asdict(c) for c in all_checks],
    }
