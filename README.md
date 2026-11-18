# AGENTBEER — профилированный ИИ-агент-помощник врача

Прототип ВКР: поддержка быстрой диагностики на базе **Open WebUI + Parquet/DuckDB + Qdrant + SearxNG**.

> **Дисклеймер:** система не ставит диагноз. Каждый ответ содержит предупреждение «Требуется проверка врачом».

## Архитектура

```
Ноутбук (без GPU)
├── Docker Compose
│   ├── Open WebUI   — чат, Knowledge, Tools, Web Search
│   ├── Qdrant       — векторная база знаний
│   └── SearxNG      — профильный веб-поиск (whitelist)
├── Python venv
│   ├── ETL          — обезличивание → Parquet → Qdrant (FastEmbed)
│   ├── Tool         — duckdb_query (SELECT-only)
│   └── Eval         — метрики, Cohen's kappa
└── Внешний LLM API  — только обезличенные данные
```

## Быстрый старт

### 1. Окружение

```bash
cp .env.example .env
# впиши LLM_API_KEY (OpenRouter / Groq)
```

### 2. Поднять сервисы

```bash
docker compose up -d
```

- Open WebUI: http://localhost:3000
- Qdrant dashboard: http://localhost:6333/dashboard
- SearxNG: http://localhost:8080

### 3. Python venv (ETL + eval)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. ETL-заглушка (синтетика → Parquet + Qdrant)

```bash
python -m etl.run_etl
```

### 5. Загрузить Tool в Open WebUI

Admin Panel → Tools → `tools/duckdb_query.py` (см. инструкцию в шапке файла).

## ФЗ-152

- ФИО/полисы/адреса/телефоны/ДР заменяются на `patient_XXX` (случайный UUID, **не** производный от ФИО).
- `data/id_map.parquet.enc` — mapping, только локально, шифруется Fernet, **не** попадает в Qdrant/LLM/логи.
- `etl/pii_guard.py` — regex + whitelist перед отправкой в LLM.
- В логах: только `trace_id`, `patient_id`, `source_id`, статус, длительность.

## Структура

```
etl/
├── config.py       пути, whitelist полей
├── anonymize.py    ФИО → ID, шифрование id_map
├── pii_guard.py    проверка промпта перед LLM
├── build_parquet.py
├── build_qdrant.py
└── run_etl.py      оркестратор
tools/
└── duckdb_query.py Open WebUI Tool
eval/
├── scenarios.jsonl тестовый набор
├── metrics.py      Recall@5, Precision@5, MRR, Top-1/3, PII leak, Disclaimer
├── run_eval.py     автоматическая оценка
└── cohen_kappa.py  согласованность экспертов
data/
├── parquet/        витрины
└── id_map.parquet.enc
docs/
└── searxng/settings.yml  whitelist доменов
```

## Инструменты (Open WebUI Tools)

| Tool | Файл | Назначение |
|---|---|---|
| duckdb_query | tools/duckdb_query.py | SELECT по Parquet (whitelist таблиц, LIMIT<=1000) |
| web_search_whitelist | tools/web_search_whitelist.py | Поиск через SearxNG с фильтром доменов + PII-check |

Загрузка: Admin Panel -> Tools -> Create Tool -> вставить файл.

Whitelist доменов (ТЗ п.6.4): cr.minzdrav.gov.ru, pubmed.ncbi.nlm.nih.gov, ncbi.nlm.nih.gov, escardio.org, acc.org, cardiosite.ru.

## Оценка

EVAL_MODE=stub python -m eval.run_eval

EVAL_MODE=openwebui OPENWEBUI_API_KEY=<token> OPENWEBUI_MODEL=<model> python -m eval.run_eval

Метрики: Recall@5, Precision@5, MRR, Top-1/3, Disclaimer rate (цель 100%), PII leak rate (цель 0%). Cohen's kappa: python -m eval.cohen_kappa.

## Ограничения

- Нет GPU: LLM только через внешний API.
- Нет отдельного FastAPI: оркестрация — средствами Open WebUI.
- Реальные данные подключаются позже; сейчас — синтетика-заглушка.

## Лицензия / академическое использование

Прототип для ВКР. Требуется проверка врачом.
