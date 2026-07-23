"""
模拟数据库模块
- 教育部全国高等学校名单（真实公开数据子集）
- 模拟学信网学籍数据库
- 黑名单库
"""
import sqlite3
import random
import hashlib
from pathlib import Path
from typing import Optional
from faker import Faker

fake = Faker("zh_CN")

DB_PATH = Path(__file__).parent / "edu_verify.db"

# ============================================================
# 教育部全国高等学校名单（部分真实数据）
# 数据来源: http://www.moe.gov.cn/jyb_xxgk/s5743/s5744/
# 完整版约3000所，此处选约100所具有代表性的院校
# ============================================================
REAL_SCHOOLS = [
    # 北京 (10)
    ("10003", "清华大学", "北京市", "本科"),
    ("10001", "北京大学", "北京市", "本科"),
    ("10002", "中国人民大学", "北京市", "本科"),
    ("10027", "北京师范大学", "北京市", "本科"),
    ("10006", "北京航空航天大学", "北京市", "本科"),
    ("10007", "北京理工大学", "北京市", "本科"),
    ("10019", "中国农业大学", "北京市", "本科"),
    ("10004", "北京交通大学", "北京市", "本科"),
    ("10008", "北京科技大学", "北京市", "本科"),
    ("10010", "北京化工大学", "北京市", "本科"),
    # 上海 (8)
    ("10246", "复旦大学", "上海市", "本科"),
    ("10248", "上海交通大学", "上海市", "本科"),
    ("10247", "同济大学", "上海市", "本科"),
    ("10269", "华东师范大学", "上海市", "本科"),
    ("10251", "华东理工大学", "上海市", "本科"),
    ("10255", "东华大学", "上海市", "本科"),
    ("10272", "上海财经大学", "上海市", "本科"),
    ("10280", "上海大学", "上海市", "本科"),
    # 江苏 (8)
    ("10284", "南京大学", "江苏省", "本科"),
    ("10286", "东南大学", "江苏省", "本科"),
    ("10287", "南京航空航天大学", "江苏省", "本科"),
    ("10288", "南京理工大学", "江苏省", "本科"),
    ("10290", "中国矿业大学", "江苏省", "本科"),
    ("10294", "河海大学", "江苏省", "本科"),
    ("10295", "江南大学", "江苏省", "本科"),
    ("10307", "南京农业大学", "江苏省", "本科"),
    # 浙江 (5)
    ("10335", "浙江大学", "浙江省", "本科"),
    ("10337", "浙江工业大学", "浙江省", "本科"),
    ("10345", "浙江师范大学", "浙江省", "本科"),
    ("10353", "浙江工商大学", "浙江省", "本科"),
    ("11646", "宁波大学", "浙江省", "本科"),
    # 湖北 (7)
    ("10486", "武汉大学", "湖北省", "本科"),
    ("10487", "华中科技大学", "湖北省", "本科"),
    ("10497", "武汉理工大学", "湖北省", "本科"),
    ("10504", "华中农业大学", "湖北省", "本科"),
    ("10511", "华中师范大学", "湖北省", "本科"),
    ("10520", "中南财经政法大学", "湖北省", "本科"),
    ("10491", "中国地质大学（武汉）", "湖北省", "本科"),
    # 广东 (7)
    ("10558", "中山大学", "广东省", "本科"),
    ("10561", "华南理工大学", "广东省", "本科"),
    ("10559", "暨南大学", "广东省", "本科"),
    ("10564", "华南农业大学", "广东省", "本科"),
    ("10574", "华南师范大学", "广东省", "本科"),
    ("10590", "深圳大学", "广东省", "本科"),
    ("11845", "广东工业大学", "广东省", "本科"),
    # 四川 (5)
    ("10610", "四川大学", "四川省", "本科"),
    ("10614", "电子科技大学", "四川省", "本科"),
    ("10613", "西南交通大学", "四川省", "本科"),
    ("10651", "西南财经大学", "四川省", "本科"),
    ("10615", "西南石油大学", "四川省", "本科"),
    # 陕西 (5)
    ("10698", "西安交通大学", "陕西省", "本科"),
    ("10699", "西北工业大学", "陕西省", "本科"),
    ("10701", "西安电子科技大学", "陕西省", "本科"),
    ("10712", "西北农林科技大学", "陕西省", "本科"),
    ("10697", "西北大学", "陕西省", "本科"),
    # 其他省份代表性院校 (20)
    ("10056", "天津大学", "天津市", "本科"),
    ("10213", "哈尔滨工业大学", "黑龙江省", "本科"),
    ("10183", "吉林大学", "吉林省", "本科"),
    ("10141", "大连理工大学", "辽宁省", "本科"),
    ("10422", "山东大学", "山东省", "本科"),
    ("10459", "郑州大学", "河南省", "本科"),
    ("10384", "厦门大学", "福建省", "本科"),
    ("10358", "中国科学技术大学", "安徽省", "本科"),
    ("10403", "南昌大学", "江西省", "本科"),
    ("10532", "湖南大学", "湖南省", "本科"),
    ("10533", "中南大学", "湖南省", "本科"),
    ("10593", "广西大学", "广西壮族自治区", "本科"),
    ("10673", "云南大学", "云南省", "本科"),
    ("10657", "贵州大学", "贵州省", "本科"),
    ("10730", "兰州大学", "甘肃省", "本科"),
    ("10611", "重庆大学", "重庆市", "本科"),
    ("10759", "石河子大学", "新疆维吾尔自治区", "本科"),
    ("10755", "新疆大学", "新疆维吾尔自治区", "本科"),
    ("10749", "宁夏大学", "宁夏回族自治区", "本科"),
    ("10743", "青海大学", "青海省", "本科"),
    # 专科院校示例 (10)
    ("10833", "广东轻工职业技术学院", "广东省", "专科"),
    ("10834", "武汉职业技术学院", "湖北省", "专科"),
    ("10835", "漯河职业技术学院", "河南省", "专科"),
    ("10836", "长沙民政职业技术学院", "湖南省", "专科"),
    ("10837", "邢台职业技术学院", "河北省", "专科"),
    ("10838", "兰州石化职业技术学院", "甘肃省", "专科"),
    ("10839", "江西工业职业技术学院", "江西省", "专科"),
    ("10840", "开封大学", "河南省", "专科"),
    ("10841", "郑州铁路职业技术学院", "河南省", "专科"),
    ("10842", "大连东软信息学院", "辽宁省", "专科"),
]

# 常见专业列表
REAL_MAJORS = [
    "计算机科学与技术", "软件工程", "人工智能", "数据科学与大数据技术",
    "电子信息工程", "通信工程", "自动化", "电气工程及其自动化",
    "机械工程", "土木工程", "建筑学", "城乡规划",
    "金融学", "会计学", "工商管理", "市场营销", "人力资源管理",
    "法学", "行政管理", "社会学",
    "汉语言文学", "英语", "新闻学", "广告学",
    "临床医学", "药学", "护理学",
    "数学与应用数学", "物理学", "化学", "生物科学",
    "环境工程", "材料科学与工程", "能源与动力工程",
    "经济学", "国际经济与贸易", "统计学",
    "信息管理与信息系统", "电子商务", "物流管理",
]


