import os, json, requests
from dotenv import load_dotenv
load_dotenv()

base = os.getenv("LLM_API_BASE_URL")
key = os.getenv("LLM_API_KEY")
model = os.getenv("LLM_MODEL")
print("base:", base)
print("model:", model)
print("key set:", bool(key) and not key.startswith("replace"))

headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

# 1. Простой ответ
payload = {"model": model, "messages": [{"role": "user", "content": "Reply with exactly: OK"}], "max_tokens": 20}
r = requests.post(f"{base}/chat/completions", headers=headers, json=payload, timeout=60)
print("simple:", r.status_code, r.text[:300])

# 2. Tool calling
tools = [{
    "type": "function",
    "function": {
        "name": "duckdb_query",
        "description": "Execute SELECT on Parquet tables",
        "parameters": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]},
    },
}]
payload2 = {
    "model": model,
    "messages": [{"role": "user", "content": "Сколько строк в таблице patients? Используй инструмент duckdb_query."}],
    "tools": tools,
    "tool_choice": "auto",
    "max_tokens": 200,
}
r2 = requests.post(f"{base}/chat/completions", headers=headers, json=payload2, timeout=60)
print("tools:", r2.status_code)
try:
    d = r2.json()
    msg = d.get("choices", [{}])[0].get("message", {})
    print("tool_calls:", json.dumps(msg.get("tool_calls"), ensure_ascii=False))
    print("content:", (msg.get("content") or "")[:200])
except Exception as e:
    print("parse error:", e, r2.text[:300])
