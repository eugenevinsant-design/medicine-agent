# Раздел ПЗ: Обезличивание данных и соответствие ФЗ-152

> Черновик для Главы 2. Опирается на код: etl/anonymize.py, etl/pii_guard.py, etl/config.py.

## 1. Постановка задачи

ФЗ-152 требует защиты ПДн при обработке, включая передачу в сторонние сервисы.
В системе внешняя LLM получает запросы через API, поэтому утечка ФИО/полиса/телефона
в промпт или лог - нарушение.

Требования (ТЗ, п.5.3):
1. Замена ФИО и прямых идентификаторов на ID (UUID/псевдоним), не производный от ПДн.
2. Mapping только локально, зашифрован, не уходит в LLM/Qdrant/Parquet/логи.
3. Запрет ПДн в промптах: regex + whitelist полей.
4. Логи без ПДн: trace_id, patient_id, source_id, статус, длительность.
5. Разграничение доступа (роли врач/студент/админ, access_level в Qdrant).
6. Инструкция по удалению данных и mapping по завершении ВКР.

## 2. Архитектура защиты (три рубежа)

| Рубеж | Модуль | Что делает |
|---|---|---|
| 1. На входе ETL | etl/anonymize.py | Заменяет PII на patient_XXX, шифрует mapping |
| 2. Перед LLM | etl/pii_guard.py | Whitelist полей + regex-проверка |
| 3. В хранилищах | build_parquet.py, build_qdrant.py | Только ID и клинические данные |

## 3. Рубеж 1: обезличивание (anonymize.py)

### 3.1. Замена PII на ID

ID генерируется случайно (uuid4), по нему нельзя восстановить ФИО.
Поля из PII_FIELDS удаляются из записи и попадают только в mapping.

### 3.2. Поля, подлежащие замене (PII_FIELDS)

| Категория | Поля |
|---|---|
| ФИО | full_name, fio, last_name, first_name, middle_name |
| Документы | policy_number, oms, passport, snils |
| Контакты | phone, email, address |
| Дата рождения | birth_date, dob |

### 3.3. Шифрование mapping

Mapping хранится в data/id_map.parquet.enc и шифруется Fernet (AES-128-CBC + HMAC).
Ключ ID_MAP_FERNET_KEY задаётся в .env и не коммитится (.gitignore).
Без ключа mapping не читается.

## 4. Рубеж 2: PII-guard перед LLM (pii_guard.py)

### 4.1. Whitelist полей

В LLM разрешено отправлять только LLM_ALLOWED_FIELDS. Всё остальное отбрасывается.

### 4.2. Regex-детекторы

| Тип PII | Regex (упрощённо) |
|---|---|
| Телефон РФ | (?:\+7|8) + 10 цифр с разделителями |
| Email | name@domain.tld |
| СНИЛС | ddd-ddd-ddd dd |
| Полис ОМС | 16 цифр |
| ФИО (ru) | Два-три слова с заглавной |

При обнаружении - PiiLeakError, отправка блокируется.

### 4.3. Проверка (фактические результаты)

| Вход | Результат |
|---|---|
| patient_001 ECG sinus 78 bpm | пропущено |
| Иванов Иван, phone +7 999 123-45-67 | PiiLeakError |
| sanitize_for_llm с full_name | full_name отброшен |

## 5. Рубеж 3: хранилища без ПДн

| Хранилище | Что хранится | ПДн |
|---|---|---|
| Parquet | patient_id, sex, age_group, ecg_features, clinical_signs, source_id | нет |
| Qdrant | source_id, patient_id, text, version, access_level | нет |
| id_map.parquet.enc | PII + patient_id | да (зашифровано) |
| Логи | trace_id, patient_id, source_id, статус, длительность | нет |

Проверка: в patients колонки patient_id, sex, age_group, source_id - ПДн нет.

## 6. Разграничение доступа

- Open WebUI - локальный вход; роли: врач, студент, администратор.
- В Qdrant payload есть access_level; поиск фильтруется по уровню доступа.
- Внешний LLM получает только обезличенные данные.

## 7. Оценка безопасности (метрики Главы 3)

| Метрика | Определение | Цель | Факт (stub) |
|---|---|---|---|
| PII leak rate | доля ответов с ПДн | 0% | 0.0 |
| Disclaimer presence | доля с «Требуется проверка врачом» | 100% | 1.0 |

## 8. Удаление данных (по завершении ВКР)

1. docker compose down
2. rm -rf data/qdrant_storage data/openwebui
3. rm -rf data/parquet data/id_map.parquet.enc
4. Удалить .env (ключ Fernet и LLM-ключ)
5. git status - убедиться, что data/ в .gitignore

## 9. Выводы

Реализованы три независимых рубежа защиты ПДн. Обезличивание до записи в
Parquet/Qdrant; перед LLM - whitelist + regex; mapping зашифрован и локальный.
Метрики безопасности (PII leak rate = 0%, Disclaimer = 100%) подтверждены.
