import sqlite3
conn = sqlite3.connect("D:/edu-verify/edu_verify.db")
conn.execute("UPDATE mock_chsi SET graduation_date = '2024-06-25' WHERE certificate_number = '1000242024000969'")
conn.commit()
cur = conn.execute("SELECT name, graduation_date FROM mock_chsi")
print(cur.fetchone())
conn.close()