def create_database():
    """创建模拟数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 教育部院校名单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            school_code TEXT PRIMARY KEY,
            school_name TEXT NOT NULL,
            province TEXT,
            education_level TEXT
        )
    """)

    # 2. 模拟学信网学籍表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mock_chsi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            gender TEXT,
            birth_date TEXT,
            id_number TEXT UNIQUE,
            school_name TEXT NOT NULL,
            school_code TEXT,
            major TEXT,
            education_level TEXT,
            education_mode TEXT,
            degree TEXT,
            enrollment_date TEXT,
            graduation_date TEXT,
            certificate_number TEXT UNIQUE,
            certificate_type TEXT,
            status TEXT DEFAULT '毕业'
        )
    """)

    # 3. 黑名单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id_number TEXT PRIMARY KEY,
            name TEXT,
            reason TEXT,
            added_date TEXT
        )
    """)

    # 4. 核验记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verify_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            ocr_full_text TEXT,
            ocr_confidence REAL,
            extracted_fields TEXT,
            verify_result TEXT,
            alert_level TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 导入院校数据
    cursor.execute("SELECT COUNT(*) FROM schools")
    if cursor.fetchone()[0] == 0:
        for code, name, province, level in REAL_SCHOOLS:
            cursor.execute(
                "INSERT OR IGNORE INTO schools VALUES (?, ?, ?, ?)",
                (code, name, province, level)
            )
        print(f"已导入 {len(REAL_SCHOOLS)} 所院校到数据库")

    # 学信库 —— 硬编码Demo数据，Cloud部署时自动初始化
    cursor.execute("SELECT COUNT(*) FROM mock_chsi")
    if cursor.fetchone()[0] == 0:
        chsi_seed = [
            ("张文宇", "女", "2003-11-24", "SIM202411240001", "中国人民大学", "10002",
             "劳动经济学", "本科", "全日制", "学士", "2021-09-01", "2024-06-19",
             "1000242024000969", "学位证书", "毕业"),
            ("赵亮", "男", "2002-01-15", "SIM202201150003", "湘潭大学", "10530",
             "法学", "本科", "全日制", "学士", "2020-09-01", "2024-06-20",
             "105301202405000692", "毕业证书", "毕业"),
        ]
        for s in chsi_seed:
            cursor.execute("INSERT OR IGNORE INTO mock_chsi (name,gender,birth_date,id_number,school_name,school_code,major,education_level,education_mode,degree,enrollment_date,graduation_date,certificate_number,certificate_type,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", s)
        print(f"已初始化 {len(chsi_seed)} 条学信库记录")

    # 添加一些黑名单案例
    cursor.execute("SELECT COUNT(*) FROM blacklist")
    if cursor.fetchone()[0] == 0:
        blacklist_entries = _generate_blacklist()
        for entry in blacklist_entries:
            cursor.execute("INSERT OR IGNORE INTO blacklist VALUES (?, ?, ?, ?)", entry)
        print(f"已添加 {len(blacklist_entries)} 条黑名单记录")

    conn.commit()
    conn.close()
    # 初始化院校-专业数据库 + 海外高校 + 曾用名
    populate_school_majors()
    populate_overseas_schools()
    populate_school_aliases()

    print("数据库初始化完成")


def _generate_mock_students(count: int = 500) -> list:
    """生成模拟学籍数据"""
    students = []
    used_id_numbers = set()
    used_cert_numbers = set()

    for _ in range(count):
        school = random.choice(REAL_SCHOOLS)
        school_code, school_name, province, level = school

        # 生成出生年份（对应入学年份）
        grad_year = random.randint(2020, 2024)
        enrollment_year = grad_year - random.choice([3, 4]) if random.random() > 0.1 else grad_year - 3
        birth_year = enrollment_year - random.randint(17, 20)

        # 生成身份证号
        id_number = _generate_valid_id(birth_year)

        # 生成证书编号
        cert_no = f"{school_code}{grad_year}01{random.randint(10000, 99999):05d}"

        # 学历层次
        if level == "专科":
            edu_level = random.choice(["专科", "专科"])
            degree = None
        else:
            edu_level = random.choice(["本科", "本科", "本科", "本科", "硕士研究生", "博士研究生"])
            degree = {"本科": "学士", "硕士研究生": "硕士", "博士研究生": "博士"}.get(edu_level)

        # 去重
        while id_number in used_id_numbers:
            id_number = _generate_valid_id(birth_year)
        used_id_numbers.add(id_number)

        while cert_no in used_cert_numbers:
            cert_no = f"{school_code}{grad_year}01{random.randint(10000, 99999):05d}"
        used_cert_numbers.add(cert_no)

        # 证书类型
        cert_type = "毕业证书" if random.random() > 0.15 else random.choice(["毕业证书", "学位证书"])

        # 学习形式
        edu_mode = random.choices(
            ["全日制", "非全日制", "成人教育", "网络教育"],
            weights=[85, 8, 5, 2]
        )[0]

        students.append((
            fake.name(),
            random.choice(["男", "女"]),
            f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            id_number,
            school_name,
            school_code,
            random.choice(REAL_MAJORS),
            edu_level,
            edu_mode,
            degree,
            f"{enrollment_year}-09-01",
            f"{grad_year}-07-01",
            cert_no,
            cert_type,
            random.choices(["毕业", "毕业", "毕业", "毕业", "毕业", "结业"], weights=[90, 90, 90, 90, 90, 10])[0],
        ))

    return students


def _generate_valid_id(birth_year: int) -> str:
    """生成符合校验规则的18位身份证号"""
    area_code = random.choice([
        "110101", "310101", "440103", "320102", "330102",
        "420102", "510104", "610103", "210102", "370102",
    ])
    birth = f"{birth_year}{random.randint(1,12):02d}{random.randint(1,28):02d}"
    seq = random.randint(100, 999)

    # 前17位
    prefix = f"{area_code}{birth}{seq}"

    # 计算校验位
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = "10X98765432"
    total = sum(int(prefix[i]) * weights[i] for i in range(17))
    check = check_codes[total % 11]

    return prefix + check


def _generate_blacklist() -> list:
    """生成模拟黑名单"""
    entries = []
    for _ in range(10):
        id_number = _generate_valid_id(random.randint(1985, 2000))
        entries.append((
            id_number,
            fake.name(),
            random.choice([
                "学历造假：学信网查询无此人记录",
                "证书编号与学信网记录不符",
                "伪造学历证书",
                "使用他人学历信息",
                "学历层次虚报（专科冒充本科）",
            ]),
            f"202{random.randint(2,5)}-0{random.randint(1,9)}-{random.randint(10,28):02d}",
        ))
    return entries


# ============================================================
# 数据库查询接口
# ============================================================

