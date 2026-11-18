"""Загрузка обезличенных текстов в Qdrant через FastEmbed (локально, без GPU)."""
from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from etl.config import EMBEDDING_DIM, EMBEDDING_MODEL, QDRANT_COLLECTION, QDRANT_URL


def _embedder():
    # Импорт здесь, чтобы ETL можно было запускать без скачивания модели на этапе импорта
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=EMBEDDING_MODEL)


def ensure_collection(client: QdrantClient) -> None:
    collections = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


def _documents_from_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    docs = []
    for rec in records:
        text_parts = []
        if rec.get("clinical_signs"):
            text_parts.append(f"Клинические признаки: {rec['clinical_signs']}")
        if rec.get("ecg_features"):
            text_parts.append(f"ЭКГ: {rec['ecg_features']}")
        if not text_parts:
            continue
        docs.append({
            "source_id": rec.get("source_id", "unknown"),
            "patient_id": rec.get("patient_id"),
            "text": " ".join(text_parts),
            "version": "v1",
            "access_level": "doctor",
        })
    return docs


def upload_to_qdrant(records: list[dict[str, Any]]) -> int:
    docs = _documents_from_records(records)
    if not docs:
        return 0

    # trust_env=False: не использовать системный HTTP-прокси (иначе ReadTimeout на localhost)
    client = QdrantClient(url=QDRANT_URL, timeout=30, trust_env=False)
    ensure_collection(client)

    embedder = _embedder()
    texts = [d["text"] for d in docs]
    vectors = list(embedder.embed(texts))

    points = []
    for i, (doc, vec) in enumerate(zip(docs, vectors)):
        points.append(PointStruct(id=i + 1, vector=vec.tolist(), payload=doc))

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(points)
