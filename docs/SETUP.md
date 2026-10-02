# UAISS — Локальный запуск

## Требования

| Инструмент | Минимальная версия |
|-----------|-------------------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| Android Studio | Hedgehog (2023.1) или новее |
| Android SDK | API 24–36 |
| Java (JDK) | 17+ |

---

## 1. Клонирование / распаковка

```
C:\edu\appUAISS\     ← рабочая директория проекта
```

---

## 2. Запуск бэкенда

### Установка зависимостей

```bash
pip install fastapi uvicorn pydantic PyJWT python-multipart apscheduler requests
```

**Полный список (если нужен `requirements.txt`):**
```
fastapi
uvicorn[standard]
pydantic
PyJWT
python-multipart
apscheduler
requests
```

> Firebase push-уведомления опциональны. Для их включения также: `pip install firebase-admin`
> `requests` нужен для MAX-уведомлений (`send_max_message` и встроенный приём входящих сообщений бота).

### Запуск

```bash
cd C:\edu\appUAISS
python test_py_original.py
```

**При первом запуске произойдёт:**
1. Создание `config.json` с настройками по умолчанию
2. Создание `exams.db` со всеми таблицами
3. Добавление тестовых пользователей (если не существуют)
4. Запуск планировщика уведомлений (APScheduler)
5. Старт сервера на `http://0.0.0.0:8000`

**Вывод в консоли:**
```
🚀 Инициализация UAISS Web API...
📅 Планировщик уведомлений ЗАПУЩЕН!
✅ База данных готова к работе!

🔑 Тестовые учетные записи:
   Сотрудник:     коваленко / 123456
   Сотрудник:     смирнов   / 123456
   Администратор: морозова  / admin123

UAISS Web API Сервер запущен!
http://localhost:8000
Документация: http://localhost:8000/docs
```

### Проверка

