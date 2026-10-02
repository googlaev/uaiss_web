# UAISS — Общая архитектура

## Что такое UAISS

**UAISS** (Управление Автоматизированными Информационными Системами Сотрудников) — корпоративная система для отслеживания сроков действия экзаменов/допусков сотрудников и их рабочих статусов (больничный, командировка, отпуск).

Версия: 1.0.0 | Язык интерфейса: русский

---

## Компоненты системы

```
┌──────────────────────────────────────────────────────────┐
│                   Мобильное приложение                    │
│           Android APK (Capacitor + HTML/JS/CSS)           │
│           Или веб-браузер (www/index.html)                │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTPS REST API (JSON)
                        │ Authorization: Bearer <JWT>
┌───────────────────────▼──────────────────────────────────┐
│                    Бэкенд (FastAPI)                        │
│           test_py_original.py  │  PORT 8000               │
│                                │                          │
│   ┌─────────────────┐   ┌──────▼────────────────┐        │
│   │   APScheduler   │   │   SQLite3 (exams.db)  │        │
│   │ (нотификации    │   │   users / exams /      │        │
│   │  в 09:00/день)  │   │   exam_types /         │        │
│   └─────────────────┘   │   user_status          │        │
│                         └───────────────────────┘        │
│                                                          │
│   ┌─────────────────┐   ┌──────────────────────┐        │
│   │  Gmail SMTP     │   │  Firebase Admin SDK   │        │
│   │ (email-уведом.) │   │  (FCM push — опция.)  │        │
│   └─────────────────┘   └──────────────────────┘        │
│   ┌───────────────────────────────────────────┐         │
│   │  MAX Bot API (botapi.max.ru)               │         │
│   │  в этом же процессе (фоновый поток)        │         │
│   └───────────────────────────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

---

## Стек технологий

| Слой | Технология | Версия |
|------|-----------|--------|
| Мобильная оболочка | Capacitor | 8.4.1 |
| Фронтенд | Vanilla JS + HTML + CSS | ES6+ |
| Бэкенд | FastAPI (Python) | актуальная |
| ASGI-сервер | Uvicorn | актуальная |
| БД | SQLite3 | (stdlib) |
| Авторизация | JWT HS256 | PyJWT |
| Планировщик | APScheduler | актуальная |
| Email | smtplib (stdlib) + Gmail SMTP | — |
| Push (опция) | Firebase Admin SDK + FCM | актуальная |
| Android SDK | min 24 / target 36 | — |
| Сборка Android | Gradle | 8.14.3 |

---

## Взаимодействие компонентов

### Аутентификация

```
Клиент → POST /api/v1/auth/login {login, password}
         ← {access_token, user_id, full_name, role}

Клиент сохраняет access_token в localStorage('authToken')
Все последующие запросы: Authorization: Bearer <token>
Срок жизни токена: 8 часов (настраивается в config.json)
При 401 → автоматический logout + редирект на логин
```

### Формат данных

- Протокол: **REST over HTTPS**
- Формат: **JSON** (Content-Type: application/json)
- Даты в API: формат **ДД.ММ.ГГГГ** (`date` при вводе передаётся в YYYY-MM-DD, бэкенд конвертирует)
- CORS: разрешены все origins (`*`) — в продакшене следует ограничить

### Уведомления

**Email** — основной канал:
- APScheduler запускает `check_and_send_notifications_sync()` ежедневно в 09:00
- Письма за 30, 7, 3, 2, 1 день до истечения экзамена + при просрочке
- Gmail SMTP (smtp.gmail.com:587 + STARTTLS)

**Push (FCM)** — опциональный канал (не активирован в основном коде):
- Код находится в `backend_fcm_patch.py` и `backend_push_additions.py`
- Требует `serviceAccountKey.json` от Firebase-проекта `uaiss-4862a`
- Мобильное приложение поддерживает регистрацию FCM-токена и локальные нотификации

**MAX** — дополнительный канал (мессенджер MAX, botapi.max.ru), по тем же порогам дней и в том же ежедневном прогоне, что и email:
- Привязать аккаунт можно тремя способами: (1) открыть **мини-приложение UAISS внутри MAX** и один раз войти по логину/паролю — привязка происходит автоматически по подписи `initData`; (2) в веб/APK-профиле → «Привязать MAX» → одноразовый код → отправить боту `/link КОД`; (3) сразу написать боту `/фио ...`
- Код/ФИО-привязку обрабатывает фоновый поток внутри самого бэкенда (long polling `botapi.max.ru/updates`, запускается `start_max_bot()` при старте FastAPI-приложения) — отдельный процесс не нужен, пишет `max_chat_id` в таблицу `users`
- Бэкенд (`test_py_original.py`) отправляет напоминания через `send_max_message()` в той же функции `check_and_send_notifications_sync()`, что и email — по расписанию APScheduler (ежедневно) и при ручном запуске `/api/v1/notifications/send` или `/api/v1/max/notifications/send`
- Настройки — секция `max` в `config.json` (`enabled`, `token`, `api_url`, `bot_username`)

**Мини-приложение MAX** — та же SPA (`www/index.html`), что и в APK, отдаётся бэкендом по `/maxapp/` (см. `docs/BACKEND.md`, раздел «MAX-уведомления и мини-приложение»). Регистрируется в `business.max.ru/self` как мини-апп бота.

---

## Роли пользователей

| Роль | Возможности |
|------|------------|
| `employee` | Свои экзамены, свои статусы, смена пароля/email |
| `admin` | Всё то же + просмотр всех сотрудников, CSV-выгрузка, ручной запуск уведомлений |

---

## Карта директорий

```
C:\edu\appUAISS\
├── www/
│   └── index.html          # SPA: весь UI + JS-логика (132 КБ)
├── android/                # Android-проект (Capacitor native shell)
│   ├── app/
│   │   ├── src/main/
│   │   │   └── AndroidManifest.xml
│   │   ├── google-services.json   # Firebase конфиг (проект uaiss-4862a)
│   │   └── build.gradle
│   └── variables.gradle    # minSdk:24, compileSdk:36
├── test_py_original.py     # Весь бэкенд (FastAPI, 1098 строк)
├── config.json             # Конфиг бэкенда (создаётся автоматически)
├── exams1.db               # SQLite БД (текущая, production)
├── capacitor.config.json   # Конфиг Capacitor
├── package.json            # Node-зависимости (Capacitor)
├── backend_fcm_patch.py    # Инструкция по интеграции FCM
├── backend_push_additions.py # Вспомогательные FCM-функции (не подключены)
├── quiz_bot.py               # Исходный пример MAX-бота (не используется в проде, справочно)
├── Dockerfile               # Образ бэкенда (только test_py_original.py + зависимости)
├── docker-compose.yml       # Сборка и запуск контейнера, volume для config.json/exams.db
├── config.example.json      # Шаблон config.json без реальных секретов
└── docs/                   # Эта документация
```

---

## Продакшен

- Бэкенд развёрнут по адресу: `https://bot.codle.ru`
- Фронтенд hardcode'ит этот адрес в `www/index.html:230` (`const SERVER_URL`)
- Деплой: `Dockerfile` + `docker-compose.yml` (см. `docs/SETUP.md`, раздел «Docker»); TLS/домен — через внешний реверс-прокси, контейнер слушает `:8000` изнутри
- CI/CD **не обнаружено** — сборка и запуск образа ручные (`docker compose up -d --build`)
