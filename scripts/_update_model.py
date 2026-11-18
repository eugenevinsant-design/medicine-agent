import requests
from pathlib import Path

BASE = "http://localhost:3000"
TOKEN = Path(".webui_key").read_text(encoding="utf-8").strip()
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

SYSTEM_PROMPT = (
    "Ты — профилированный ИИ-ассистент врача. Отвечай на русском. "
    "Используй инструменты: duckdb_query для запросов к базе пациентов и "
    "web_search_whitelist для поиска медицинской информации. "
    "Всегда указывай источник (source_id). Никогда не ставь окончательный диагноз. "
    "В КАЖДОМ ответе обязательно добавляй: «Требуется проверка врачом»."
)

payload = {
    "id": "doctor-assistant",
    "name": "doctor-assistant",
    "base_model_id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "meta": {
        "description": "Профилированный ИИ-ассистент врача",
        "system_prompt": SYSTEM_PROMPT,
        "tool_ids": ["duckdb_query", "web_search_whitelist"],
    },
    "params": {},
}

r = requests.post(f"{BASE}/api/v1/models/doctor-assistant/update", headers=headers, json=payload, timeout=30)
print("update status:", r.status_code)
print("body:", r.text[:400])
