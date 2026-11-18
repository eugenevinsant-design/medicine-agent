"""Запись обезличенных данных в Parquet-витрины (партиции по source_id)."""
from __future__ import annotations

import shutil
from typing import Any

import pandas as pd

from etl.config import PARQUET_DIR


def _reset_table(path) -> None:
    """Удалить старую витрину, чтобы ETL был идемпотентным (без дубликатов)."""
    if path.exists():
        shutil.rmtree(path)


def write_parquet(records: list[dict[str, Any]]) -> dict[str, str]:
    """Разложить записи по таблицам и партициям source_id.

    Идемпотентность: старые витрины удаляются перед записью,
    иначе повторный запуск ETL создаёт дубликаты (новые UUID-файлы).
    Возвращает mapping table -> путь витрины.
    """
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)

    # Нормализация: вложенные dict в JSON-строку, чтобы Parquet был плоским
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
            df[col] = df[col].apply(lambda x: pd.NA if x is None else str(x))

    # --- patients: основные поля ---
    patients_cols = [c for c in ["patient_id", "sex", "age_group", "source_id"] if c in df.columns]
    patients = df[patients_cols].copy()
    patients_path = PARQUET_DIR / "patients"
    _reset_table(patients_path)
    patients.to_parquet(patients_path, partition_cols=["source_id"] if "source_id" in patients.columns else None, index=False)

    # --- ecg_features: признаки ЭКГ ---
    ecg_cols = [c for c in ["patient_id", "source_id", "ecg_features"] if c in df.columns]
    ecg = df[ecg_cols].copy()
    ecg_path = PARQUET_DIR / "ecg_features"
    _reset_table(ecg_path)
    ecg.to_parquet(ecg_path, partition_cols=["source_id"] if "source_id" in ecg.columns else None, index=False)

    # --- clinical_signs: клинические признаки ---
    sign_cols = [c for c in ["patient_id", "source_id", "clinical_signs"] if c in df.columns]
    signs = df[sign_cols].copy()
    signs_path = PARQUET_DIR / "clinical_signs"
    _reset_table(signs_path)
    signs.to_parquet(signs_path, partition_cols=["source_id"] if "source_id" in signs.columns else None, index=False)

    return {
        "patients": str(patients_path),
        "ecg_features": str(ecg_path),
        "clinical_signs": str(signs_path),
    }
