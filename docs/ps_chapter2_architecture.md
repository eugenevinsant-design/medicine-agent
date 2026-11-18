# Глава 2 (черновик): Проектирование и реализация

> Раздел ПЗ: архитектура системы и ETL-пайплайн.

## 1. Общая архитектура

Система развёрнута на ноутбуке без GPU и состоит из двух контуров:
Docker Compose (сервисы) и Python venv (ETL, Tools, оценка).

Сервисы Docker Compose:
- Open WebUI (порт 3000): чат, Knowledge, Tools, Web Search.
- Qdrant (порт 6333): векторная база знаний.
- SearxNG (порт 8080): профильный веб-поиск.

Python venv:
- ETL: обезличивание, Parquet, Qdrant (FastEmbed).
- Tools: duckdb_query, web_search_whitelist.
- Eval: метрики, Cohen's kappa.

Внешний LLM API получает только обезличенные данные.

### 1.1. Обоснование выбора компонентов

| Компонент | Выбор | Обоснование |
|---|---|---|
| Оркестратор | Open WebUI | Готовый чат + Tools + Knowledge + Web Search |
| Векторная БД | Qdrant | Лёгкий, REST/gRPC, фильтры payload, FastEmbed |
| Табличное хранилище | Parquet + DuckDB | Колоночный формат, SQL без сервера |
| Эмбеддинги | FastEmbed all-MiniLM-L6-v2 | ONNX, без GPU, совпадает с Open WebUI |
| Веб-поиск | SearxNG | Self-hosted, JSON API, движки pubmed/crossref |
| LLM | Бесплатный API | Нет GPU; function calling через OpenAI-совместимый endpoint |

## 2. Конвейер обработки запроса

1. Врач пишет запрос в Open WebUI (patient_001, ЭКГ: ...).
2. LLM (Native function calling) решает, какие Tool'ы вызвать.
3. Open WebUI вызывает duckdb_query (Parquet), Knowledge/Qdrant (семантический поиск), web_search_whitelist (веб-поиск).
4. LLM синтезирует ответ с источниками и дисклеймером.

## 3. ETL-пайплайн

### 3.1. Этапы

| Этап | Модуль | Вход | Выход |
|---|---|---|---|
| 1. Загрузка | etl/loaders.py | CSV/Parquet/JSON/Excel | list[dict] |
| 2. Обезличивание | etl/anonymize.py | записи с PII | patient_id + mapping |
| 3. Шифрование mapping | etl/anonymize.py | mapping | id_map.parquet.enc |
| 4. Parquet | etl/build_parquet.py | обезличенные записи | data/parquet/* |
| 5. Эмбеддинги + Qdrant | etl/build_qdrant.py | тексты | коллекция medical_knowledge |

Оркестратор - etl/run_etl.py. Источник задаётся в etl/config.py:
SOURCE_INPUT (None - синтетика) и FIELD_MAP (переименование колонок).

### 3.2. Формат Parquet-витрин

| Витрина | Колонки | Партиции |
|---|---|---|
| patients | patient_id, sex, age_group, source_id | source_id |
| ecg_features | patient_id, source_id, ecg_features | source_id |
| clinical_signs | patient_id, source_id, clinical_signs | source_id |

### 3.3. Коллекция Qdrant

| Параметр | Значение |
|---|---|
| Имя | medical_knowledge |
| Размерность | 384 |
| Метрика | Cosine |
| Payload | source_id, patient_id, text, version, access_level |

## 4. Инструменты (Open WebUI Tools)

### 4.1. duckdb_query

- Принимает SQL, разрешает только SELECT/WITH.
- Whitelist таблиц: patients, ecg_features, clinical_signs.
- Принудительный LIMIT <= 1000.
- Возвращает JSON с rows, row_count, source_id.
- Подключён к /app/data/parquet (volume в контейнере).

### 4.2. web_search_whitelist

- Оборачивает SearxNG (http://searxng:8080).
- Фильтр доменов: cr.minzdrav.gov.ru, pubmed.ncbi.nlm.nih.gov, ncbi.nlm.nih.gov, escardio.org, acc.org, cardiosite.ru.
- PII-check перед запросом (ФЗ-152).

## 5. Конфигурация (Docker Compose)

| Переменная | Значение | Назначение |
|---|---|---|
| VECTOR_DB | qdrant | внешняя векторная БД |
| QDRANT_URI | http://qdrant:6333 | адрес из контейнера |
| QDRANT_COLLECTION_NAME | medical_knowledge | имя коллекции |
| RAG_EMBEDDING_MODEL | all-MiniLM-L6-v2 | совпадает с ETL |
| SEARXNG_QUERY_URL | http://searxng:8080/search?q=<query> | встроенный Web Search |
| SEARXNG_URL | http://searxng:8080 | для Tool'а |
| PARQUET_DIR | /app/data/parquet | для duckdb_query |

## 6. Воспроизводимость

1. cp .env.example .env, вписать LLM-ключ и ID_MAP_FERNET_KEY.
2. docker compose up -d.
3. python -m etl.run_etl (в venv).
4. Загрузить Tools в Admin Panel, настроить Web Search и Knowledge.
5. EVAL_MODE=stub python -m eval.run_eval - проверка метрик.

## 7. Технические решения и проблемы (апробация)

| Проблема | Решение |
|---|---|
| qdrant-client шёл через системный прокси -> ReadTimeout | QdrantClient(trust_env=False) |
| Несовпадение моделей эмбеддингов ETL и Open WebUI | Переключить ETL на all-MiniLM-L6-v2 |
| pubmed-движок отдаёт www.ncbi.nlm.nih.gov | Добавить домен в whitelist |
| Кириллица в консоли Windows (cp1251) | sys.stdout.reconfigure(encoding='utf-8') |
| Excel без openpyxl | Добавить openpyxl в requirements |
