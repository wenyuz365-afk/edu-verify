"""测试 LLM — 验证 max_tokens 和 thinking 修复"""
import sys
sys.path.insert(0, "D:/edu-verify")
from field_extractor import get_field_extractor

ocr_text = """
学士学位证书
张文宇，性别女，2003年11月24日生。在中国人民大学
修完劳动经济学专业教学计划规定的全部课程，成绩合格，
已通过课程考试和论文答辩。经审核，授予
经济学学士学位。

中国人民大学学位评定委员会主席
二〇二五年六月二十五日

证书编号：100022025010012345
"""

extractor = get_field_extractor()
fields = extractor.extract(ocr_text, use_llm=True)
print(f"Name: {fields.name}")
print(f"School: {fields.school}")
print(f"Major: {fields.major}")
print(f"Degree: {fields.degree}")
print(f"Birth: {fields.birth_date}")
print(f"Cert No: {fields.certificate_number}")
print(f"Method: {fields.extraction_method}")
