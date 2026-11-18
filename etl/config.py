"""Конфигурация ETL-пайплайна."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Пути ---
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PARQUET_DIR = DATA_DIR / "parquet"
ID_MAP_PATH = DATA_DIR / "id_map.parquet.enc"
SYNTHETIC_INPUT = ROOT / "etl" / "synthetic" / "patients.json"

# Реальный источник от руководителя: подключить одной строкой (CSV/Parquet/JSON/Excel).
# Пример: SOURCE_INPUT = ROOT / "data" / "incoming" / "patients.csv"
SOURCE_INPUT: Path | None = None  # None -> использовать SYNTHETIC_INPUT

# Маппинг полей, если у источника другие имена колонок:
# FIELD_MAP = {"ФИО": "full_name", "Дата рождения": "birth_date"}
FIELD_MAP: dict[str, str] = {}

# --- Qdrant ---
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "medical_knowledge")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

# --- ФЗ-152 ---
ID_MAP_FERNET_KEY = os.getenv("ID_MAP_FERNET_KEY", "")

# Поля, которые разрешено отправлять во внешнюю LLM (whitelist).
# Всё остальное считается потенциальным PII и блокируется pii_guard.
LLM_ALLOWED_FIELDS = {
    "patient_id",
    "source_id",
    "age_group",
    "sex",
    "ecg_features",
    "clinical_signs",
    "text",
    "version",
    "access_level",
}

# Поля-идентификаторы, которые ВСЕГДА заменяются на ID
PII_FIELDS = {
    "full_name",
    "fio",
    "last_name",
    "first_name",
    "middle_name",
    "policy_number",
    "oms",
    "address",
    "phone",
    "birth_date",
    "dob",
    "passport",
    "snils",
    "email",
}

# Whitelist таблиц для duckdb_query (Parquet-витрины)
PARQUET_TABLES = {
    "patients",
    "ecg_features",
    "clinical_signs",
}
