import json, requests
from pathlib import Path

BASE = "http://localhost:3000"
TOKEN = Path(".webui_key").read_text(encoding="utf-8").strip()
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

r = requests.get(f"{BASE}/api/models", headers=headers, timeout=30)
data = r.json()
print("All models:")
for m in data.get("data", []):
    print(" -", m.get("id"), "| name:", m.get("name"), "| owned_by:", m.get("owned_by"))

# попробуем отправить в базовую модель (напрямую)
payload = {"model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", "messages": [{"role":"user","content":"Скажи 'тест'"}], "stream": False}
r2 = requests.post(f"{BASE}/api/chat/completions", headers=headers, json=payload, timeout=60)
print("\nbase model status:", r2.status_code)
print("response:", r2.text[:500])
