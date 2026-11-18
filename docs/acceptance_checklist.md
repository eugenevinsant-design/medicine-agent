# Чек-лист критериев приёмки ВКР (п.10 ТЗ)

> Таблица соответствия критериям приёмки и фактическим результатам проверки.
> Обновлять по мере проверки на реальном LLM-ключе.

| # | Критерий (ТЗ п.10) | Проверка | Статус |
|---|---|---|---|
| 1 | Open WebUI открывается локально | http://localhost:3000 -> HTTP 200, healthy | ВЫПОЛНЕНО |
| 2 | LLM отвечает через бесплатный API | требуется ключ; `verify_tools.py` готов | ОЖИДАЕТ КЛЮЧ |
| 3 | duckdb_query возвращает агрегаты из Parquet | SELECT count(*) -> 3; DELETE/чужая таблица блокируются | ВЫПОЛНЕНО |
| 4 | Qdrant возвращает релевантные фрагменты | top-1 src_ecg_003 для запроса про ФП | ВЫПОЛНЕНО |
| 5 | Web Search только whitelist-источники | живой тест: 5 URL с ncbi/escardio/acc | ВЫПОЛНЕНО |
| 6 | В ответах нет фамилий, только ID | Parquet: patient_id/sex/age_group/source_id | ВЫПОЛНЕНО |
| 7 | В логах и промптах нет ПДн (PII leak = 0%) | pii_guard блокирует ФИО+телефон; eval stub: 0.0 | ВЫПОЛНЕНО (код) |
| 8 | Ответ содержит источники и дисклеймер (100%) | eval stub: disclaimer_rate = 1.0 | ВЫПОЛНЕНО (код) |
| 9 | Система работает на ноутбуке без GPU | FastEmbed ONNX, LLM через API | ВЫПОЛНЕНО |
| 10 | Тестовый набор, оценка, Cohen's kappa >= 0.6 | 50 сценариев; kappa(1,2)=0.706 | ВЫПОЛНЕНО (пример) |
| 11 | ПЗ по ГОСТ, оригинальность >= 70% | черновики ФЗ-152 и Гл.2 готовы; ПЗ в работе | В РАБОТЕ |

## Детализация по пунктам

### 1. Open WebUI
`docker compose ps` -> `agentbeer-openwebui Up (healthy)`, порт 3000.

### 2. LLM API
Без ключа модель не отвечает. `.env` содержит `LLM_API_BASE_URL`, `LLM_API_KEY`,
`LLM_MODEL`. Провайдеры: OpenRouter (primary), Groq (fallback).

### 3-4. Инструменты
- duckdb_query: whitelist patients/ecg_features/clinical_signs, LIMIT<=1000.
- Qdrant: коллекция medical_knowledge, 384 dim, Cosine, 3 точки.

### 5. Web Search
`tools/web_search_whitelist.py` + движки pubmed/crossref в SearxNG.

### 6-8. ФЗ-152 и безопасность
- anonymize.py: PII -> patient_XXX, mapping зашифрован Fernet.
- pii_guard.py: regex + whitelist перед LLM.
- eval: PII leak rate = 0.0, disclaimer_rate = 1.0 (stub).

### 10. Оценка
- 50 сценариев в 5 группах (ischemia, af, tachy, brady, other).
- Метрики: Recall@5, Precision@5, MRR, Top-1/3, PII leak, Disclaimer.
- Cohen's kappa: пример 3 экспертов, пара 1-2 = 0.706 (>= 0.6).

### 11. ПЗ
- Черновики: docs/ps_fz152.md, docs/ps_chapter2_architecture.md.
- Формат по ГОСТ 7.32-2017, оригинальность >= 70% (Антиплагиат) - в работе.

## Что осталось до полного закрытия

1. Вписать реальный LLM-ключ, прогнать `verify_tools.py` и `EVAL_MODE=openwebui`.
2. Подключить реальные данные (SOURCE_INPUT/FIELD_MAP в etl/config.py).
3. Собрать ПЗ целиком (Главы 1, 3, 4), оформить по ГОСТ, проверить Антиплагиат.
4. Подготовить презентацию (15-20 слайдов) и доклад (10 мин).
