import sqlite3
conn = sqlite3.connect("D:/edu-verify/edu_verify.db")
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM schools")
print(f"Schools: {c.fetchone()[0]}")

c.execute("SELECT COUNT(*) FROM mock_chsi")
print(f"Chsi records: {c.fetchone()[0]}")

c.execute("SELECT DISTINCT education_level FROM mock_chsi")
print(f"Levels: {[r[0] for r in c.fetchall()]}")

# 检查覆盖了多少学校
c.execute("SELECT COUNT(DISTINCT school_name) FROM mock_chsi")
print(f"Schools in chsi: {c.fetchone()[0]}")

# 列出所有学校
c.execute("SELECT school_name FROM schools ORDER BY school_name")
schools = [r[0] for r in c.fetchall()]
print(f"\nAll {len(schools)} schools:")
for s in schools:
    print(f"  {s}")

conn.close()
