# Руководство по настройке Open WebUI (UI)

> Для Приложения ВКР. Все шаги выполняются после `docker compose up -d`.
> Адрес: http://localhost:3000

## 1. Первый вход

1. Открой http://localhost:3000.
2. Зарегистрируй первого пользователя — он автоматически становится **admin**.
3. Дальнейшие пользователи (врач, студент) создаются в Admin Panel → Users.

## 2. Загрузка Tool: duckdb_query

1. Войди как admin.
2. **Admin Panel → Tools → Create Tool** (кнопка «+»).
3. Вставь содержимое `tools/duckdb_query.py`.
4. **Save**.
5. Убедись, что Tool **включён** (toggle ON) и в его Valves задан `PARQUET_DIR=/app/data/parquet`
   (в контейнере этот путь уже смонтирован; см. `docker-compose.yml`).

## 3. Загрузка Tool: web_search_whitelist

1. **Admin Panel → Tools → Create Tool**.
2. Вставь содержимое `tools/web_search_whitelist.py`.
3. **Save**, включи Tool.
4. Valves: `SEARXNG_URL=http://searxng:8080` (в контейнере это уже прокинуто через env;
   если Valve пустой — Open WebUI возьмёт значение из окружения контейнера).

## 4. Web Search → SearxNG (встроенный поиск)

Это **отдельный** механизм от Tool'а `web_search_whitelist`.

1. **Admin Panel → Settings → Web Search**.
2. Включи **Web Search**.
3. **Web Search Engine**: выбери **searxng**.
4. **Searxng Query URL**: `http://searxng:8080/search?q=<query>`
   (именно с `<query>` в конце — Open WebUI подставит запрос).
5. **Save**.

Проверка: открой чат, нажми иконку «+» у поля ввода → включи **Web Search** → задай вопрос,
требующий свежих данных. В ответе должны появиться ссылки.

## 5. Модель с function calling (Native mode)

> **Важно:** Native mode — режим по умолчанию в Open WebUI. Менять глобально ничего не нужно,
> если модель его поддерживает.

1. Подключи LLM-провайдера: **Admin Panel → Settings → Connections**
   (OpenAI-совместимый endpoint: OpenRouter / Groq).
2. **Admin Panel → Settings → Models** → выбери модель → **Edit** (карандаш).
3. **Advanced Params → Function Calling**: должно быть **Native** (по умолчанию).
   Если стоит иное — переключи на Native и сохрани.
4. В том же окне включи **Builtin Tools → Web Search** (чтобы модель могла вызывать
   встроенный `search_web` / `fetch_url` в Native mode).

### Требования к модели

Native tool calling надёжно работает на актуальных моделях. Для бесплатного API
рекомендуется `openai/gpt-oss-20b:free` (OpenRouter) или `openai/gpt-oss-20b` (Groq).
Малые локальные модели (<30B) часто ломают JSON tool calls — для них Native mode
не рекомендуется[citation:3].

## 6. Knowledge → Qdrant

> Требуется согласование модели эмбеддингов (см. отдельный раздел ПЗ).
> По умолчанию Open WebUI использует `sentence-transformers/all-MiniLM-L6-v2`,
> а ETL — FastEmbed `BAAI/bge-small-en-v1.5`. Векторные пространства разные.

1. **Admin Panel → Settings → Documents**.
2. **Embedding Model Engine**: выбери движок, совместимый с ETL
   (или переключи ETL на модель Open WebUI — вариант B).
3. **Vector DB**: должен быть **qdrant** (уже задан через env).
4. **Qdrant URI**: `http://qdrant:6333` (задан через env).
5. **Collection Name**: `medical_knowledge` (задан через env).
6. После смены модели эмбеддингов нажми **Reindex** для Knowledge-базы.

## 7. Включение Tool'ов для модели

1. **Admin Panel → Settings → Models** → выбери модель → **Edit**.
2. Прокрути до **Tools** (или **Workspace Tools**).
3. Включи оба Tool'а: `duckdb_query`, `web_search_whitelist`.
4. **Save**.

Теперь в чате модель сможет вызывать эти Tool'ы в Native mode.

## 8. Проверка сквозного сценария

1. Новый чат → выбери модель.
2. Запрос: `Пациент patient_001, ЭКГ: синусовый ритм, ЧСС 78, QT 410 мс.
   Какие средние QT по пациентам 60-69 лет?`
3. Ожидаемо: модель вызывает `duckdb_query`, получает агрегат из Parquet,
   отвечает с источником и дисклеймером «Требуется проверка врачом».

## Замечания по ФЗ-152

- В промптах и Tool-вызовах допускаются только `patient_XXX` (ID), без ФИО/телефонов.
- `web_search_whitelist` блокирует запросы с PII до отправки в SearxNG.
- Логи Open WebUI не должны содержать ПДн; при необходимости настрой Filter-функцию
  для редактирования сообщений на входе/выходе.
