"""Быстрая оценка на подвыборке сценариев (для проверки методики)."""
import json, os, time
from pathlib import Path
import requests

from eval.metrics import disclaimer_present, mrr, pii_leak, precision_at_k, recall_at_k

BASE = "http://localhost:3000"
TOKEN = Path(".webui_key").read_text(encoding="utf-8").strip()
MODEL = os.getenv("OPENWEBUI_MODEL", "doctor-assistant")
LIMIT = int(os.getenv("EVAL_LIMIT", "5"))
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

scenarios = [json.loads(l) for l in open("eval/scenarios.jsonl", encoding="utf-8") if l.strip()][:LIMIT]
results = []
for sc in scenarios:
    payload = {"model": MODEL, "messages": [{"role": "user", "content": sc["query"]}],
               "stream": False, "tool_ids": ["duckdb_query", "web_search_whitelist"]}
    start = time.time()
    r = requests.post(f"{BASE}/api/chat/completions", headers=headers, json=payload, timeout=180)
    lat = time.time() - start
    text = ""
    if r.status_code == 200:
        msg = r.json().get("choices", [{}])[0].get("message", {})
        text = msg.get("content") or ""
        # если контент пустой, но есть tool_calls/reasoning — берём их как текст
        if not text and msg.get("tool_calls"):
            text = json.dumps(msg["tool_calls"], ensure_ascii=False)
    import re
    sources = sorted(set(re.findall(r"src_[\w-]+", text)))
    results.append({
        "id": sc["id"],
        "recall@5": recall_at_k(sources, sc.get("expected_source_ids", []), 5),
        "precision@5": precision_at_k(sources, sc.get("expected_source_ids", []), 5),
        "mrr": mrr(sources, sc.get("expected_source_ids", [])),
        "disclaimer": disclaimer_present(text),
        "pii_leak": pii_leak(text),
        "latency": lat,
        "status": r.status_code,
    })
    print(f"{sc['id']}: status={r.status_code}, lat={lat:.1f}s, disclaimer={disclaimer_present(text)}")

n = len(results) or 1
summary = {
    "n": len(results),
    "recall@5": round(sum(r["recall@5"] for r in results)/n, 4),
    "precision@5": round(sum(r["precision@5"] for r in results)/n, 4),
    "mrr": round(sum(r["mrr"] for r in results)/n, 4),
    "disclaimer_rate": round(sum(r["disclaimer"] for r in results)/n, 4),
    "pii_leak_rate": round(sum(r["pii_leak"] for r in results)/n, 4),
    "latency_avg": round(sum(r["latency"] for r in results)/n, 2),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
with open("eval/results_subset.csv", "w", encoding="utf-8") as f:
    f.write("id,recall@5,precision@5,mrr,disclaimer,pii_leak,latency,status\n")
    for r in results:
        f.write(f"{r['id']},{r['recall@5']},{r['precision@5']},{r['mrr']},{r['disclaimer']},{r['pii_leak']},{r['latency']:.2f},{r['status']}\n")
print("Сохранено в eval/results_subset.csv")
