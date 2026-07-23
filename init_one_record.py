"""清空学信库，只保留一条记录"""
import sqlite3

DB = "D:/edu-verify/edu_verify.db"
conn = sqlite3.connect(DB)
c = conn.cursor()

# 清空
c.execute("DELETE FROM mock_chsi")
c.execute("DELETE FROM verify_records")

# 只插入这一条
c.execute("""INSERT INTO mock_chsi
    (name, gender, birth_date, id_number, school_name, school_code,
     major, education_level, education_mode, degree,
     enrollment_date, graduation_date, certificate_number, certificate_type, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
    "张文宇", "女", "2003-11-24", "SIM202411240001",
    "中国人民大学", "10002", "劳动经济学", "本科", "全日制", "学士",
    "2021-09-01", "2025-06-25", "1000242024000969", "学位证书", "毕业"
))

conn.commit()
c.execute("SELECT COUNT(*) FROM mock_chsi")
print(f"Records: {c.fetchone()[0]}")
c.execute("SELECT name, school_name, certificate_number FROM mock_chsi")
for r in c.fetchall():
    print(f"  {r[0]} | {r[1]} | {r[2]}")
conn.close()
print("Done")
