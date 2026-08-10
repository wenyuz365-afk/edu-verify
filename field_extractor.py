"""
学历证书关键字段提取模块 — AI 驱动
直接使用 LLM 从 OCR 文本中智能提取所有字段，不再依赖正则规则。
"""
import json
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class EducationFields:
    name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    id_number: Optional[str] = None
    school: Optional[str] = None
    college: Optional[str] = None
    major: Optional[str] = None
    degree: Optional[str] = None
    education_level: Optional[str] = None
    education_mode: Optional[str] = None
    graduation_date: Optional[str] = None
    enrollment_date: Optional[str] = None
    certificate_number: Optional[str] = None
    certificate_type: Optional[str] = None
    issue_date: Optional[str] = None
    raw_text: Optional[str] = None
    extraction_method: Optional[str] = None


def _get_api_config():
    """读取API配置: 优先Streamlit Secrets，回退环境变量"""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'ANTHROPIC_AUTH_TOKEN' in st.secrets:
            return {
                'token': st.secrets['ANTHROPIC_AUTH_TOKEN'],
                'base_url': st.secrets.get('ANTHROPIC_BASE_URL', 'https://api.deepseek.com/anthropic'),
                'model': st.secrets.get('ANTHROPIC_MODEL', 'deepseek-v4-pro'),
            }
    except: pass
    import os
    return {
        'token': os.environ.get('ANTHROPIC_AUTH_TOKEN', ''),
        'base_url': os.environ.get('ANTHROPIC_BASE_URL', 'https://api.deepseek.com/anthropic'),
        'model': os.environ.get('ANTHROPIC_MODEL', 'deepseek-v4-pro'),
    }


