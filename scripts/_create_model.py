import requests, json
from pathlib import Path

BASE = "http://localhost:3000"
TOKEN = Path(".webui_key").read_text(encoding="utf-8").strip()
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Попробуем создать модель через API
payload = {
    "id": "doctor-assistant",
    "name": "doctor-assistant",
    "base_model_id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "meta": {
        "description": "Профилированный ИИ-ассистент врача"
    },
    "params": {},
}

r = requests.post(f"{BASE}/api/v1/models/create", headers=headers, json=payload, timeout=30)
print("create status:", r.status_code)
print(r.text[:500])

# Проверим список
r2 = requests.get(f"{BASE}/api/models", headers=headers, timeout=30)
for m in r2.json().get("data", []):
    if "doctor" in str(m.get("id", "")).lower() or "Врач" in str(m.get("name", "")):
        print("Найдена:", m.get("id"), "|", m.get("name"))