- API: [http://localhost:8000/docs](http://localhost:8000/docs) — Swagger UI с интерактивными эндпоинтами
- Тестовый вход: `POST /api/v1/auth/login` с `{"login":"морозова","password":"admin123"}`

### Настройка email

Отредактировать `config.json`:

```json
"smtp": {
  "host": "smtp.gmail.com",
  "port": 587,
  "user": "your-email@gmail.com",
  "password": "your-app-password",
  "use_tls": true
}
```

> Для Gmail: создайте App Password в настройках безопасности Google-аккаунта (двухфакторная аутентификация должна быть включена).

### Настройка MAX-уведомлений

1. Получите токен бота в MAX (botapi.max.ru) — так же, как в `quiz_bot.py`
2. Отредактировать `config.json`:

```json
"max": {
  "enabled": true,
  "token": "<токен бота>",
  "api_url": "https://botapi.max.ru",
  "bot_username": "@ваш_бот",
  "link_code_ttl_minutes": 15,
  "allow_name_link": true
}
```

3. Перезапустить бэкенд (`python test_py_original.py`) — приём входящих сообщений бота (`/link`, `/фио`) запускается автоматически в фоновом потоке того же процесса, отдельно ничего запускать не нужно.

4. Привязать аккаунт — три способа:
   - **Мини-приложение MAX**: открыть мини-апп и один раз войти по логину/паролю — привязка происходит сама (см. шаг 5)
   - **По коду**: приложение/веб → профиль → «💬 Уведомления в MAX» → «Привязать MAX» → получить код → отправить боту `/link КОД`
   - **По ФИО** (без захода в приложение): сразу написать боту `/фио Гуляев Иван Павлович`, `/фио Гуляев И.П.` или коротко `/фио ГИП` (слитные инициалы). Отключается флагом `max.allow_name_link: false`, если такой способ нежелателен (см. `docs/BACKEND.md`).

### Регистрация мини-приложения MAX

Бэкенд уже отдаёт мини-апп по адресу `<ваш-домен>/maxapp/` (статика из `www/index.html` — та же SPA, что и в APK; монтируется автоматически при старте, если папка `www/` существует рядом с `test_py_original.py`). Чтобы его увидели в MAX:

1. Откройте `business.max.ru/self` (или мини-апп «MAX для бизнеса») → **Чат-боты** → выберите вашего бота
2. **⋮** → **Настройки** → вставьте URL: `https://<ваш-домен>/maxapp/` (обязательно HTTPS, без localhost)
3. Выберите тип кнопки («Открыть» и т.п.) → **Сохранить**

Требования к URL: HTTPS, только латиница/цифры/точки/дефисы, не длиннее 1024 символов — см. `dev.max.ru/docs/webapps/introduction`.

---

## 3. Запуск веб-интерфейса в браузере

Открыть `www/index.html` напрямую **не получится** — нужен веб-сервер из-за fetch-запросов.

**Вариант A:** FastAPI отдаёт статику сам (если положить `index.html` рядом с `test_py_original.py`):
```bash
# Сейчас GET / возвращает new_uaiss.html (если существует)
# Переименуйте www/index.html → new_uaiss.html в корне проекта, тогда:
# http://localhost:8000/ откроет приложение
```

**Вариант B:** Простой HTTP-сервер:
```bash
cd C:\edu\appUAISS\www
python -m http.server 3000
# Открыть http://localhost:3000
```

**Перед этим** измените `SERVER_URL` в `www/index.html` (строка 230):
```javascript
const SERVER_URL = 'http://localhost:8000';
```

---

## 4. Запуск мобильного приложения (Android)

### Установка Node-зависимостей

```bash
cd C:\edu\appUAISS
npm install
```

### Настройка SERVER_URL для устройства

В `www/index.html` строка 230 — выберите нужный адрес:

```javascript
// Эмулятор Android Studio
const SERVER_URL = 'http://10.0.2.2:8000';

// Реальное устройство по USB (требует adb reverse)
// В терминале: adb reverse tcp:8000 tcp:8000
const SERVER_URL = 'http://localhost:8000';

// Реальное устройство по WiFi
const SERVER_URL = 'http://192.168.X.X:8000';  // IP вашего ПК в сети
```

### Синхронизация и запуск

```bash
# Синхронизировать www/ → android/app/src/main/assets/
npx cap sync

# Открыть Android Studio
npx cap open android
```

В Android Studio:
1. Дождаться синхронизации Gradle
2. Выбрать устройство / эмулятор (API 24+)
3. Нажать Run (▶)

### Сборка подписанного APK (для установки без Android Studio)

В Android Studio: **Build → Generate Signed Bundle/APK → APK**  
Результат: `android/app/build/outputs/apk/release/app-release.apk`

---

## 5. Запуск бэкенда в Docker

Альтернатива шагам 2 (Python) — собрать и запустить бэкенд в контейнере. Веб-интерфейс (шаг 3) и Android (шаг 4) при этом запускаются как обычно, просто указывая `SERVER_URL` на адрес контейнера.

### Файлы

- `Dockerfile` — образ на `python:3.12-slim`, ставит `requirements.txt`, копирует `test_py_original.py` и `www/` (нужна для мини-приложения MAX, отдаётся по `/maxapp/`)
- `docker-compose.yml` — сборка + запуск, порт `8000:8000`, монтирует `config.json` и `exams.db` с хоста внутрь контейнера (чтобы секреты и данные не попадали в образ и не терялись при пересборке)
- `config.example.json` — шаблон конфигурации без реальных секретов

### Первый запуск

```bash
# 1. Подготовить config.json (если ещё не создан локальным запуском python test_py_original.py)
cp config.example.json config.json     # Linux/macOS
copy config.example.json config.json   # Windows PowerShell/cmd

# 2. Создать пустой exams.db (sqlite сам инициализирует пустой файл как новую БД)
touch exams.db                          # Linux/macOS
New-Item -ItemType File exams.db        # Windows PowerShell

# 3. Отредактировать config.json: SMTP, при желании max.enabled/max.token (см. раздел 2 выше)

# 4. Собрать и запустить
docker compose up -d --build
```

> Оба файла (`config.json`, `exams.db`) должны существовать на хосте **до** первого `docker compose up` — Docker создаёт директорию вместо файла для отсутствующего bind-mount источника, что ломает и JSON-конфиг, и sqlite.

### Проверка и управление

```bash
docker compose logs -f          # логи (эмодзи корректно выводятся, в отличие от cp1251-консоли Windows)
docker compose ps               # статус, включая healthcheck (GET /docs)
curl http://localhost:8000/docs # Swagger UI
docker compose restart          # перечитать config.json после правки (грузится один раз при старте процесса)
docker compose down             # остановить и удалить контейнер (volume-файлы на хосте остаются)
```

MAX-бот (`/link`, `/фио`) стартует внутри контейнера автоматически вместе с бэкендом — как и при обычном запуске, отдельно ничего поднимать не нужно.

### Если порт 8000 уже занят другим контейнером

`docker ps -a` покажет, что его держит. Остановите конфликтующий контейнер (`docker stop <имя>`) или поменяйте маппинг порта в `docker-compose.yml` (`"8001:8000"`).

---

## 6. Тестовые учётные записи

| Логин | Пароль | Роль |
|-------|--------|------|
| коваленко | 123456 | employee |
| смирнов | 123456 | employee |
| морозова | admin123 | admin |

---

## 7. Полезные команды

```bash
# Пересоздать БД с нуля (удалить и перезапустить)
del exams.db && python test_py_original.py

# Проверить текущие записи в БД
sqlite3 exams.db "SELECT * FROM users;"
sqlite3 exams.db "SELECT * FROM exam_types;"

# Посмотреть логи планировщика (вывод в консоль при запуске сервера)
# (APScheduler пишет в stdout)

# Синхронизировать www → android без открытия Studio
npx cap sync android

# Запустить на подключённом устройстве (если одно)
npx cap run android
```

---

## 8. Возможные проблемы

| Проблема | Решение |
|----------|---------|
| `ModuleNotFoundError: No module named 'apscheduler'` | `pip install apscheduler` |
| `Port 8000 already in use` | Найти процесс: `netstat -ano \| findstr :8000`, завершить через Task Manager |
| Приложение не достучивается до бэкенда | Проверить `SERVER_URL` в `index.html:230`, firewall, `adb reverse` |
| Gradle sync fails в Android Studio | File → Invalidate Caches, затем синхронизировать |
| Email не отправляется | Проверить SMTP-настройки в `config.json`, App Password для Gmail |
| `exams.db` занят другим процессом | Завершить предыдущий экземпляр бэкенда |
| MAX-уведомления не приходят | Проверить `max.enabled`/`max.token` в `config.json`, что в логе бэкенда есть строка «MAX-бот: приём входящих сообщений запущен», и что пользователь привязал аккаунт (`/max/status` → `linked: true`) |
| Код привязки MAX не принимается | Код истёк (по умолчанию 15 мин) — сгенерировать новый в приложении и отправить боту заново |
| `docker compose up` падает на `no such table: users` | `config.json`/`exams.db` не существовали на хосте до первого запуска — Docker подставил директорию вместо файла. Удалите созданные директории, создайте файлы правильно (см. раздел 5) и запустите заново |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | Порт занят другим контейнером — `docker ps -a`, затем `docker stop <имя>` или смените порт в `docker-compose.yml` |
