"""Open WebUI Tool: web_search_whitelist.

Оборачивает SearxNG и возвращает только результаты с доменов из whitelist
(ТЗ, п.6.4): cr.minzdrav.gov.ru, pubmed.ncbi.nlm.nih.gov, escardio.org,
acc.org, cardiosite.ru.

Дополнительно: перед запросом в SearxNG проверяется, что в запросе нет PII
(ФЗ-152). ID пациента (patient_XXX) — допустимы; ФИО/телефоны/email — блокируются.

Загрузка в Open WebUI:
  Admin Panel -> Tools -> Create Tool -> вставить этот файл.
"""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlparse

import requests

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")

# Whitelist профильных доменов (ТЗ п.6.4)
DOMAIN_WHITELIST = {
    "cr.minzdrav.gov.ru",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",       # результаты pubmed-движка приходят с www.ncbi.nlm.nih.gov
    "escardio.org",
    "acc.org",
    "cardiosite.ru",
}
MAX_RESULTS = 10

_PII_PATTERNS = [
    re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b"),  # ФИО ru
    re.compile(r"(?:\+7|8)[\s\-(]?\d{3}[\s\-)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"),  # phone
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),  # email
]


def _contains_pii(text: str) -> bool:
    return any(p.search(text) for p in _PII_PATTERNS)


def _domain_allowed(url: str) -> bool:
    host = urlparse(url).hostname or ""
    host = host.lower()
    return any(host == d or host.endswith("." + d) for d in DOMAIN_WHITELIST)


def web_search_whitelist(query: str) -> str:
    """Поиск в SearxNG с фильтром по whitelist доменов.

    Args:
        query: поисковый запрос без персональных данных (ID допустимы).
    Returns:
        JSON {"results": [{"title", "url", "content"}], "count": N} или {"error"}.
    """
    if _contains_pii(query):
        return json.dumps({"error": "Запрос содержит потенциальные ПДн (ФИО/телефон/email). Удалите их."}, ensure_ascii=False)

    try:
        resp = requests.get(
            f"{SEARXNG_URL}/search",
            params={"q": query, "format": "json"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": f"SearxNG недоступен: {exc}"}, ensure_ascii=False)

    filtered = []
    for item in data.get("results", []):
        url = item.get("url", "")
        if not _domain_allowed(url):
            continue
        filtered.append({
            "title": item.get("title", ""),
            "url": url,
            "content": item.get("content", ""),
        })
        if len(filtered) >= MAX_RESULTS:
            break

    return json.dumps({"results": filtered, "count": len(filtered)}, ensure_ascii=False)


class Tools:
    def web_search_whitelist(self, query: str) -> str:
        """Поиск только по профильным whitelist-доменам (без ПДн в запросе)."""
        return web_search_whitelist(query)