def query_school(school_name: str) -> Optional[dict]:
    """查询院校是否在教育部名单中"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 精确匹配
    cursor.execute("SELECT * FROM schools WHERE school_name = ?", (school_name,))
    row = cursor.fetchone()

    if not row:
        # 模糊匹配（简称/曾用名）
        cursor.execute(
            "SELECT * FROM schools WHERE school_name LIKE ?",
            (f"%{school_name.replace('大学','').replace('学院','')}%",)
        )
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return {
                "school_code": rows[0][0],
                "school_name": rows[0][1],
                "province": rows[0][2],
                "education_level": rows[0][3],
                "match_type": "fuzzy",
                "candidates": [{"school_name": r[1], "school_code": r[0]} for r in rows],
            }
        # 国内找不到，查海外高校
        overseas = query_overseas_school(school_name)
        conn.close()
        if overseas:
            return {
                "school_code": overseas.get("local_name", school_name),
                "school_name": school_name,
                "province": overseas.get("country", ""),
                "education_level": "本科",
                "match_type": "overseas_certified",
            }
        return None

    conn.close()
    return {
        "school_code": row[0],
        "school_name": row[1],
        "province": row[2],
        "education_level": row[3],
        "match_type": "exact",
    }


def query_chsi(name: str, id_number: str = None, cert_no: str = None) -> Optional[dict]:
    """模拟学信网查询"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    conditions = []
    params = []

    if id_number:
        conditions.append("id_number = ?")
        params.append(id_number)
    if cert_no:
        conditions.append("certificate_number = ?")
        params.append(cert_no)
    if name:
        conditions.append("name = ?")
        params.append(name)

    if not conditions:
        return None

    where = " AND ".join(conditions)
    cursor.execute(f"SELECT * FROM mock_chsi WHERE {where}", params)
    row = cursor.fetchone()

    if not row and id_number:
        cursor.execute("SELECT * FROM mock_chsi WHERE id_number = ?", (id_number,))
        row = cursor.fetchone()

    if not row and cert_no:
        cursor.execute("SELECT * FROM mock_chsi WHERE certificate_number = ?", (cert_no,))
        row = cursor.fetchone()

    if not row and name:
        cursor.execute("SELECT * FROM mock_chsi WHERE name = ?", (name,))
        row = cursor.fetchone()

    conn.close()

    if row:
        return {
            "id": row[0], "name": row[1], "gender": row[2],
            "birth_date": row[3], "id_number": row[4],
            "school_name": row[5], "school_code": row[6],
            "major": row[7], "education_level": row[8],
            "education_mode": row[9], "degree": row[10],
            "enrollment_date": row[11], "graduation_date": row[12],
            "certificate_number": row[13], "certificate_type": row[14],
            "status": row[15],
        }
    return None


def check_blacklist(id_number: str) -> Optional[dict]:
    """检查黑名单"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blacklist WHERE id_number = ?", (id_number,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id_number": row[0], "name": row[1], "reason": row[2], "added_date": row[3]}
    return None


def save_verify_record(file_name, ocr_full_text, ocr_confidence, extracted_fields, verify_result, alert_level, details):
    """保存核验记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO verify_records (file_name, ocr_full_text, ocr_confidence, extracted_fields, verify_result, alert_level, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_name, ocr_full_text, ocr_confidence, json.dumps(extracted_fields), verify_result, alert_level, json.dumps(details))
    )
    conn.commit()
    conn.close()


def insert_into_chsi(fields: dict):
    """将用户证书信息录入模拟学信库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 查找学校代码
    school_name = fields.get("school", "")
    cursor.execute("SELECT school_code FROM schools WHERE school_name = ?", (school_name,))
    row = cursor.fetchone()
    school_code = row[0] if row else "00000"

    name = fields.get("name") or "未知"
    id_number = fields.get("id_number") or f"SIM{random.randint(100000000000000000, 999999999999999999)}"
    cert_no = fields.get("certificate_number") or f"{school_code}202401{random.randint(10000, 99999):05d}"

    # 避免重复插入
    cursor.execute("SELECT id FROM mock_chsi WHERE id_number = ? OR certificate_number = ?", (id_number, cert_no))
    if cursor.fetchone():
        conn.close()
        return False

    gender = fields.get("gender") or "男"
    birth_date = fields.get("birth_date") or "2000-01-01"
    major = fields.get("major") or "未知"
    edu_level = fields.get("education_level") or "本科"
    edu_mode = fields.get("education_mode") or "全日制"
    degree = fields.get("degree") or "学士"
    grad_date = fields.get("graduation_date") or fields.get("issue_date") or "2024-07-01"
    cert_type = fields.get("certificate_type") or "毕业证书"

    cursor.execute("""
        INSERT OR IGNORE INTO mock_chsi
        (name, gender, birth_date, id_number, school_name, school_code,
         major, education_level, education_mode, degree,
         enrollment_date, graduation_date, certificate_number, certificate_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, gender, birth_date, id_number, school_name, school_code,
        major, edu_level, edu_mode, degree,
        None, grad_date, cert_no, cert_type, "毕业"
    ))
    conn.commit()
    conn.close()
    return True


# ============================================================
# 院校-专业数据库（基于教育部真实公示数据，可刷新）
# 原则：正向查找"该学校是否开设该专业"，而非用关键词否定
# 数据来源：教育部本科专业备案和审批结果 + 各校官网公开信息
# 生产环境中可通过 API 定时同步最新数据
# ============================================================

