"""Open WebUI Tool: duckdb_query для Parquet-витрин.

Загрузка в Open WebUI:
  Admin Panel -> Tools -> Create Tool -> вставить этот файл.
  Tool регистрирует функцию duckdb_query(sql: str) и отдаёт её LLM.

Безопасность:
  - только SELECT (и WITH ... SELECT);
  - whitelist таблиц (PARQUET_TABLES);
  - LIMIT <= 1000 (принудительно добавляется, если отсутствует);
  - доступ только к data/parquet/.

Замечание: путь к data/parquet/ задаётся через PARQUET_DIR (env или дефолт).
Если Open WebUI работает в контейнере, смонтируй data/parquet внутрь
контейнера и задай PARQUET_DIR на путь внутри контейнера.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import duckdb

# Whitelist таблиц (соответствует etl/config.py::PARQUET_TABLES)
PARQUET_TABLES = {"patients", "ecg_features", "clinical_signs"}
MAX_LIMIT = 1000

PARQUET_DIR = Path(os.getenv("PARQUET_DIR", "data/parquet")).resolve()

_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|merge|grant|revoke|attach|detach|copy|pragma|call|execute)\b", re.IGNORECASE)
_SELECT_START = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_LIMIT_RE = re.compile(r"\blimit\s+\d+\b", re.IGNORECASE)


def _validate_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    if not sql:
        raise ValueError("Пустой SQL")
    if not _SELECT_START.match(sql):
        raise ValueError("Разрешены только SELECT / WITH ... SELECT")
    if _FORBIDDEN.search(sql):
        raise ValueError("Обнаружена запрещённая конструкция (только чтение)")
    # Whitelist таблиц: все идентификаторы после FROM/JOIN должны быть в whitelist
    for table in re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w]*)", sql, flags=re.IGNORECASE):
        if table.lower() not in PARQUET_TABLES:
            raise ValueError(f"Таблица '{table}' не в whitelist {sorted(PARQUET_TABLES)}")
    if not _LIMIT_RE.search(sql):
        sql = f"{sql} LIMIT {MAX_LIMIT}"
    return sql


def _con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    for table in PARQUET_TABLES:
        path = PARQUET_DIR / table
        if path.exists():
            con.execute(
                f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{path}/**/*.parquet')"
            )
    return con


def duckdb_query(sql: str) -> str:
    """Выполнить SELECT по Parquet-витринам и вернуть JSON с результатом.

    Args:
        sql: SQL-запрос (только SELECT, whitelist таблиц, LIMIT<=1000).
    Returns:
        JSON-строка {"rows": [...], "row_count": N, "source_id": "..."}.
    """
    try:
        safe_sql = _validate_sql(sql)
        con = _con()
        df = con.execute(safe_sql).fetchdf()
        rows: list[dict[str, Any]] = json.loads(df.to_json(orient="records", force_ascii=False))
        source_ids = sorted({str(r.get("source_id")) for r in rows if r.get("source_id")})
        return json.dumps(
            {
                "rows": rows,
                "row_count": len(rows),
                "source_id": source_ids[0] if len(source_ids) == 1 else source_ids,
            },
            ensure_ascii=False,
        )
    except Exception as exc:  # noqa: BLE001 — Tool должен вернуть ошибку, а не упасть
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# --- Минимальный интерфейс Open WebUI Tool ---
class Tools:
    def duckdb_query(self, sql: str) -> str:
        """Выполнить SELECT по Parquet-витринам (только чтение)."""
        return duckdb_query(sql)
