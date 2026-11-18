"""PII-guard: проверка промпта перед отправкой во внешнюю LLM.

Правила:
- Regex-детекторы типичных PII (ФИО-паттерны, телефоны, email, СНИЛС, полис).
- Whitelist полей: в промпт допускаются только LLM_ALLOWED_FIELDS.
- Если найден PII — выбрасывается PiiLeakError, отправка блокируется.
"""
from __future__ import annotations

import re
from typing import Any

from etl.config import LLM_ALLOWED_FIELDS


class PiiLeakError(RuntimeError):
    """Обнаружен потенциальный PII в данных, предназначенных для LLM."""


# Типичные паттерны PII (консервативные, чтобы не ловить ложные срабатывания на ID)
_PATTERNS: dict[str, re.Pattern] = {
    "phone_ru": re.compile(r"(?:\+7|8)[\s\-(]?\d{3}[\s\-)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "snils": re.compile(r"\b\d{3}-\d{3}-\d{3}[\s-]?\d{2}\b"),
    "oms_policy": re.compile(r"\b\d{16}\b"),
    "fio_ru": re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b"),
}


def find_pii(text: str) -> dict[str, list[str]]:
    """Вернуть найденные PII-совпадения по типам (пусто, если чисто)."""
    hits: dict[str, list[str]] = {}
    for name, pattern in _PATTERNS.items():
        matches = [m.group(0) for m in pattern.finditer(text)]
        if matches:
            hits[name] = matches
    return hits


def assert_clean(text: str) -> None:
    """Бросить PiiLeakError, если в тексте есть PII."""
    hits = find_pii(text)
    if hits:
        raise PiiLeakError(f"Обнаружен PII перед отправкой в LLM: {hits}")


def filter_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Оставить только whitelist-поля, остальные отбросить (не отправлять в LLM)."""
    return {k: v for k, v in record.items() if k in LLM_ALLOWED_FIELDS}


def sanitize_for_llm(record: dict[str, Any]) -> dict[str, Any]:
    """Whitelist + проверка на PII. Возвращает безопасный словарь."""
    safe = filter_fields(record)
    blob = " ".join(str(v) for v in safe.values())
    assert_clean(blob)
    return safe
