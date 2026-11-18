"""Обезличивание по ФЗ-152: замена PII на случайные ID + шифрование mapping."""
from __future__ import annotations

import json
import secrets
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from cryptography.fernet import Fernet

from etl.config import ID_MAP_FERNET_KEY, ID_MAP_PATH, PII_FIELDS


def _new_patient_id() -> str:
    """Случайный псевдоним, НЕ производный от ФИО."""
    return f"patient_{uuid.uuid4().hex[:12]}"


def _fernet() -> Fernet:
    if not ID_MAP_FERNET_KEY or ID_MAP_FERNET_KEY == "change-me-generate-your-own-key":
        raise RuntimeError(
            "ID_MAP_FERNET_KEY не задан. Сгенерируй: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(ID_MAP_FERNET_KEY.encode())


def anonymize_records(records: list[dict[str, Any]]) -> tuple[list[dict], dict[str, dict]]:
    """Возвращает (обезличенные записи, mapping original_identifier -> pii).

    Mapping содержит только PII и строится по исходному идентификатору
    (например, по ФИО), чтобы позже можно было восстановить связь локально.
    """
    anonymized: list[dict] = []
    mapping: dict[str, dict] = {}

    for rec in records:
        original_key = rec.get("full_name") or rec.get("fio") or rec.get("patient_id")
        if original_key is None:
            original_key = f"anon_{secrets.token_hex(4)}"

        patient_id = _new_patient_id()
        pii = {k: rec[k] for k in PII_FIELDS if k in rec}
        mapping[original_key] = {"patient_id": patient_id, **pii}

        clean = {k: v for k, v in rec.items() if k not in PII_FIELDS}
        clean["patient_id"] = patient_id
        anonymized.append(clean)

    return anonymized, mapping


def save_mapping_encrypted(mapping: dict[str, dict], path: Path = ID_MAP_PATH) -> None:
    """Сохранить mapping зашифрованным (Fernet). Только локально."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(mapping, ensure_ascii=False).encode("utf-8")
    token = _fernet().encrypt(payload)
    path.write_bytes(token)


def load_mapping_encrypted(path: Path = ID_MAP_PATH) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(f"Mapping не найден: {path}")
    token = path.read_bytes()
    payload = _fernet().decrypt(token)
    return json.loads(payload.decode("utf-8"))


def mapping_to_dataframe(mapping: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for original_key, info in mapping.items():
        rows.append({"original_key": original_key, **info})
    return pd.DataFrame(rows)
