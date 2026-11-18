"""Оркестратор ETL: источник (CSV/Parquet/JSON/Excel) -> обезличивание -> Parquet -> Qdrant."""
from __future__ import annotations

import logging

from etl.anonymize import anonymize_records, save_mapping_encrypted
from etl.build_parquet import write_parquet
from etl.build_qdrant import upload_to_qdrant
from etl.config import FIELD_MAP, SOURCE_INPUT, SYNTHETIC_INPUT
from etl.loaders import load_records

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("etl")


def main() -> None:
    # SOURCE_INPUT=None -> синтетика-заглушка; иначе реальный источник от руководителя
    source = SOURCE_INPUT or SYNTHETIC_INPUT
    log.info("Источник: %s", source)

    records = load_records(source, field_map=FIELD_MAP or None)
    log.info("Загружено исходных записей: %d", len(records))

    anonymized, mapping = anonymize_records(records)
    log.info("Обезличено записей: %d", len(anonymized))

    save_mapping_encrypted(mapping)
    log.info("Mapping сохранён зашифрованным (локально)")

    paths = write_parquet(anonymized)
    log.info("Parquet-витрины: %s", paths)

    uploaded = upload_to_qdrant(anonymized)
    log.info("Загружено в Qdrant: %d векторов", uploaded)

    log.info("ETL завершён успешно")


if __name__ == "__main__":
    main()