class FieldExtractor:
    """AI 驱动的证书字段提取器"""

    def extract(self, ocr_text: str, use_llm: bool = True) -> EducationFields:
        """唯一入口：LLM 提取（始终使用 AI）"""
        return self._extract_via_llm(ocr_text)

    def _extract_via_llm(self, ocr_text: str) -> EducationFields:
        """调用 LLM API 从 OCR 文本中智能提取字段"""
        try:
            import httpx
            cfg = _get_api_config()
            api_token = cfg['token']
            base_url = cfg['base_url']

            if not api_token:
                raise ValueError("API token not configured")

            system_prompt = """你是一个学历证书信息提取专家。无论证书来自哪所学校、何种格式，你都能准确理解其中的内容。

## 提取规则

1. **姓名**：证书上学生的姓名。通常是"学生XXX"、"XXX，性别"、证书开头的人名、或紧挨"兹证明/兹授予"后面的人名
2. **性别**：男或女。通常与姓名相邻
3. **出生日期**：学生的出生日期。通常格式为"XXXX年X月X日生"、"出生于XXXX年X月"、或紧接姓名/性别后的日期。没有出生日期则返回 null
4. **身份证号**：仅毕业证书有。18位数字。学位证书通常没有，此时返回 null
5. **学校**：颁发证书的学校全称。如"XX大学"、"XX学院"
6. **学院**：学生所属二级学院，如"管理学院"、"计算机学院"。没有则 null
7. **专业**：学生所修专业名称，如"计算机科学与技术"、"工商管理"。注意区分"学科门类"（如管理学）和专业
8. **学位**：学士/硕士/博士
9. **学历层次**：本科/硕士研究生/博士研究生/专科
10. **学习形式**：全日制/非全日制/成人教育/网络教育。学位证书通常不标注，返回 null
11. **毕业日期**：学生完成学业的日期。通常格式为"XXXX年X月"、"于XXXX年X月毕业"
12. **证书编号**：证书的唯一编号。通常是一串数字或数字+字母
13. **证书类型**：毕业证书/学位证书/结业证书。根据证书内容判断
14. **签发日期**：证书的签发日期（非出生日期、非毕业日期），通常在最底部。没有则 null

## 重要：日期区分
证书上可能出现多个日期，请仔细区分：
- **出生日期**：描述"出生"的日期，通常是证书上最早的日期
- **毕业日期**：描述"毕业"/"修完"/"完成学业"的日期
- **签发日期**：证书底部签名日期，通常最晚

## 重要：年份识别
证书上的年份常以中文大写数字书写，请准确识别：
- "二〇二五"=2025，"二〇二四"=2024，"二〇二三"=2023，"二〇二二"=2022，"二〇二一"=2021，"二〇二〇"=2020
- 注意区分"二〇二五"和"二〇二四"，它们容易混淆
- 所有日期统一输出为 YYYY-MM-DD 格式

## 输出格式
只输出一个纯净的 JSON 对象，不要 ```json``` 包裹，不要任何解释文字。无法确定的字段填 null。"""

            resp = httpx.post(
                f"{base_url}/v1/messages",
                json={
                    "model": _get_api_config()['model'],
                    "max_tokens": 4096,
                    "temperature": 0,
                    "thinking": {"type": "disabled"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"请从以下证书OCR文本中提取所有字段：\n\n{ocr_text}"},
                    ],
                },
                headers={
                    "x-api-key": api_token,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=60
            )

            if resp.status_code != 200:
                raise ValueError(f"API error {resp.status_code}: {resp.text[:300]}")

            data = resp.json()

            # DeepSeek V4 Pro 是推理模型，content 包含多个块
            # content[0] = thinking（推理过程）, content[1...] = text（实际回答）
            # 注意：有时模型只返回一个 text 块，需兼容所有情况
            text_content = ""
            thinking_text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text_content += block.get("text", "")
                elif block.get("type") == "thinking":
                    thinking_text = block.get("thinking", "")

            # 如果没有 text 块，可能是模型配置不同，尝试从 thinking 中提取
            if not text_content:
                # 有些情况下模型把答案也放在 thinking 末尾
                # 或者整个响应只有一个块，type 为 text
                if data.get("content"):
                    first = data["content"][0]
                    text_content = first.get("text", "")
                if not text_content and thinking_text:
                    # Last resort: 从 thinking 尾部提取可能是答案的 JSON
                    text_content = thinking_text

            if not text_content:
                raise ValueError(f"No text in response. Content blocks: {json.dumps([{'type': b.get('type'), 'len': len(str(b))} for b in data.get('content', [])], ensure_ascii=False)}")

            # 解析 JSON 响应
            print(f"[LLM Extract] Raw response text: {text_content[:300]}", flush=True)
            raw_dict = self._parse_json(text_content)
            fields_dict = self._normalize_keys(raw_dict)

            # 学位证书的毕业日期 = 签发日期（两者等同）
            if not fields_dict.get("graduation_date") and fields_dict.get("issue_date"):
                fields_dict["graduation_date"] = fields_dict["issue_date"]

            # 确保关键字段类型正确
            for key in list(fields_dict.keys()):
                if isinstance(fields_dict[key], float) and fields_dict[key] == int(fields_dict[key]):
                    pass  # keep as-is

            fields_dict["raw_text"] = ocr_text
            fields_dict["extraction_method"] = f"llm-{_get_api_config()['model']}"

            # 只保留 EducationFields 中定义的字段
            valid_keys = {k for k in EducationFields.__dataclass_fields__}
            clean = {k: fields_dict.get(k) for k in valid_keys if k in fields_dict}

            print(f"[LLM Extract] {json.dumps(clean, ensure_ascii=False, default=str)}")
            return EducationFields(**clean)

        except Exception as e:
            print(f"[LLM Extract] Failed: {e}")
            # 绝对不回退到规则 — 返回错误状态让用户看到
            return EducationFields(
                raw_text=ocr_text,
                extraction_method=f"error: {str(e)[:100]}"
            )

    # 中英文字段名映射（AI 可能返回中文或英文键名）
    KEY_MAP = {
        "姓名": "name", "name": "name",
        "性别": "gender", "gender": "gender",
        "出生日期": "birth_date", "birth_date": "birth_date",
        "身份证号": "id_number", "id_number": "id_number",
        "学校": "school", "school": "school",
        "学院": "college", "college": "college",
        "专业": "major", "major": "major",
        "学位": "degree", "degree": "degree",
        "学历层次": "education_level", "education_level": "education_level",
        "学习形式": "education_mode", "education_mode": "education_mode",
        "毕业日期": "graduation_date", "graduation_date": "graduation_date",
        "入学日期": "enrollment_date", "enrollment_date": "enrollment_date",
        "证书编号": "certificate_number", "certificate_number": "certificate_number",
        "证书类型": "certificate_type", "certificate_type": "certificate_type",
        "签发日期": "issue_date", "issue_date": "issue_date",
        "原始文本": "raw_text", "raw_text": "raw_text",
    }

    def _normalize_keys(self, raw: dict) -> dict:
        """将 AI 返回的中文键名映射为英文字段名"""
        result = {}
        for k, v in raw.items():
            english_key = self.KEY_MAP.get(k, k)  # 找不到映射就保留原键
            result[english_key] = v
        return result

    def _parse_json(self, text: str) -> dict:
        """从 LLM 响应中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 包裹的 JSON
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取第一个 {...} 对象
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass

        # 最后的兜底
        raise ValueError(f"Cannot parse JSON from LLM response: {text[:200]}")


# 单例
    def extract_resume_education(self, ocr_text: str) -> list:
        """
        从简历OCR文本中提取所有教育经历（支持多段）。
        返回格式: [{"school": "", "major": "", "education_level": "", "start_year": "", "end_year": ""}, ...]
        """
        try:
            import httpx
            cfg = _get_api_config()
            api_token = cfg['token']
            base_url = cfg['base_url']
            if not api_token:
                raise ValueError("API not configured")

            current_year = str(__import__('datetime').datetime.now().year)
            system_prompt = f"""你是简历信息提取专家。从简历文本中提取所有教育经历（本科、硕士、博士等）。当前年份是{current_year}年。

