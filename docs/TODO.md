# UAISS — Технический долг и незавершённые места

## TODO/FIXME в коде

### www/index.html (встроенный Capacitor native-bridge.js)

| Строка | Комментарий | Контекст |
|--------|------------|---------|
| ~143 | `// TODO: export as Cap function` (×2) | В скрипте native-bridge Capacitor — внутреннее замечание из исходников библиотеки |
| ~688 | `//TODO: Add progress event emission on native side` | В том же bridge-скрипте, касается событий прогресса |

> Эти TODO — в коде сторонней библиотеки Capacitor (native-bridge.js), а не в прикладной логике. Исправлять их не нужно.

В `test_py_original.py` явных TODO/FIXME не обнаружено.

---

## Архитектурный технический долг

### Критичное

| # | Проблема | Файл/Место | Рекомендация |
|---|----------|-----------|--------------|
| 1 | **SHA-256 без соли для паролей** — уязвимость к rainbow table атакам | `test_py_original.py:197` `hash_password()` | Заменить на `bcrypt` или `argon2-cffi` |
| 2 | **SMTP-пароль в config.json** — хранится открытым текстом | `config.json: smtp.password` | Использовать переменную окружения `SMTP_PASSWORD` |
| 3 | **CORS `allow_origins=["*"]`** — разрешает запросы с любого домена | `test_py_original.py:80-86` | Ограничить до `["https://bot.codle.ru"]` в продакшене |
| 4 | **JWT без blacklist** — logout не инвалидирует токен, старые токены продолжают работать 8 часов | `test_py_original.py:436` | Хранить blacklist в Redis или сократить TTL до 15-30 мин + refresh token |

### Важное

| # | Проблема | Файл/Место | Рекомендация |
|---|----------|-----------|--------------|
| 5 | **Расхождение расчёта дат:** `/exams/my` считает `duration * 30 дней` (приближённо), уведомления — через `calendar.monthrange` (точно) | `test_py_original.py:558` vs `test_py_original.py:345` | Унифицировать метод расчёта в одной утилите |
| 6 | **Весь фронтенд в одном файле** — 132 КБ HTML с вёрсткой, стилями и логикой. Сложно поддерживать и тестировать | `www/index.html` | Рассмотреть разбивку на модули (ES modules) или переход на лёгкий фреймворк |
| 7 | **Migrations через ALTER TABLE** — при росте схемы станет неуправляемым | `test_py_original.py:128-190` `check_and_fix_database()` | Внедрить Alembic или собственный version-based migration |
| 8 | **Отсутствие rate-limiting на `/auth/login`** — brute-force не ограничен | `test_py_original.py:416` | Добавить `slowapi` или nginx-уровень ограничений |
| 9 | **SQLite** — не подходит для конкурентной записи при нескольких воркерах | `config.json: database.path` | При горизонтальном масштабировании — PostgreSQL |

### Незначительное / Улучшения

| # | Проблема | Место | Рекомендация |
|---|----------|-------|--------------|
| 10 | **Legacy-поля в таблице exams** — `notification_sent`, `month_notification_sent`, `week_notification_sent`, `exam_day_notification_sent`, `end_day_notification_sent` не используются | `test_py_original.py:598` | Удалить при следующей миграции |
| 11 | **SERVER_URL hardcode в index.html** — меняется вручную при каждой сборке | `www/index.html:230` | Вынести в `capacitor.config.json` (server.url) или build-скрипт |
| 12 | **Название основного файла** `test_py_original.py` — вводит в заблуждение, похоже на временный файл | — | Переименовать в `main.py` или `server.py` |
| 13 | **FCM-интеграция не завершена** — код написан (`backend_fcm_patch.py`), но не подключён к основному серверу | `backend_fcm_patch.py`, `backend_push_additions.py` | Внедрить патч или удалить незаконченный код |
| 14 | **Даты как TEXT** в SQLite — нет нативных SQL-операций с датами | Вся БД | При рефакторинге перейти на хранение в ISO-формате `YYYY-MM-DD` |
| 15 | **Отсутствие логирования** — ошибки пишутся в stdout через print(), нет структурированных логов | `test_py_original.py` | Подключить `logging` модуль Python или `loguru` |
| 16 | **GET / возвращает JSON вместо SPA** — если нет `new_uaiss.html`, API выдаёт текстовый ответ вместо приложения | `test_py_original.py:1035-1039` | Зафиксировать путь к `www/index.html` |
| 17 | **Нет CI/CD** — сборка образа и `docker compose up` вручную; Docker уже есть (`Dockerfile`, `docker-compose.yml`) | Весь проект | Добавить workflow (GitHub Actions/GitLab CI): сборка образа + пуш в registry |
| 18 | **Нет тестов** — ни unit, ни интеграционных | Весь проект | Добавить хотя бы pytest-тесты на критичные эндпоинты (login, add exam, notifications) |

---

## Незавершённые функции

| Функционал | Статус | Где |
|-----------|--------|-----|
| MAX-уведомления | ✅ Реализовано (эндпоинты `/max/*`, встроенный приём сообщений бота, привязка в профиле веб/APK; шлются ежедневно по тем же порогам дней, что и email, в `check_and_send_notifications_sync()`) | `test_py_original.py`, `www/index.html` |
| Мини-приложение MAX | ✅ Реализовано — та же SPA, отдаётся по `/maxapp/`, автовход через `initData` (`/max/webapp-auth`); требует регистрации URL в `business.max.ru/self` | `test_py_original.py`, `www/index.html`, `docs/SETUP.md` |
| Docker-деплой | ✅ Реализовано (`Dockerfile` + `docker-compose.yml`) | корень проекта |
| FCM push-уведомления с сервера | Написан, но не интегрирован | `backend_fcm_patch.py`, `backend_push_additions.py` |
| Журнал уведомлений в интерфейсе | UI-элемент есть, бэкенд-эндпоинт `/notifications/log` не реализован | `www/index.html` (bell icon) |
| Управление пользователями (admin) | Нет CRUD для создания/удаления пользователей через UI | Отсутствует |
| Управление типами экзаменов (admin) | Типы можно добавить только напрямую в БД | Отсутствует |
| Экспорт статусов | Есть только CSV экзаменов, статусы не экспортируются | Отсутствует |

---

## Приоритет исправлений

```
🔴 Немедленно (безопасность):
   #1 SHA-256 → bcrypt
   #2 SMTP пароль в env
   #3 CORS ограничить

🟠 Скоро (стабильность):
   #5 Унифицировать расчёт дат
   #8 Rate-limit на login
   #12 Переименовать main-файл

🟡 Планово (качество):
   #6 Разбить index.html на модули
   #7 Миграции через Alembic
   #13 Завершить FCM или удалить
   #17 CI/CD (Docker уже есть)
   #18 Тесты
```
