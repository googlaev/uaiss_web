# UAISS — Мобильное приложение

**Тип:** Hybrid App (Capacitor 8.4.1 + Vanilla JS SPA)
**Платформа:** Android (min API 24 / Android 7.0)
**App ID:** `ru.uaiss.mobile`
**Основной файл:** `new_uaiss.html` (~140 КБ, весь UI и логика в одном файле) — для сборки Android APK используется его копия `www/index.html` (см. `docs/ARCHITECTURE.md`, карта директорий)

---

## Архитектурный подход

Приложение — **Single Page Application** без фреймворка. Весь JavaScript написан вручную в `<script>` теге `index.html`. Рендеринг — через `innerHTML` центрального `render()`. Никаких React/Vue/Angular.

```
new_uaiss.html / www/index.html
├── <style>        CSS-переменные, dark/light темы, компоненты
├── <div id="root"> Корневой элемент для рендеринга
└── <script>       Вся бизнес-логика и UI (единый блок)
    ├── Конфигурация (API_BASE — относительный в new_uaiss.html, абсолютный в www/index.html)
    ├── Состояние (let-переменные)
    ├── apiRequest() — fetch-обёртка с JWT
    ├── Функции работы с данными (login, loadAllData, addExam, ...)
    ├── render() — главная функция рендеринга
    ├── Обработчики событий (window.* функции)
    ├── tryMaxWebAppAutoLogin() — автовход при открытии внутри мини-аппа MAX
    └── Инициализация приложения (initApp())
```

> В реальном фронтенде нет функций `initPushNotifications()`/`initLocalNotifications()` — FCM-токен устройства на сервер (`POST /fcm-token`) пока не отправляется из `new_uaiss.html`/`www/index.html`; это открытый пробел, не решённый в рамках текущей версии (см. `docs/TODO.md`).

---

## Глобальное состояние (JS-переменные)

```javascript
let isAuthenticated = false;
let currentUser = null;       // { user_id, full_name, role, email }
let currentView = 'home';     // 'home' | 'exams' | 'add-exam' | 'status' | 'management'
let exams = [];               // массив экзаменов пользователя
let statuses = [];            // история статусов пользователя
let currentStats = null;      // статистика всех сотрудников (admin)
let examTypes = [];           // справочник типов экзаменов
let selectedExamType = null;  // выбранный тип при добавлении
let modalType = null;         // открытое модальное окно
let examMenuOpen = false;     // состояние меню экзамена
let notifDrawerOpen = false;  // открыт ли дравер уведомлений
let statusFilter = null;      // фильтр на экране управления
let theme = 'light';          // 'light' | 'dark'
```

Состояние **не персистируется** между сессиями (кроме `authToken` в localStorage).

---

## Экраны (Views)

| View | Описание | Доступ |
|------|----------|--------|
| `home` | Дашборд: сводная статистика, ближайшие истекающие экзамены | employee, admin |
| `exams` | Список своих экзаменов с сортировкой и фильтрацией | employee, admin |
| `add-exam` | Выбор типа экзамена + дата сдачи | employee, admin |
| `status` | Текущий статус + история, кнопки смены | employee, admin |
| `management` | Обзор всех сотрудников (статусы + истекающие экзамены) | admin only |

**Навигация** — нижний tab-bar с иконками. Переход: `currentView = 'view'; render();`

**Дополнительно:**
- Модальное окно профиля (правый верхний угол) — смена пароля, email, тема
- Дравер уведомлений (иконка колокольчика) — журнал/лог нотификаций
- Контекстное меню экзамена — продлить, изменить дату, удалить

---

## Ключевые JS-функции

```javascript
// www/index.html

// API
apiRequest(endpoint, options)   // fetch + Bearer JWT, обрабатывает 401

// Аутентификация
login(loginValue, passwordValue) // POST /auth/login, сохраняет token + user в state

// Загрузка данных
loadAllData()                    // параллельный fetch: /exams/my + /status/my + /status/current + /exam-types

// Экзамены
addExam(examTypeId, date)        // проверка дубля → POST /exams
extendExam(examId, date)         // PUT /exams/{id}/extend
deleteExam(examId)               // DELETE /exams/{id}

// Статусы
addStatus(statusType, start, end) // проверка пересечения → POST /status
closeStatus(statusId, endDate)    // PATCH /status/{id}/close
extendStatus(statusId, endDate)   // PATCH /status/{id}/extend
deleteStatus(statusId)            // DELETE /status/{id}

// Рендеринг
render()                          // перерисовывает app#app на основе currentView и state

// Уведомления
initPushNotifications()           // регистрирует FCM-токен, слушает push-события
initLocalNotifications()          // инициализирует Android-канал уведомлений
```

---

## Работа с API

