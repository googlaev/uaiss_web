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
│           test.py  │  PORT 8000               │
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

**Push (FCM)** — активный канал наряду с email и MAX:
- `firebase_admin` инициализируется при старте `test.py` из `serviceAccountKey.json` (Firebase-проект `uaiss-4862a`); без файла — не падает, просто пишет предупреждение и push молча не работает
- Токены устройств копятся в `fcm_tokens` (`POST /fcm-token`), шлются через `send_push_to_user()`/`send_fcm_push()`, параллельно email/MAX в `check_and_send_notifications_sync()`
- Плюс ручные `/notifications/test-push` (себе) и `/notifications/broadcast` (admin, всем/выбранным)
- `backend_fcm_patch.py`/`backend_push_additions.py` в корне — черновики из более ранней стадии этой же разработки, не используются

**MAX** — дополнительный канал (мессенджер MAX, botapi.max.ru), по тем же порогам дней и в том же ежедневном прогоне, что и email:
- Привязать аккаунт можно тремя способами: (1) открыть **мини-приложение UAISS внутри MAX** и один раз войти по логину/паролю — привязка происходит автоматически по подписи `initData`; (2) в веб/APK-профиле → «Привязать MAX» → одноразовый код → отправить боту `/link КОД`; (3) сразу написать боту `/фио ...`
- Код/ФИО-привязку обрабатывает фоновый поток внутри самого бэкенда (long polling `botapi.max.ru/updates`, запускается `start_max_bot()` при старте FastAPI-приложения) — отдельный процесс не нужен, пишет `max_chat_id` в таблицу `users`
- Бэкенд (`test.py`) отправляет напоминания через `send_max_message()` в той же функции `check_and_send_notifications_sync()`, что и email — по расписанию APScheduler (ежедневно) и при ручном запуске `/api/v1/notifications/send` или `/api/v1/max/notifications/send`
- Настройки — секция `max` в `config.json` (`enabled`, `token`, `api_url`, `bot_username`)

**Мини-приложение MAX** — та же SPA (`www/index.html`), что и в APK, отдаётся бэкендом по `/maxapp/` (см. `docs/BACKEND.md`, раздел «MAX-уведомления и мини-приложение»). Регистрируется в `business.max.ru/self` как мини-апп бота.

---

## Роли пользователей

| Роль | Возможности |
|------|------------|
| `employee` | Свои экзамены, свои статусы, смена пароля/email |
| `admin` | Всё то же + просмотр всех сотрудников, CSV-выгрузка, ручной запуск уведомлений, полный CRUD пользователей/экзаменов/статусов/типов экзаменов (`/admin/*`), push-рассылка (`/notifications/broadcast`) |

---

## Карта директорий

```
C:\edu\appUAISS\
├── test.py                  # Весь бэкенд (FastAPI) — имя модуля жёстко зашито
│                             #   в Dockerfile (COPY test.py, CMD uvicorn test:app)
├── new_uaiss.html            # SPA: весь UI + JS-логика, отдаётся бэкендом на "/" и "/maxapp/"
├── www/
│   └── index.html            # Копия new_uaiss.html с абсолютным API_BASE — источник
│                              #   для Capacitor-сборки Android (webDir: www); держать в синхроне
├── android/                 # Android-проект (Capacitor native shell)
│   ├── app/
│   │   ├── src/main/
│   │   │   └── AndroidManifest.xml
│   │   ├── google-services.json   # Firebase конфиг (проект uaiss-4862a)
│   │   └── build.gradle
│   └── variables.gradle    # minSdk:24, compileSdk:36
├── config.json              # Конфиг бэкенда (создаётся автоматически, НЕ в git — секреты)
├── exams.db                 # SQLite БД (production, НЕ в git)
├── serviceAccountKey.json   # Приватный ключ Firebase (НЕ в git), нужен для FCM push
├── capacitor.config.json    # Конфиг Capacitor
├── package.json             # Node-зависимости (Capacitor)
├── quiz_bot.py               # Исходный пример MAX-бота (не используется в проде, справочно)
├── Dockerfile                # Образ бэкенда: python:3.11-slim + ntpdate, COPY test.py + new_uaiss.html
├── docker-compose.yml        # Сервис "web" (container_name uaiss_web_app), volume для
│                              #   exams.db/config.json/serviceAccountKey.json, cap_add SYS_TIME
├── config.example.json       # Шаблон config.json без реальных секретов
└── docs/                    # Эта документация
```

---

## Продакшен

- Бэкенд развёрнут по адресу: `https://bot.codle.ru` (контейнер слушает `:8000` изнутри, TLS/домен — через внешний реверс-прокси)
- Боевой фронтенд (`new_uaiss.html`) ходит на API по относительному пути `/api/v1` — тот же домен, с которого отдана страница
- Деплой: `Dockerfile` + `docker-compose.yml` (см. `docs/SETUP.md`, раздел «Docker»); контейнер называется `uaiss_web_app`, сервис в compose — `web`
- CI/CD **не обнаружено** — сборка и запуск образа ручные (`docker compose up -d --build`)
- Сервер синхронизирует время по NTP при каждом старте контейнера (`ntpdate -u pool.ntp.org`, нужен `cap_add: SYS_TIME`) — критично для корректного срабатывания планировщика уведомлений