## 提取规则
1. 提取每一段高等教育经历，返回数组。多段同层次学历（如两个本科/两个硕士）都要分别提取
2. 每段包含: school(学校全称), major(专业名称), education_level(本科/硕士研究生/博士研究生/专科), start_year(入学年份YYYY), end_year(毕业年份YYYY或null), status(见下方)

## status判定（按优先级）：
   - 简历出现"退学"/"肄业"/"辍学"/"dropout" → status="dropout"
   - 简历出现"交换"/"访学"/"暑期"/"交流"/"exchange"/"visiting" → status="exchange"
   - 简历出现"双学位"/"辅修"/"minor"/"double degree" → status="minor"
   - 简历出现"连读"/"八年制"/"本硕博"/"本博"/"硕博连读"/"combined" → status="merged", education_level取最高学位
   - 简历出现"至今"/"在读"/"present"/"预计"/"预期"/end_year为null/end_year>={current_year} → status="ongoing"
   - 以上都不满足 → status="graduated"

3. 学校名称使用全称（如简历写"北大"→"北京大学"）
4. 专业名称保持简历原文，不做修改
5. 按学历从低到高排序（本科→硕士→博士）
6. 连读项目(merged)只输出一段，education_level取最高层级

## 输出格式
只输出JSON数组，不要其他文字。例:
[{{"school":"清华大学","major":"法学","education_level":"本科","start_year":"2018","end_year":"2022","status":"graduated"}},{{"school":"北京大学","major":"民法学","education_level":"硕士研究生","start_year":"2025","end_year":null,"status":"ongoing"}}]"""

            resp = httpx.post(f"{base_url}/v1/messages", json={
                "model": cfg['model'],
                "max_tokens": 1024, "temperature": 0,
                "thinking": {"type": "disabled"},
                "messages": [
                    {"role":"system","content":system_prompt},
                    {"role":"user","content":f"请从以下简历中提取所有教育经历:\n\n{ocr_text}"},
                ],
            }, headers={
                "x-api-key":api_token, "anthropic-version":"2023-06-01", "content-type":"application/json"
            }, timeout=60)

            if resp.status_code != 200:
                raise ValueError(f"API error {resp.status_code}")

            data = resp.json()
            text_content = ""
            for block in data.get("content",[]):
                if block.get("type")=="text":
                    text_content = block.get("text",""); break
            if not text_content and data.get("content"):
                text_content = data["content"][0].get("text","")

            parsed = json.loads(text_content)
            if not isinstance(parsed, list):
                # 可能是 {"education": [...]} 格式
                parsed = parsed.get("education", parsed.get("教育经历", [parsed]))
            return parsed

        except Exception as e:
            print(f"[Resume Extract] Failed: {e}")
            return []


_field_extractor = None


def get_field_extractor() -> FieldExtractor:
    global _field_extractor
    if _field_extractor is None:
        _field_extractor = FieldExtractor()
    return _field_extractor