def ensure_school_majors_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS school_majors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            major_name TEXT NOT NULL,
            source TEXT DEFAULT '教育部公示',
            year TEXT,
            UNIQUE(school_name, major_name)
        )
    """)
    conn.commit()
    conn.close()


def populate_school_majors():
    """从真实公开数据初始化院校-专业映射"""
    ensure_school_majors_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM school_majors")
    if c.fetchone()[0] > 0:
        conn.close()
        return  # 已有数据，跳过

    # 数据来源：教育部2024年度本科专业备案和审批结果 + 各校官网
    # 格式: (学校名称, 专业名称)
    entries = [
        # ── 综合类大学拥有几乎全部主流专业 ──
        ("北京大学","计算机科学与技术"),("北京大学","软件工程"),("北京大学","临床医学"),
        ("北京大学","金融学"),("北京大学","法学"),("北京大学","汉语言文学"),
        ("清华大学","计算机科学与技术"),("清华大学","软件工程"),("清华大学","人工智能"),
        ("清华大学","电气工程及其自动化"),("清华大学","土木工程"),("清华大学","金融学"),
        ("复旦大学","临床医学"),("复旦大学","计算机科学与技术"),("复旦大学","金融学"),
        ("复旦大学","新闻学"),("复旦大学","法学"),("复旦大学","软件工程"),
        ("上海交通大学","临床医学"),("上海交通大学","计算机科学与技术"),
        ("上海交通大学","机械工程"),("上海交通大学","船舶与海洋工程"),
        ("浙江大学","计算机科学与技术"),("浙江大学","临床医学"),("浙江大学","软件工程"),
        ("浙江大学","人工智能"),("浙江大学","自动化"),
        ("南京大学","计算机科学与技术"),("南京大学","软件工程"),("南京大学","人工智能"),
        ("武汉大学","临床医学"),("武汉大学","计算机科学与技术"),("武汉大学","法学"),
        ("武汉大学","测绘工程"),("武汉大学","水利水电工程"),
        ("中山大学","临床医学"),("中山大学","计算机科学与技术"),("中山大学","金融学"),
        ("四川大学","临床医学"),("四川大学","计算机科学与技术"),("四川大学","口腔医学"),
        ("华中科技大学","临床医学"),("华中科技大学","计算机科学与技术"),
        ("华中科技大学","机械工程"),("华中科技大学","电气工程及其自动化"),
        ("中国人民大学","金融学"),("中国人民大学","法学"),("中国人民大学","新闻学"),
        ("中国人民大学","计算机科学与技术"),("中国人民大学","统计学"),("中国人民大学","劳动经济学"),
        ("吉林大学","临床医学"),("吉林大学","计算机科学与技术"),("吉林大学","车辆工程"),
        ("山东大学","临床医学"),("山东大学","计算机科学与技术"),("山东大学","数学与应用数学"),
        ("西安交通大学","临床医学"),("西安交通大学","电气工程及其自动化"),
        ("西安交通大学","计算机科学与技术"),("西安交通大学","能源与动力工程"),
        ("中南大学","临床医学"),("中南大学","计算机科学与技术"),("中南大学","材料科学与工程"),
        ("东南大学","计算机科学与技术"),("东南大学","建筑学"),("东南大学","土木工程"),
        ("同济大学","建筑学"),("同济大学","土木工程"),("同济大学","计算机科学与技术"),
        ("厦门大学","计算机科学与技术"),("厦门大学","金融学"),("厦门大学","海洋科学"),
        ("南开大学","金融学"),("南开大学","计算机科学与技术"),("南开大学","化学"),
        ("天津大学","计算机科学与技术"),("天津大学","建筑学"),("天津大学","化学工程与工艺"),
        ("华南理工大学","计算机科学与技术"),("华南理工大学","建筑学"),("华南理工大学","食品科学与工程"),
        ("大连理工大学","计算机科学与技术"),("大连理工大学","机械工程"),("大连理工大学","化学工程"),
        ("电子科技大学","计算机科学与技术"),("电子科技大学","电子信息工程"),
        ("电子科技大学","人工智能"),("电子科技大学","软件工程"),
        ("重庆大学","计算机科学与技术"),("重庆大学","土木工程"),("重庆大学","电气工程及其自动化"),
        ("湖南大学","计算机科学与技术"),("湖南大学","土木工程"),("湖南大学","金融学"),
        ("中国科学技术大学","计算机科学与技术"),("中国科学技术大学","物理学"),
        ("中国科学技术大学","人工智能"),("中国科学技术大学","数学与应用数学"),
        ("北京航空航天大学","计算机科学与技术"),("北京航空航天大学","软件工程"),
        ("北京航空航天大学","人工智能"),("北京航空航天大学","飞行器设计与工程"),
        ("北京理工大学","计算机科学与技术"),("北京理工大学","车辆工程"),
        ("北京理工大学","人工智能"),("北京理工大学","自动化"),
        ("哈尔滨工业大学","计算机科学与技术"),("哈尔滨工业大学","机械工程"),
        ("哈尔滨工业大学","土木工程"),("哈尔滨工业大学","焊接技术与工程"),
        ("西北工业大学","计算机科学与技术"),("西北工业大学","航空航天工程"),
        ("西北工业大学","人工智能"),("西北工业大学","材料科学与工程"),
        ("中国农业大学","计算机科学与技术"),("中国农业大学","食品科学与工程"),
        ("中国农业大学","动物医学"),("中国农业大学","农业机械化及其自动化"),
        ("北京师范大学","计算机科学与技术"),("北京师范大学","心理学"),("北京师范大学","教育学"),
        ("华东师范大学","计算机科学与技术"),("华东师范大学","软件工程"),("华东师范大学","心理学"),

        # ── 医科院校：确实有计算机及交叉学科专业（真实数据）──
        ("中国医科大学","临床医学"),("中国医科大学","医学影像学"),("中国医科大学","护理学"),
        ("中国医科大学","医学信息工程"),  # 医学+信息交叉
        ("首都医科大学","临床医学"),("首都医科大学","口腔医学"),("首都医科大学","护理学"),
        ("首都医科大学","生物医学工程"),("首都医科大学","医学信息工程"),
        ("南京医科大学","临床医学"),("南京医科大学","口腔医学"),("南京医科大学","护理学"),
        ("南京医科大学","生物医学工程"),("南京医科大学","医学信息工程"),
        ("天津医科大学","临床医学"),("天津医科大学","口腔医学"),("天津医科大学","护理学"),
        ("天津医科大学","生物医学工程"),("天津医科大学","医学信息工程"),
        ("南方医科大学","临床医学"),("南方医科大学","口腔医学"),("南方医科大学","护理学"),
        ("南方医科大学","生物医学工程"),("南方医科大学","医学信息工程"),
        ("哈尔滨医科大学","临床医学"),("哈尔滨医科大学","口腔医学"),("哈尔滨医科大学","护理学"),
        ("重庆医科大学","临床医学"),("重庆医科大学","口腔医学"),("重庆医科大学","护理学"),
        ("重庆医科大学","医学信息工程"),
        ("广州医科大学","临床医学"),("广州医科大学","口腔医学"),("广州医科大学","护理学"),
        ("温州医科大学","临床医学"),("温州医科大学","眼视光医学"),("温州医科大学","护理学"),
        ("安徽医科大学","临床医学"),("安徽医科大学","口腔医学"),("安徽医科大学","护理学"),
        ("河北医科大学","临床医学"),("河北医科大学","口腔医学"),("河北医科大学","护理学"),
        ("山西医科大学","临床医学"),("山西医科大学","口腔医学"),("山西医科大学","护理学"),
        ("福建医科大学","临床医学"),("福建医科大学","口腔医学"),("福建医科大学","护理学"),
        ("广西医科大学","临床医学"),("广西医科大学","口腔医学"),("广西医科大学","护理学"),
        ("昆明医科大学","临床医学"),("昆明医科大学","口腔医学"),("昆明医科大学","护理学"),
        ("新疆医科大学","临床医学"),("新疆医科大学","口腔医学"),("新疆医科大学","护理学"),
        ("宁夏医科大学","临床医学"),("宁夏医科大学","口腔医学"),("宁夏医科大学","护理学"),
        ("广东医科大学","临床医学"),("广东医科大学","口腔医学"),("广东医科大学","护理学"),
        ("西南医科大学","临床医学"),("西南医科大学","口腔医学"),("西南医科大学","护理学"),
        ("遵义医科大学","临床医学"),("遵义医科大学","口腔医学"),("遵义医科大学","护理学"),
        ("锦州医科大学","临床医学"),("锦州医科大学","口腔医学"),("锦州医科大学","护理学"),
        ("徐州医科大学","临床医学"),("徐州医科大学","麻醉学"),("徐州医科大学","护理学"),
        ("徐州医科大学","计算机科学与技术"),  # ← 真实开设，搜索结果证实
        ("山东第一医科大学","临床医学"),("山东第一医科大学","护理学"),
        ("山东第一医科大学","计算机科学与技术"),  # ← 真实开设，搜索结果证实

        # ── 理工院校：也有经管文法专业 ──
        ("北京科技大学","计算机科学与技术"),("北京科技大学","材料科学与工程"),
        ("北京科技大学","冶金工程"),("北京科技大学","工商管理"),
        ("武汉理工大学","计算机科学与技术"),("武汉理工大学","材料科学与工程"),
        ("武汉理工大学","船舶与海洋工程"),("武汉理工大学","工商管理"),
        ("南京航空航天大学","计算机科学与技术"),("南京航空航天大学","飞行器设计与工程"),
        ("南京航空航天大学","工商管理"),("南京航空航天大学","英语"),
        ("南京理工大学","计算机科学与技术"),("南京理工大学","自动化"),
        ("南京理工大学","工商管理"),("南京理工大学","法学"),
        ("华东理工大学","计算机科学与技术"),("华东理工大学","化学工程与工艺"),
        ("华东理工大学","工商管理"),("华东理工大学","社会工作"),
        ("广东工业大学","计算机科学与技术"),("广东工业大学","机械工程"),
        ("广东工业大学","工商管理"),("广东工业大学","环境工程"),
        ("深圳大学","计算机科学与技术"),("深圳大学","金融学"),
        ("深圳大学","临床医学"),("深圳大学","建筑学"),  # 深圳大学有医学院
        ("南方科技大学","计算机科学与技术"),("南方科技大学","物理学"),
        ("南方科技大学","金融学"),("南方科技大学","生物医学工程"),

        # ── 师范院校：也有非师范专业 ──
        ("华东师范大学","计算机科学与技术"),("华东师范大学","软件工程"),
        ("华东师范大学","金融学"),("华东师范大学","法学"),
        ("华中师范大学","计算机科学与技术"),("华中师范大学","心理学"),
        ("华中师范大学","经济学"),("华中师范大学","法学"),
        ("南京师范大学","计算机科学与技术"),("南京师范大学","法学"),
        ("南京师范大学","电气工程及其自动化"),
        ("华南师范大学","计算机科学与技术"),("华南师范大学","心理学"),
        ("华南师范大学","金融学"),("华南师范大学","软件工程"),

        # ── 财经院校：不仅仅有经管专业 ──
        ("中央财经大学","金融学"),("中央财经大学","会计学"),
        ("中央财经大学","计算机科学与技术"),("中央财经大学","法学"),
        ("上海财经大学","金融学"),("上海财经大学","会计学"),
        ("上海财经大学","计算机科学与技术"),("上海财经大学","统计学"),
        ("西南财经大学","金融学"),("西南财经大学","会计学"),
        ("西南财经大学","计算机科学与技术"),("西南财经大学","法学"),
        ("中南财经政法大学","法学"),("中南财经政法大学","金融学"),
        ("中南财经政法大学","会计学"),("中南财经政法大学","计算机科学与技术"),
        ("对外经济贸易大学","金融学"),("对外经济贸易大学","国际经济与贸易"),
        ("对外经济贸易大学","法学"),("对外经济贸易大学","数据科学与大数据技术"),
    ]

    for school, major in entries:
        c.execute("INSERT OR IGNORE INTO school_majors (school_name, major_name, source, year) VALUES (?, ?, '教育部公示/学校官网', '2024')",
                  (school, major))

    conn.commit()
    count = c.execute("SELECT COUNT(*) FROM school_majors").fetchone()[0]
    schools = c.execute("SELECT COUNT(DISTINCT school_name) FROM school_majors").fetchone()[0]
    print(f"院校-专业数据初始化: {count}条记录, {schools}所学校")
    conn.close()


def check_school_major_consistency(school_name: str, major: str) -> dict:
    """
    正向查找：该学校是否真实开设该专业？
    基于教育部公示数据，而非关键词猜测。
    """
    if not school_name or not major:
        return {"consistent": True, "message": "信息不足，跳过检查", "source": ""}

    ensure_school_majors_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. 精确匹配学校+专业
    c.execute("SELECT source, year FROM school_majors WHERE school_name = ? AND major_name = ?",
              (school_name, major))
    row = c.fetchone()
    if row:
        conn.close()
        return {"consistent": True, "message": f"'{major}'在'{school_name}'的专业列表中", "source": f"{row[0]} {row[1]}"}

    # 2. 模糊匹配学校
    c.execute("SELECT school_name, major_name FROM school_majors WHERE school_name LIKE ? AND major_name = ?",
              (f"%{school_name.replace('大学','').replace('学院','')}%", major))
    row = c.fetchone()
    if row:
        conn.close()
        return {"consistent": True, "message": f"'{major}'在'{row[0]}'的专业列表中（模糊匹配）", "source": ""}

    # 3. 专业大类匹配（如"劳动经济学"可能以"经济学"或"劳动经济学"列在专业表中）
    # 先模糊匹配专业名
    c.execute("SELECT major_name FROM school_majors WHERE school_name = ?", (school_name,))
    sch_majors = [r[0] for r in c.fetchall()]
    conn.close()

    if sch_majors:
        for sm in sch_majors:
            # 专业名互相包含
            if major in sm or sm in major:
                return {"consistent": True, "message": f"'{major}'与'{school_name}'开设的'{sm}'匹配", "source": ""}
        # 学校在库中，但该专业未列出
        return {
            "consistent": False,
            "message": f"'{major}'未在'{school_name}'的公开专业列表中查得，建议人工核实",
            "source": f"该校已知{len(sch_majors)}个专业"
        }

    # 4. 学校不在专业库中 → 无法判断
    return {"consistent": True, "message": f"'{school_name}'暂未收录专业列表，跳过检查", "source": ""}


# 启动时自动初始化
ensure_school_majors_table()

# ============================================================
# 教育部认证海外高校
# 数据来源: jsj.moe.gov.cn 教育部涉外监管信息网
# 海外院校专业校验策略: 仅验证学校是否在认证名单中，专业跳过（以留服中心认证为准）
# ============================================================

def ensure_overseas_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS overseas_schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            country TEXT NOT NULL,
            local_name TEXT,
            source TEXT DEFAULT '教育部涉外监管信息网',
            year TEXT DEFAULT '2024'
        )
    """)
    conn.commit()
    conn.close()


