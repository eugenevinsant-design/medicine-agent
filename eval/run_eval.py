"""Автоматическая оценка ответов агента по scenarios.jsonl.

Два режима (переключаются EVAL_MODE):
  - stub   : заглушка, детерминированные ответы (без LLM/Open WebUI);
  - openwebui : реальный вызов Open WebUI API (нужен токен и LLM-ключ).

Переменные окружения:
  EVAL_MODE=stub|openwebui
  OPENWEBUI_BASE_URL=http://localhost:3000
  OPENWEBUI_API_PATH=/api/chat/completions
  OPENWEBUI_API_KEY=<токен из Open WebUI> (или JWT из .webui_key)
  OPENWEBUI_MODEL=<имя модели>
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from eval.metrics import (
    disclaimer_present,
    mrr,
    pii_leak,
    precision_at_k,
    recall_at_k,
    top1_hit,
    top3_hit,
)

SCENARIOS = Path(__file__).resolve().parent / "scenarios.jsonl"

# --- Open WebUI API ---
BASE_URL = os.getenv("OPENWEBUI_BASE_URL", "http://localhost:3000").rstrip("/")
API_PATH = os.getenv("OPENWEBUI_API_PATH", "/api/chat/completions")
API_KEY = os.getenv("OPENWEBUI_API_KEY", "")
MODEL = os.getenv("OPENWEBUI_MODEL", "Врач-ассистент")
EVAL_MODE = os.getenv("EVAL_MODE", "stub").lower()

DISCLAIMER = "Требуется проверка врачом"


@dataclass
class AgentAnswer:
    text: str
    sources: list[str] = field(default_factory=list)
    predicted_topics: list[str] = field(default_factory=list)
    latency: float = 0.0


# --- Режим 1: заглушка -------------------------------------------------------
def call_agent_stub(query: str) -> AgentAnswer:
    """Детерминированная заглушка: берёт source_id из запроса, добавляет дисклеймер."""
    m = re.search(r"patient_\w+", query)
    patient = m.group(0) if m else "patient_000"
    topics: list[str] = []
    low = query.lower()
    if "фибрилляц" in low or "перебои" in low:
        topics = ["фибрилляция предсердий", "антикоагуляция"]
    elif "боль в груди" in low or "стенокард" in low:
        topics = ["стенокардия", "ИБС"]
    elif "сердцебиение" in low or "тревог" in low:
        topics = ["тахикардия", "тревожное расстройство"]
    return AgentAnswer(
        text=f"Гипотезы: {', '.join(topics) or 'н/д'}. {DISCLAIMER}.",
        sources=[],
        predicted_topics=topics,
        latency=0.0,
    )


# --- Режим 2: реальный Open WebUI API ----------------------------------------
def _extract_sources(text: str) -> list[str]:
    """Вытащить source_id вида src_xxx из текста ответа."""
    return sorted(set(re.findall(r"src_[\w-]+", text)))


def call_agent_openwebui(query: str) -> AgentAnswer:
    if not API_KEY:
        raise RuntimeError("Задай OPENWEBUI_API_KEY в окружении")
    url = f"{BASE_URL}{API_PATH}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": query}],
        "stream": False,
        "tool_ids": ["duckdb_query", "web_search_whitelist"],
    }
    start = time.time()
    resp = requests.post(url, headers=headers, json=payload, timeout=180)
    latency = time.time() - start
    resp.raise_for_status()
    data = resp.json()
    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    # Если в ответе есть блок с результатом инструмента, тоже его парсим
    return AgentAnswer(text=text, sources=_extract_sources(text), predicted_topics=[], latency=latency)


def call_agent(query: str) -> AgentAnswer:
    if EVAL_MODE == "openwebui":
        return call_agent_openwebui(query)
    return call_agent_stub(query)


# --- Оценка ------------------------------------------------------------------
def load_scenarios(path: Path = SCENARIOS) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def evaluate_one(scenario: dict, answer: AgentAnswer) -> dict:
    relevant = scenario.get("expected_source_ids", [])
    expected_topics = scenario.get("expected_topics", [])
    return {
        "id": scenario["id"],
        "recall@5": recall_at_k(answer.sources, relevant, k=5),
        "precision@5": precision_at_k(answer.sources, relevant, k=5),
        "mrr": mrr(answer.sources, relevant),
        "top1": top1_hit(answer.predicted_topics[0] if answer.predicted_topics else None, expected_topics),
        "top3": top3_hit(answer.predicted_topics, expected_topics),
        "disclaimer": disclaimer_present(answer.text),
        "pii_leak": pii_leak(answer.text),
        "latency": answer.latency,
    }


def main() -> None:
    scenarios = load_scenarios()
    results = []
    for sc in scenarios:
        try:
            answer = call_agent(sc["query"])
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] {sc['id']}: {exc}")
            continue
        results.append(evaluate_one(sc, answer))

    n = len(results) or 1
    latencies = sorted(r["latency"] for r in results if r["latency"] > 0)
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0

    summary = {
        "mode": EVAL_MODE,
        "n": len(results),
        "recall@5": round(sum(r["recall@5"] for r in results) / n, 4),
        "precision@5": round(sum(r["precision@5"] for r in results) / n, 4),
        "mrr": round(sum(r["mrr"] for r in results) / n, 4),
        "top1": round(sum(r["top1"] for r in results) / n, 4),
        "top3": round(sum(r["top3"] for r in results) / n, 4),
        "disclaimer_rate": round(sum(r["disclaimer"] for r in results) / n, 4),
        "pii_leak_rate": round(sum(r["pii_leak"] for r in results) / n, 4),
        "latency_p50": round(p50, 2),
        "latency_p95": round(p95, 2),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    # Сохраним детальные результаты в CSV для таблиц Главы 4
    with open("eval/results.csv", "w", encoding="utf-8") as f:
        f.write("id,recall@5,precision@5,mrr,top1,top3,disclaimer,pii_leak,latency\n")
        for r in results:
            f.write(f"{r['id']},{r['recall@5']},{r['precision@5']},{r['mrr']},{r['top1']},{r['top3']},{r['disclaimer']},{r['pii_leak']},{r['latency']:.2f}\n")
    print("\nДетальные результаты сохранены в eval/results.csv")


if __name__ == "__main__":
    main()
