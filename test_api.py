"""测试 DeepSeek API 调用"""
import os, json, httpx

api_token = "sk-fa998f9a47194397b0dfea8aa9b8413c"
base_url = "https://api.deepseek.com/anthropic"

resp = httpx.post(
    f"{base_url}/v1/messages",
    json={
        "model": "deepseek-v4-pro",
        "max_tokens": 300,
        "temperature": 0,
        "messages": [
            {"role": "user", "content": "从以下文本提取姓名和学校，只返回JSON：张三，男，1999年5月生，在清华大学修完计算机科学与技术专业，于2021年6月获得工学学士学位。"}
        ],
    },
    headers={
        "x-api-key": api_token,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    },
    timeout=30
)

print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Model: {data.get('model', 'unknown')}")
    content = data.get('content', [])
    for i, block in enumerate(content):
        print(f"Content[{i}]: type={block.get('type')}, keys={list(block.keys())}")
        if block.get('type') == 'text':
            print(f"  TEXT: {block.get('text', '')[:500]}")
        elif block.get('type') == 'thinking':
            print(f"  THINKING: {block.get('thinking', '')[:200]}...")
else:
    print(f"Error: {resp.text[:500]}")
