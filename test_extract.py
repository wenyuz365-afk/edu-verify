"""测试 LLM 字段提取"""
import sys
sys.path.insert(0, "D:/edu-verify")

from field_extractor import get_field_extractor

# 模拟学位证书 OCR 文本
ocr_text = """
学士学位证书

唐穗艳，性别女，1999年5月11日生。在广东理工学院
修完物流管理专业教学计划规定的全部课程，成绩合格，
已通过课程考试和论文答辩。经审核，符合《中华人民
共和国学位条例》的规定，学科门类为管理学，授予
管理学学士学位。

广东理工学院学位评定委员会主席
二〇二一年六月二十五日

证书编号：8888100032022010012345
"""

extractor = get_field_extractor()
fields = extractor.extract(ocr_text, use_llm=True)
print(f"\n=== Results ===")
print(f"Name: {fields.name}")
print(f"Gender: {fields.gender}")
print(f"Birth: {fields.birth_date}")
print(f"School: {fields.school}")
print(f"Major: {fields.major}")
print(f"Degree: {fields.degree}")
print(f"Education Level: {fields.education_level}")
print(f"Graduation: {fields.graduation_date}")
print(f"Cert No: {fields.certificate_number}")
print(f"Cert Type: {fields.certificate_type}")
print(f"Method: {fields.extraction_method}")