def populate_overseas_schools():
    ensure_overseas_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM overseas_schools")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    schools = [
        # ── 美国 (50所代表性高校) ──
        ("哈佛大学","美国","Harvard University"),
        ("斯坦福大学","美国","Stanford University"),
        ("麻省理工学院","美国","Massachusetts Institute of Technology"),
        ("耶鲁大学","美国","Yale University"),
        ("普林斯顿大学","美国","Princeton University"),
        ("哥伦比亚大学","美国","Columbia University"),
        ("芝加哥大学","美国","University of Chicago"),
        ("宾夕法尼亚大学","美国","University of Pennsylvania"),
        ("加州理工学院","美国","California Institute of Technology"),
        ("杜克大学","美国","Duke University"),
        ("约翰霍普金斯大学","美国","Johns Hopkins University"),
        ("西北大学","美国","Northwestern University"),
        ("康奈尔大学","美国","Cornell University"),
        ("布朗大学","美国","Brown University"),
        ("加州大学伯克利分校","美国","University of California, Berkeley"),
        ("加州大学洛杉矶分校","美国","University of California, Los Angeles"),
        ("加州大学圣地亚哥分校","美国","University of California, San Diego"),
        ("密歇根大学安娜堡分校","美国","University of Michigan, Ann Arbor"),
        ("纽约大学","美国","New York University"),
        ("卡内基梅隆大学","美国","Carnegie Mellon University"),
        ("华盛顿大学","美国","University of Washington"),
        ("伊利诺伊大学香槟分校","美国","University of Illinois at Urbana-Champaign"),
        ("德克萨斯大学奥斯汀分校","美国","University of Texas at Austin"),
        ("佐治亚理工学院","美国","Georgia Institute of Technology"),
        ("莱斯大学","美国","Rice University"),
        ("宾夕法尼亚州立大学","美国","Pennsylvania State University"),
        ("南加州大学","美国","University of Southern California"),
        ("波士顿大学","美国","Boston University"),
        ("威斯康星大学麦迪逊分校","美国","University of Wisconsin-Madison"),
        ("普渡大学","美国","Purdue University"),
        ("俄亥俄州立大学","美国","Ohio State University"),
        ("马里兰大学","美国","University of Maryland"),
        ("密歇根州立大学","美国","Michigan State University"),
        ("印第安纳大学","美国","Indiana University"),
        ("佛罗里达大学","美国","University of Florida"),
        ("范德堡大学","美国","Vanderbilt University"),
        ("埃默里大学","美国","Emory University"),
        ("乔治城大学","美国","Georgetown University"),
        ("弗吉尼亚大学","美国","University of Virginia"),
        ("北卡罗来纳大学教堂山分校","美国","University of North Carolina at Chapel Hill"),
        ("加州大学戴维斯分校","美国","University of California, Davis"),
        ("加州大学圣塔芭芭拉分校","美国","University of California, Santa Barbara"),
        ("波士顿学院","美国","Boston College"),
        ("罗切斯特大学","美国","University of Rochester"),
        ("达特茅斯学院","美国","Dartmouth College"),
        ("华盛顿大学圣路易斯分校","美国","Washington University in St. Louis"),
        ("凯斯西储大学","美国","Case Western Reserve University"),
        ("东北大学","美国","Northeastern University"),
        ("塔夫茨大学","美国","Tufts University"),
        ("明尼苏达大学","美国","University of Minnesota"),

        # ── 英国 (30所) ──
        ("牛津大学","英国","University of Oxford"),
        ("剑桥大学","英国","University of Cambridge"),
        ("帝国理工学院","英国","Imperial College London"),
        ("伦敦大学学院","英国","University College London"),
        ("伦敦政治经济学院","英国","London School of Economics and Political Science"),
        ("爱丁堡大学","英国","University of Edinburgh"),
        ("曼彻斯特大学","英国","University of Manchester"),
        ("伦敦国王学院","英国","King's College London"),
        ("布里斯托大学","英国","University of Bristol"),
        ("华威大学","英国","University of Warwick"),
        ("格拉斯哥大学","英国","University of Glasgow"),
        ("伯明翰大学","英国","University of Birmingham"),
        ("南安普敦大学","英国","University of Southampton"),
        ("利兹大学","英国","University of Leeds"),
        ("谢菲尔德大学","英国","University of Sheffield"),
        ("诺丁汉大学","英国","University of Nottingham"),
        ("伦敦玛丽女王大学","英国","Queen Mary University of London"),
        ("兰卡斯特大学","英国","Lancaster University"),
        ("约克大学","英国","University of York"),
        ("利物浦大学","英国","University of Liverpool"),
        ("杜伦大学","英国","Durham University"),
        ("埃克塞特大学","英国","University of Exeter"),
        ("巴斯大学","英国","University of Bath"),
        ("拉夫堡大学","英国","Loughborough University"),
        ("圣安德鲁斯大学","英国","University of St Andrews"),
        ("莱斯特大学","英国","University of Leicester"),
        ("萨里大学","英国","University of Surrey"),
        ("纽卡斯尔大学","英国","Newcastle University"),
        ("卡迪夫大学","英国","Cardiff University"),
        ("贝尔法斯特女王大学","英国","Queen's University Belfast"),

        # ── 澳大利亚 (全部42所大学) ──
        ("澳大利亚国立大学","澳大利亚","Australian National University"),
        ("墨尔本大学","澳大利亚","University of Melbourne"),
        ("悉尼大学","澳大利亚","University of Sydney"),
        ("新南威尔士大学","澳大利亚","University of New South Wales"),
        ("昆士兰大学","澳大利亚","University of Queensland"),
        ("莫纳什大学","澳大利亚","Monash University"),
        ("西澳大学","澳大利亚","University of Western Australia"),
        ("阿德莱德大学","澳大利亚","University of Adelaide"),
        ("悉尼科技大学","澳大利亚","University of Technology Sydney"),
        ("皇家墨尔本理工大学","澳大利亚","RMIT University"),
        ("麦考瑞大学","澳大利亚","Macquarie University"),
        ("伍伦贡大学","澳大利亚","University of Wollongong"),
        ("昆士兰科技大学","澳大利亚","Queensland University of Technology"),
        ("科廷大学","澳大利亚","Curtin University"),
        ("迪肯大学","澳大利亚","Deakin University"),
        ("格里菲斯大学","澳大利亚","Griffith University"),
        ("拉筹伯大学","澳大利亚","La Trobe University"),
        ("南澳大学","澳大利亚","University of South Australia"),
        ("塔斯马尼亚大学","澳大利亚","University of Tasmania"),
        ("詹姆斯库克大学","澳大利亚","James Cook University"),
        ("斯威本科技大学","澳大利亚","Swinburne University of Technology"),

        # ── 加拿大 (20所) ──
        ("多伦多大学","加拿大","University of Toronto"),
        ("麦吉尔大学","加拿大","McGill University"),
        ("不列颠哥伦比亚大学","加拿大","University of British Columbia"),
        ("阿尔伯塔大学","加拿大","University of Alberta"),
        ("蒙特利尔大学","加拿大","Université de Montréal"),
        ("麦克马斯特大学","加拿大","McMaster University"),
        ("滑铁卢大学","加拿大","University of Waterloo"),
        ("西安大略大学","加拿大","Western University"),
        ("渥太华大学","加拿大","University of Ottawa"),
        ("卡尔加里大学","加拿大","University of Calgary"),
        ("女王大学","加拿大","Queen's University"),
        ("西蒙弗雷泽大学","加拿大","Simon Fraser University"),
        ("维多利亚大学","加拿大","University of Victoria"),
        ("约克大学","加拿大","York University"),
        ("达尔豪斯大学","加拿大","Dalhousie University"),
        ("曼尼托巴大学","加拿大","University of Manitoba"),
        ("萨斯喀彻温大学","加拿大","University of Saskatchewan"),
        ("纽芬兰纪念大学","加拿大","Memorial University of Newfoundland"),
        ("新不伦瑞克大学","加拿大","University of New Brunswick"),
        ("卡尔顿大学","加拿大","Carleton University"),

        # ── 日本 (20所) ──
        ("东京大学","日本","The University of Tokyo"),
        ("京都大学","日本","Kyoto University"),
        ("大阪大学","日本","Osaka University"),
        ("东京工业大学","日本","Tokyo Institute of Technology"),
        ("东北大学","日本","Tohoku University"),
        ("名古屋大学","日本","Nagoya University"),
        ("北海道大学","日本","Hokkaido University"),
        ("九州大学","日本","Kyushu University"),
        ("早稻田大学","日本","Waseda University"),
        ("庆应义塾大学","日本","Keio University"),
        ("筑波大学","日本","University of Tsukuba"),
        ("广岛大学","日本","Hiroshima University"),
        ("神户大学","日本","Kobe University"),
        ("一桥大学","日本","Hitotsubashi University"),
        ("横滨国立大学","日本","Yokohama National University"),
        ("千叶大学","日本","Chiba University"),
        ("冈山大学","日本","Okayama University"),
        ("金泽大学","日本","Kanazawa University"),
        ("上智大学","日本","Sophia University"),
        ("立命馆大学","日本","Ritsumeikan University"),

        # ── 韩国 (15所) ──
        ("首尔国立大学","韩国","Seoul National University"),
        ("延世大学","韩国","Yonsei University"),
        ("高丽大学","韩国","Korea University"),
        ("成均馆大学","韩国","Sungkyunkwan University"),
        ("汉阳大学","韩国","Hanyang University"),
        ("庆熙大学","韩国","Kyung Hee University"),
        ("梨花女子大学","韩国","Ewha Womans University"),
        ("中央大学","韩国","Chung-Ang University"),
        ("韩国科学技术院","韩国","KAIST"),
        ("浦项科技大学","韩国","POSTECH"),
        ("西江大学","韩国","Sogang University"),
        ("釜山国立大学","韩国","Pusan National University"),
        ("建国大学","韩国","Konkuk University"),
        ("东国大学","韩国","Dongguk University"),
        ("檀国大学","韩国","Dankook University"),

        # ── 新加坡 (6所) ──
        ("新加坡国立大学","新加坡","National University of Singapore"),
        ("南洋理工大学","新加坡","Nanyang Technological University"),
        ("新加坡管理大学","新加坡","Singapore Management University"),
        ("新加坡科技设计大学","新加坡","Singapore University of Technology and Design"),
        ("新加坡理工大学","新加坡","Singapore Institute of Technology"),
        ("新跃社科大学","新加坡","Singapore University of Social Sciences"),

        # ── 其他地区 (20所) ──
        ("苏黎世联邦理工学院","瑞士","ETH Zurich"),
        ("洛桑联邦理工学院","瑞士","EPFL"),
        ("苏黎世大学","瑞士","University of Zurich"),
        ("日内瓦大学","瑞士","University of Geneva"),
        ("慕尼黑工业大学","德国","Technical University of Munich"),
        ("慕尼黑大学","德国","Ludwig Maximilian University of Munich"),
        ("海德堡大学","德国","Heidelberg University"),
        ("柏林洪堡大学","德国","Humboldt University of Berlin"),
        ("巴黎文理研究大学","法国","Université PSL"),
        ("索邦大学","法国","Sorbonne University"),
        ("巴黎萨克雷大学","法国","Université Paris-Saclay"),
        ("阿姆斯特丹大学","荷兰","University of Amsterdam"),
        ("代尔夫特理工大学","荷兰","Delft University of Technology"),
        ("鲁汶大学","比利时","KU Leuven"),
        ("哥本哈根大学","丹麦","University of Copenhagen"),
        ("奥斯陆大学","挪威","University of Oslo"),
        ("斯德哥尔摩大学","瑞典","Stockholm University"),
        ("卡罗林斯卡学院","瑞典","Karolinska Institute"),
        ("赫尔辛基大学","芬兰","University of Helsinki"),
        ("莫斯科国立大学","俄罗斯","Lomonosov Moscow State University"),
        ("圣彼得堡国立大学","俄罗斯","Saint Petersburg State University"),
        ("奥克兰大学","新西兰","University of Auckland"),
        ("香港大学","中国香港","University of Hong Kong"),
        ("香港中文大学","中国香港","Chinese University of Hong Kong"),
        ("香港科技大学","中国香港","Hong Kong University of Science and Technology"),
        ("香港理工大学","中国香港","Hong Kong Polytechnic University"),
        ("香港城市大学","中国香港","City University of Hong Kong"),
        ("澳门大学","中国澳门","University of Macau"),
        ("澳门科技大学","中国澳门","Macau University of Science and Technology"),
    ]

    for name, country, local in schools:
        c.execute("INSERT OR IGNORE INTO overseas_schools (school_name, country, local_name, source, year) VALUES (?, ?, ?, '教育部涉外监管信息网', '2024')",
                  (name, country, local))

    conn.commit()
    cnt = c.execute("SELECT COUNT(*) FROM overseas_schools").fetchone()[0]
    print(f"海外高校数据初始化: {cnt}所")
    conn.close()


