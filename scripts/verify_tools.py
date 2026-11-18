"""Проверка Tool'ов в Open WebUI через API.

Поскольку создать Tool через публичный REST API нельзя (только UI/Community),
скрипт делает две вещи:
  1) Находит ID Tool'ов в Workspace (если API отдаёт список);
  2) Отправляет тестовый запрос с tool_ids и проверяет, что модель их вызывает.

Использование:
  OPENWEBUI_API_KEY=sk-... OPENWEBUI_MODEL=openai/gpt-oss-20b:free \
    python scripts/verify_tools.py
"""
from __future__ import annotations

import json
import os
import sys

import requests

# Windows-консоль (cp1251) не умеет некоторые Unicode-символы — форсируем utf-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.getenv("OPENWEBUI_BASE_URL", "http://localhost:3000").rstrip("/")
KEY = os.getenv("OPENWEBUI_API_KEY", "")
MODEL = os.getenv("OPENWEBUI_MODEL", "")
TOOL_IDS = os.getenv("TOOL_IDS", "duckdb_query,web_search_whitelist").split(",")


def headers() -> dict:
    return {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def list_models() -> None:
    """Показать доступные модели (проверка подключения LLM)."""
    r = requests.get(f"{BASE}/api/models", headers=headers(), timeout=30)
    if r.status_code != 200:
        print(f"[WARN] /api/models -> {r.status_code}: {r.text[:200]}")
        return
    data = r.json().get("data", [])
    print(f"[OK] Доступно моделей: {len(data)}")
    for m in data[:10]:
        print(f"     - {m.get('id')}")


def verify_tool_call(prompt: str, tool_id: str) -> bool:
    """Отправить запрос с одним tool_id и проверить, что tool был вызван.

    Path A (chat + session_id) возвращает task_ids; читаем финальный чат.
    Для простоты используем Path B (legacy function_calling) — один запрос,
    ответ в теле, видно sources.
    """
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "params": {"function_calling": "legacy"},
        "tool_ids": [tool_id],
        "stream": False,
    }
    r = requests.post(f"{BASE}/api/chat/completions", headers=headers(), json=payload, timeout=180)
    if r.status_code != 200:
        print(f"[FAIL] {tool_id}: HTTP {r.status_code} — {r.text[:300]}")
        return False
    body = r.json()
    sources = body.get("sources", [])
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    print(f"[INFO] {tool_id}: sources={len(sources)}, content_len={len(content)}")
    if sources:
        print(f"       sources[0]: {json.dumps(sources[0], ensure_ascii=False)[:200]}")
    return len(sources) > 0


def main() -> None:
    if not KEY:
        print("Задай OPENWEBUI_API_KEY (токен из Open WebUI: Settings -> Account -> API Keys)")
        sys.exit(1)
    if not MODEL:
        print("Задай OPENWEBUI_MODEL")
        sys.exit(1)

    print(f"Open WebUI: {BASE}")
    print(f"Model: {MODEL}")
    list_models()

    print("\n--- Проверка Tool'ов (legacy mode, один запрос) ---")
    tests = {
        "duckdb_query": "Сколько строк в таблице patients? Используй инструмент.",
        "web_search_whitelist": "Найди в pubmed информацию об atrial fibrillation.",
    }
    ok = 0
    for tool_id in TOOL_IDS:
        tool_id = tool_id.strip()
        if not tool_id:
            continue
        prompt = tests.get(tool_id, f"Вызови инструмент {tool_id} и верни результат.")
        if verify_tool_call(prompt, tool_id):
            ok += 1

    print(f"\nИтог: {ok}/{len([t for t in TOOL_IDS if t.strip()])} Tool'ов вернули sources.")
    print("Если 0 — проверь, что Tool включён в Admin Panel -> Tools и добавлен к модели.")


if __name__ == "__main__":
    main()
