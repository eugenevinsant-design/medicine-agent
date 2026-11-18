# Демо-сценарий и план скриншотов (презентация, п.9 ТЗ)

> 14 слайдов, регламент доклада 10 минут. Для каждого слайда - что показать
> и какой скриншот/команда это подтверждает.

## Слайд 1. Титульный
- Тема ВКР, ФИО, руководитель, вуз, год.
- Скриншот: нет (шаблон).

## Слайд 2. Цель и задачи
- Цель: прототип ИИ-агента-помощника врача.
- Задачи: ETL+обезличивание, RAG на Qdrant, duckdb_query, web-поиск, оценка.

## Слайд 3. Актуальность и аналоги
- Аналоги: KardiaMobile, CorVista, PMcardio.
- Отличие: локальный ноутбук без GPU, ФЗ-152, открытый стек.

## Слайд 4. Архитектура системы
- Схема: Open WebUI + Qdrant + SearxNG + Python venv + внешний LLM.
- Скриншот: `docker compose ps` (3 контейнера Up).

## Слайд 5. ETL и обезличивание (ФЗ-152)
- Поток: загрузка -> PII->ID -> Parquet -> Qdrant.
- Скриншот: лог `python -m etl.run_etl` (3 записи, 3 точки).
- Таблица: PII_FIELDS (из ps_fz152.md).

## Слайд 6. Реализация Open WebUI + Qdrant + DuckDB
- Скриншот: Open WebUI (http://localhost:3000).
- Скриншот: Qdrant dashboard (коллекция medical_knowledge, 3 точки).
- Скриншот: результат `duckdb_query` (JSON rows).

## Слайд 7. Методика оценки: метрики
- Recall@5, Precision@5, MRR, Top-1/3, Disclaimer, PII leak, kappa.
- Таблица из ps_chapter2_architecture.md / Главы 3.

## Слайд 8. Тестовый набор
- 50 сценариев, 5 групп по 10.
- Скриншот: фрагмент eval/scenarios.jsonl.

## Слайд 9. Результаты автоматической оценки
- Скриншот: вывод `EVAL_MODE=stub python -m eval.run_eval`.
- Отметить: stub-значения; реальные - после ключа.

## Слайд 10. Результаты экспертной оценки
- Скриншот: вывод `cohen_kappa --file eval/expert_scores.example.csv`.
- kappa(1,2)=0.706 (цель достигнута), разброс по парам - для обсуждения.

## Слайд 11. Анализ ошибок и ограничения
- Малый объём тестов, один LLM, stub-метрики.
- Таблица «проблема -> решение» (Глава 2, разд.7).

## Слайд 12. Демонстрация работы
- Скриншоты: чат Open WebUI с ответом агента (источники + дисклеймер).
- Пока не сделано (нужен LLM-ключ) - пометить как «демо после подключения ключа».

## Слайд 13. Выводы и рекомендации
- Прототип работает: ETL, Qdrant, Tools, ФЗ-152, оценка.
- Рекомендации: реальные данные, расширение тестов, 2-3 эксперта.

## Слайд 14. Список источников
- ГОСТ, ФЗ-152, статьи (cyberleninka), документация Open WebUI/Qdrant/DuckDB.

## Команды для скриншотов

| Слайд | Команда/действие |
|---|---|
| 4 | docker compose ps |
| 5 | .venv/Scripts/python.exe -m etl.run_etl |
| 6 | curl localhost:6333/collections/medical_knowledge |
| 9 | EVAL_MODE=stub .venv/Scripts/python.exe -m eval.run_eval |
| 10 | .venv/Scripts/python.exe -m eval.cohen_kappa --file eval/expert_scores.example.csv |

## Что снять после получения LLM-ключа

1. Чат в Open WebUI: запрос про patient_001 + вызов duckdb_query + ответ с источниками.
2. Чат с web_search_whitelist: ссылки только с whitelist-доменов.
3. EVAL_MODE=openwebui - реальные метрики.