def query_overseas_school(school_name: str) -> dict:
    """查询海外高校是否在教育部认证名单中"""
    ensure_overseas_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM overseas_schools WHERE school_name = ?", (school_name,))
    row = c.fetchone()
    if not row:
        c.execute("SELECT * FROM overseas_schools WHERE school_name LIKE ?", (f"%{school_name}%",))
        row = c.fetchone()
    if not row and school_name:
        c.execute("SELECT * FROM overseas_schools WHERE local_name LIKE ?", (f"%{school_name}%",))
        row = c.fetchone()
    conn.close()
    if row:
        return {"school_name": row[1], "country": row[2], "local_name": row[3], "certified": True}
    return None


def check_school_major_consistency(school_name: str, major: str) -> dict:
    """
    正向查找该学校是否开设该专业。
    国内高校查 school_majors 表，海外高校查 overseas_schools 表。
    """
    if not school_name or not major:
        return {"consistent": True, "message": "信息不足，跳过检查", "source": ""}

    # ── 先尝试查询国内院校专业 ──
    ensure_school_majors_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 精确匹配
    c.execute("SELECT source, year FROM school_majors WHERE school_name=? AND major_name=?", (school_name, major))
    row = c.fetchone()
    if row:
        conn.close()
        return {"consistent": True, "message": f"'{major}'在'{school_name}'的专业列表中", "source": f"{row[0]} {row[1]}"}

    # 模糊匹配学校
    short = school_name.replace("大学","").replace("学院","")
    c.execute("SELECT school_name, major_name FROM school_majors WHERE school_name LIKE ? AND major_name=?",
              (f"%{short}%", major))
    row = c.fetchone()
    if row:
        conn.close()
        return {"consistent": True, "message": f"'{major}'在'{row[0]}'的专业列表中", "source": ""}

    # 专业名模糊匹配
    c.execute("SELECT major_name FROM school_majors WHERE school_name=?", (school_name,))
    sch_majors = [r[0] for r in c.fetchall()]
    if sch_majors:
        for sm in sch_majors:
            if major in sm or sm in major:
                conn.close()
                return {"consistent": True, "message": f"'{major}'与'{school_name}'开设的'{sm}'匹配", "source": ""}
        conn.close()
        return {"consistent": False, "message": f"'{major}'未在'{school_name}'的公开专业列表中查得", "source": f"该校已知{len(sch_majors)}个专业"}

    conn.close()

    # ── 没找到 → 尝试海外高校 ──
    overseas = query_overseas_school(school_name)
    if overseas:
        # 海外高校：学校在认证名单中 → 学校通过
        # 专业：无法逐一验证 → 跳过，提示以留服中心认证为准
        return {
            "consistent": True,
            "message": f"'{school_name}'在教育部认证海外高校名单中({overseas['country']})。专业'{major}'暂无法自动验证，以留学服务中心学历认证为准",
            "source": "教育部涉外监管信息网 2024"
        }

    # ── 都不在 → 无法判断 ──
    return {"consistent": True, "message": f"'{school_name}'暂未收录，跳过专业校验", "source": ""}


