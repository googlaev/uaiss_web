# UAISS — Мобильное приложение

**Тип:** Hybrid App (Capacitor 8.4.1 + Vanilla JS SPA)  
**Платформа:** Android (min API 24 / Android 7.0)  
**App ID:** `ru.uaiss.mobile`  
**Основной файл:** `www/index.html` (~132 КБ, весь UI и логика в одном файле)

---

## Архитектурный подход

Приложение — **Single Page Application** без фреймворка. Весь JavaScript написан вручную в `<script>` теге `index.html`. Рендеринг — через `innerHTML` центрального `render()`. Никаких React/Vue/Angular.

```
www/index.html
├── <style>        CSS-переменные, dark/light темы, компоненты
├── <div id="app"> Корневой элемент для рендеринга
└── <script>       Вся бизнес-логика и UI (единый блок)
    ├── Конфигурация (SERVER_URL, API_BASE)
    ├── Состояние (let-переменные)
    ├── apiRequest() — fetch-обёртка с JWT
    ├── Функции работы с данными (login, loadAllData, addExam, ...)
    ├── render() — главная функция рендеринга
    ├── Обработчики событий (window.* функции)
    ├── initPushNotifications()
    ├── initLocalNotifications()
    └── Инициализация приложения
```

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

**Точка входа** (строка 230 `www/index.html`):
```javascript
const SERVER_URL = 'https://bot.codle.ru';
const API_BASE = SERVER_URL + '/api/v1';
```

Для локальной разработки эту строку нужно поменять. Варианты:

```javascript
// Эмулятор Android
const SERVER_URL = 'http://10.0.2.2:8000';

// Реальное устройство по USB (нужен adb reverse tcp:8000 tcp:8000)
const SERVER_URL = 'http://localhost:8000';

// Реальное устройство по WiFi
const SERVER_URL = 'http://192.168.x.x:8000';
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

Инициализируется через `@capacitor/push-notifications`:
1. Запрашивает разрешение у пользователя
2. Получает FCM-токен
3. Отправляет токен на бэкенд `POST /api/v1/fcm-token` (если эндпоинт активирован)
4. Слушает входящие push-события (открытие нужного экрана через `data.view`)

### Local Notifications

Через `@capacitor/local-notifications`:
- Инициализирует Android-канал `uaiss_exams` при старте
- Позволяет планировать уведомления на устройстве (работает без сети)
- Тест: уведомление через 30 секунд при нажатии кнопки

### MAX (мессенджер)

Веб-интерфейс (`www/index.html`, тот же код что и в APK) добавляет привязку MAX-аккаунта прямо в модалке профиля («👤 Личный кабинет» → карточка «💬 Уведомления в MAX»):

- `MaxLinkSection()` — рендерит состояние: не настроено на сервере / не привязано / показан код / привязано
- `window.loadMaxStatus()` — `GET /api/v1/max/status`, вызывается при открытии профиля
- `window.generateMaxLinkCode()` — `POST /api/v1/max/link-code`, показывает код и инструкцию отправить боту `/link КОД`
- `window.unlinkMax()` — `DELETE /api/v1/max/link`

Фактическую доставку уведомлений и обработку `/link КОД`/`/фио` делает фоновый поток внутри бэкенда (см. `docs/BACKEND.md`) — в мобильном приложении отдельного кода для MAX нет, всё идёт через тот же REST API, что и остальной функционал.

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
# 1. Обновить www/index.html (SERVER_URL на нужный адрес)
# 2. Синхронизировать веб-ресурсы с Android-проектом
npx cap sync

# 3. Открыть Android Studio
npx cap open android

# 4. В Android Studio: Build → Generate Signed APK / AAB
```

Результат сборки: `android/app/build/outputs/apk/` или `android/app/build/outputs/bundle/`