**Точка входа** (`www/index.html`, используется только Android-сборкой):
```javascript
const API_BASE = 'https://ВАШ-ДОМЕН/api/v1';
```

Capacitor-приложение грузит бандл локально (не с бэкенда), поэтому, в отличие от `new_uaiss.html` (который FastAPI отдаёт с того же домена — там путь относительный), здесь нужен абсолютный адрес. Перед сборкой APK замените на актуальный:

```javascript
// Эмулятор Android
const API_BASE = 'http://10.0.2.2:8000/api/v1';

// Реальное устройство по USB (нужен adb reverse tcp:8000 tcp:8000)
const API_BASE = 'http://localhost:8000/api/v1';

// Реальное устройство по WiFi
const API_BASE = 'http://192.168.x.x:8000/api/v1';

// Прод
const API_BASE = 'https://bot.codle.ru/api/v1';
```

**Заголовки каждого запроса:**
```javascript
headers: {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${localStorage.getItem('authToken')}`
}
```

---

## Уведомления

### FCM (облачные push)

Бэкенд полностью реализует отправку (`firebase_admin`, см. `docs/BACKEND.md`), но в текущей версии `new_uaiss.html`/`www/index.html` **нет** кода, который запрашивает разрешение, получает FCM-токен устройства и шлёт его на `POST /api/v1/fcm-token` — этот клиентский кусок не реализован (пробел, см. `docs/TODO.md`). Раньше это планировалось через `@capacitor/push-notifications`, но в репозитории этот путь не подключён.

### Local Notifications

`@capacitor/local-notifications` указан в `package.json` как зависимость, но, как и с push, вызывающего JS-кода в `new_uaiss.html`/`www/index.html` сейчас нет — планировалось, не подключено.

### MAX (мессенджер)

Способ привязки аккаунта из мобильного приложения — тот же, что и в мини-аппе: один раз войти по логину/паролю, пока приложение открыто внутри MAX (см. `docs/BACKEND.md`, раздел «MAX-уведомления и мини-приложение»). Отдельной UI-карточки «Привязать MAX» (с кнопкой получения кода `/max/link-code`, статусом `/max/status`, отвязкой `/max/link`) в текущем `new_uaiss.html` нет, хотя сами эти эндпоинты на бэкенде есть — это открытый пробел для тех, кто хочет привязаться без входа в мини-апп (например, через `/link КОД` или `/фио` боту напрямую, без визуального помощника в приложении).

---

## Capacitor-конфигурация

**`capacitor.config.json`:**
```json
{
  "appId": "ru.uaiss.mobile",
  "appName": "UAISS",
  "webDir": "www",
  "server": {
    "androidScheme": "https",
    "cleartext": true
  },
  "android": {
    "allowMixedContent": true
  },
  "plugins": {
    "SplashScreen": {
      "launchShowDuration": 1500,
      "backgroundColor": "#1A56DB",
      "showSpinner": false
    }
  }
}
```

> `cleartext: true` и `allowMixedContent: true` разрешают HTTP (нужно для локальной разработки). В продакшене достаточно HTTPS.

---

## Android-конфигурация

**`android/variables.gradle`:**
```gradle
minSdkVersion = 24       // Android 7.0+
compileSdkVersion = 36   // Android 15
targetSdkVersion = 36
```

**Permissions (`android/app/src/main/AndroidManifest.xml`):**
```xml
INTERNET
POST_NOTIFICATIONS          <!-- Android 13+ -->
RECEIVE_BOOT_COMPLETED
VIBRATE
SCHEDULE_EXACT_ALARM
USE_EXACT_ALARM
REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
```

**Firebase:**
- Конфиг: `android/app/google-services.json`
- Firebase-проект: `uaiss-4862a`
- Используется для FCM push-уведомлений (опционально)

---

## UI/UX

- **Dark/Light тема** — CSS-переменные, переключается кнопкой в профиле, сохраняется в localStorage
- **Адаптивность** — max-width: 500px, mobile-first дизайн
- **Safe area insets** — поддержка вырезов/навигационных жестов Android
- **Анимации** — fadeIn, slideUp, slideInRight через CSS-классы
- **Цветовые статусы экзаменов:**
  - Зелёный — действующий (>30 дней)
  - Оранжевый — истекает (1–30 дней)
  - Красный — просрочен

---

## Сборка APK

```bash
# 1. Обновить www/index.html (API_BASE на нужный адрес)
# 2. Синхронизировать веб-ресурсы с Android-проектом
npx cap sync

# 3. Открыть Android Studio
npx cap open android

# 4. В Android Studio: Build → Generate Signed APK / AAB
```

Результат сборки: `android/app/build/outputs/apk/` или `android/app/build/outputs/bundle/`
