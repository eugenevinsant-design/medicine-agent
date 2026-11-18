import os, json, requests
from pathlib import Path

BASE = "http://localhost:3000"
TOKEN = Path(".webui_key").read_text(encoding="utf-8").strip()
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# 1. Получим список моделей, чтобы найти нашу
r = requests.get(f"{BASE}/api/models", headers=headers, timeout=30)
print("models status:", r.status_code)
models = r.json().get("data", [])
doc_model = next((m["id"] for m in models if m.get("name") == "Врач-ассистент" or m.get("id") == "doctor-assistant"), None)
print("Найдена модель:", doc_model)

if not doc_model:
    print("Модель Врач-ассистент не найдена, используем базовую")
    doc_model = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

# 2. Отправка запроса
payload = {
    "model": doc_model,
    "messages": [{"role": "user", "content": "Пациент patient_001. Покажи средние значения QT по пациентам 60-69 лет. Используй инструмент duckdb_query."}],
    "stream": False,
}
print(f"\nОтправка запроса в {doc_model}...")
r2 = requests.post(f"{BASE}/api/chat/completions", headers=headers, json=payload, timeout=120)
print("chat status:", r2.status_code)
try:
    d = r2.json()
    if "choices" in d:
        content = d["choices"][0].get("message", {}).get("content", "")
        print("Ответ модели:\n", content)
    else:
        print("Ответ:", d)
except Exception as e:
    print("Ошибка парсинга:", e, r2.text[:500])
