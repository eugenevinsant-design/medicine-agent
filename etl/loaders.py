"""Универсальный загрузчик исходных данных для ETL.

Поддерживает форматы: CSV, Parquet, JSON, JSONL, Excel (XLSX).
Формат определяется по расширению (или явно через format=...).

Маппинг полей: если у руководителя другие имена колонок (например,
'ФИО' вместо 'full_name'), задаётся через FIELD_MAP в etl/config.py
или аргументом field_map.

Пример подключения реального источника:
    # в etl/config.py
    SOURCE_INPUT = ROOT / "data" / "incoming" / "patients.csv"
    FIELD_MAP = {"ФИО": "full_name", "Дата рождения": "birth_date"}

    # в etl/run_etl.py
    records = load_records(SOURCE_INPUT, field_map=FIELD_MAP)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger("etl.loaders")


def _read_csv(path: Path) -> pd.DataFrame:
    # sep=None + engine='python' — автоопределение разделителя (,, ;, \t)
    return pd.read_csv(path, sep=None, engine="python")


def _read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def _read_json(path: Path) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # {"records": [...]} или {"data": [...]}
        for key in ("records", "data", "items", "patients"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
    return pd.DataFrame(data)


def _read_jsonl(path: Path) -> pd.DataFrame:
    return pd.read_json(path, lines=True)


def _read_excel(path: Path) -> pd.DataFrame:
    return pd.read_excel(path)


_READERS = {
    ".csv": _read_csv,
    ".parquet": _read_parquet,
    ".pq": _read_parquet,
    ".json": _read_json,
    ".jsonl": _read_jsonl,
    ".ndjson": _read_jsonl,
    ".xlsx": _read_excel,
    ".xls": _read_excel,
}


def apply_field_map(df: pd.DataFrame, field_map: dict[str, str] | None) -> pd.DataFrame:
    """Переименовать колонки по маппингу. Остальные колонки — без изменений."""
    if not field_map:
        return df
    existing = {src: dst for src, dst in field_map.items() if src in df.columns}
    missing = [src for src in field_map if src not in df.columns]
    if missing:
        log.warning("Поля из FIELD_MAP не найдены в источнике: %s", missing)
    return df.rename(columns=existing)


def _normalize_nested(df: pd.DataFrame) -> pd.DataFrame:
    """Вложенные dict/list -> строка, чтобы Parquet был плоским.

    Для полей ecg_features / clinical_signs оставляем структуру как есть —
    её обрабатывает build_parquet. Здесь нормализуем только прочие колонки.
    """
    keep = {"ecg_features", "clinical_signs"}
    for col in df.columns:
        if col in keep:
            continue
        if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
            df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x)
    return df


def load_records(
    path: str | Path,
    *,
    field_map: dict[str, str] | None = None,
    format: str | None = None,
) -> list[dict[str, Any]]:
    """Загрузить исходные записи из файла любого поддерживаемого формата.

    Args:
        path: путь к файлу (абсолютный или относительный).
        field_map: {"Имя в источнике": "имя в ETL"}, например {"ФИО": "full_name"}.
        format: явный формат (".csv", "parquet", ...) — если расширение нестандартное.
    Returns:
        Список словарей (по одной записи на пациента/кейс).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Источник не найден: {p}")

    ext = format.lower() if format else p.suffix.lower()
    if not ext.startswith("."):
        ext = "." + ext
    reader = _READERS.get(ext)
    if reader is None:
        raise ValueError(f"Неподдерживаемый формат '{ext}'. Доступны: {sorted(_READERS)}")

    log.info("Чтение %s (формат %s)", p, ext)
    df = reader(p)
    df = apply_field_map(df, field_map)
    df = _normalize_nested(df)

    # NaN -> None, чтобы JSON/Parquet не содержали 'nan'
    records = df.where(pd.notna(df), None).to_dict(orient="records")
    log.info("Загружено записей: %d, колонок: %s", len(records), list(df.columns))
    return records