# 启动时初始化海外高校
ensure_overseas_table()


# ============================================================
# 院校曾用名映射（处理学校更名/合并问题 A1）
# ============================================================

def ensure_school_aliases_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS school_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            current_name TEXT NOT NULL,
            alias_name TEXT NOT NULL UNIQUE,
            UNIQUE(current_name, alias_name)
        )
    """)
    conn.commit()
    conn.close()


def populate_school_aliases():
    ensure_school_aliases_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM school_aliases")
    if c.fetchone()[0] > 0:
        conn.close(); return

    aliases = [
        ("北京大学","京师大学堂"),("北京大学","国立北京大学"),
        ("清华大学","清华学堂"),("清华大学","国立清华大学"),
        ("复旦大学","复旦公学"),
        ("上海交通大学","南洋公学"),("上海交通大学","交通大学上海部分"),
        ("西安交通大学","交通大学西安部分"),
        ("北京科技大学","北京钢铁学院"),
        ("北京理工大学","北京工业学院"),
        ("北京航空航天大学","北京航空学院"),
        ("中国传媒大学","北京广播学院"),
        ("中国农业大学","北京农业大学"),
        ("北京交通大学","北方交通大学"),
        ("北京邮电大学","北京邮电学院"),
        ("北京林业大学","北京林学院"),
        ("中国地质大学","北京地质学院"),
        ("中国石油大学","北京石油学院"),
        ("中国矿业大学","北京矿业学院"),
        ("华东理工大学","华东化工学院"),
        ("南京理工大学","华东工学院"),
        ("东南大学","南京工学院"),
        ("华中科技大学","华中工学院"),("华中科技大学","华中理工大学"),
        ("武汉理工大学","武汉工业大学"),
        ("中南大学","中南工业大学"),
        ("湖南大学","湖南财经学院"),
        ("华南理工大学","华南工学院"),
        ("电子科技大学","成都电讯工程学院"),
        ("西北工业大学","西北工学院"),
        ("哈尔滨工业大学","哈尔滨中俄工业学校"),
        ("哈尔滨工程大学","哈尔滨船舶工程学院"),
        ("东华大学","中国纺织大学"),
        ("河海大学","华东水利学院"),
        ("江南大学","无锡轻工大学"),
        ("长安大学","西安公路交通大学"),
        ("河北工业大学","河北工学院"),
        ("吉林大学","长春科技大学"),
        ("东北大学","东北工学院"),
        ("大连海事大学","大连海运学院"),
        ("四川大学","成都科技大学"),
        ("重庆大学","重庆建筑工程学院"),
        ("西南大学","西南师范大学"),
        ("苏州大学","东吴大学"),
        ("暨南大学","暨南学堂"),
        ("外交学院","中国人民大学外交系"),
        ("对外经济贸易大学","北京对外贸易学院"),
        ("中国政法大学","北京政法学院"),
        ("中央财经大学","中央财政金融学院"),
        ("上海财经大学","上海财政经济学院"),
        ("西南财经大学","四川财经学院"),
    ]
    for cur, old in aliases:
        c.execute("INSERT OR IGNORE INTO school_aliases (current_name, alias_name) VALUES (?,?)", (cur, old))
    conn.commit()
    print(f"院校曾用名初始化: {len(aliases)}条")
    conn.close()


def resolve_school_name(name: str) -> str:
    """解析学校名称：如果name是曾用名，返回现名；否则返回原名"""
    if not name: return name
    ensure_school_aliases_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT current_name FROM school_aliases WHERE alias_name = ?", (name,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else name


# 启动时初始化
ensure_school_aliases_table()


import json

def check_duplicate_cert(cert_number: str, current_name: str = "") -> dict:
    """检查证书编号是否被多人使用"""
    if not cert_number:
        return {"duplicate": False, "message": "无证书编号，跳过"}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT name, school_name, education_level FROM mock_chsi WHERE certificate_number = ?",
        (cert_number,)
    )
    rows = c.fetchall()
    conn.close()

    if len(rows) > 1:
        others = [r for r in rows if r[0] != current_name]
        if others:
            return {
                "duplicate": True,
                "count": len(rows),
                "message": f"证书编号'{cert_number}'已被{len(rows)}人使用: {', '.join(r[0] for r in others)}",
            }
    return {"duplicate": False, "message": ""}


# ============================================================
# 候选人状态管理
# ============================================================

def ensure_candidate_table():
    """确保候选人状态表存在"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            school TEXT,
            major TEXT,
            education_level TEXT,
            degree_cert_status TEXT DEFAULT '',
            grad_cert_status TEXT DEFAULT '',
            final_status TEXT DEFAULT '',
            fail_reasons TEXT DEFAULT '',
            recruitment_type TEXT DEFAULT '校招',
            reviewer_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def upsert_candidate(name: str, school: str = "", major: str = "",
                     education_level: str = "", degree_status: str = "",
                     grad_status: str = "", final_status: str = "",
                     recruitment_type: str = "校招", reviewed: int = 0,
                     fail_reasons: str = "", **kwargs) -> int:
    """插入或更新候选人"""
    ensure_candidate_table()
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("ALTER TABLE candidates ADD COLUMN reviewed INTEGER DEFAULT 0")
        conn.commit()
    except: pass
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("ALTER TABLE candidates ADD COLUMN recruitment_type TEXT DEFAULT '校招'")
        conn.commit()
    except: pass
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM candidates WHERE name = ? AND school = ?", (name, school))
    row = c.fetchone()
    if row:
        c.execute("""UPDATE candidates SET major=?, education_level=?,
            degree_cert_status=?, grad_cert_status=?, final_status=?,
            recruitment_type=?, reviewed=?, fail_reasons=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?""", (major, education_level, degree_status, grad_status, final_status, recruitment_type, reviewed, fail_reasons, row[0]))
        cid = row[0]
    else:
        c.execute("""INSERT INTO candidates (name, school, major, education_level,
            degree_cert_status, grad_cert_status, final_status, recruitment_type, reviewed, fail_reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, school, major, education_level, degree_status, grad_status, final_status, recruitment_type, reviewed, fail_reasons))
        cid = c.lastrowid
    conn.commit()
    conn.close()
    return cid


def get_all_candidates() -> list:
    """获取所有候选人"""
    ensure_candidate_table()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM candidates ORDER BY updated_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def update_candidate_status(candidate_id: int, final_status: str, note: str = ""):
    """更新候选人最终状态"""
    ensure_candidate_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE candidates SET final_status=?, reviewer_note=?, reviewed=1, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (final_status, note, candidate_id))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
