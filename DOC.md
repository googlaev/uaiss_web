# Документация UAISS Web
#технологический стек 
Frontend - HTML5/CSS3/JavaScript
Backend - FastAPI (Python)
Database  - SQLite3
Аутентификация - JWT
Контейнеризация - Docker

#структура проекта 
uaiss_web/
│
├── test.py # Backend сервер (основной файл)
├── new_uaiss.html # Frontend интерфейс (SPA)
├── Dockerfile # Инструкция сборки Docker образа
├── docker-compose.yml # Оркестрация контейнеров
├── requirements.txt # Python зависимости
├── README.md # Пользовательская документация
└── DOC.md # Документация разработчика

#backend 

Главный серверный файл. Содержит:
- FastAPI приложение
- Все API эндпоинты
- Работу с базой данных
- JWT аутентификацию

основные функции


 `check_and_fix_database()` - Проверка и создание БД 
 `hash_password()` - Хэширование пароля (SHA256) 
 `create_token()` - Генерация JWT токена 
 `verify_token()` - Проверка JWT токена 
 `get_current_user()` - Получение текущего пользователя 
 `get_db()` - Подключение к SQLite 

api эндпоинты

Аутентификация

 POST - `/api/v1/auth/login` - Вход в систему
 GET - `/api/v1/auth/me` - Данные пользователя 
 POST - `/api/v1/auth/logout` - Выход 

 Экзамены

 GET -`/api/v1/exams/my`- Мои экзамены 
 POST - `/api/v1/exams` - Добавить экзамен 
 DELETE - `/api/v1/exams/{id}` - Удалить экзамен 
 GET - `/api/v1/exam-types` - Типы экзаменов 
 GET - `/api/v1/exams/expiring` - Истекающие экзамены 

Статусы

 GET - `/api/v1/status/my` - Мои статусы 
 POST - `/api/v1/status` - Добавить статус 
 PATCH - `/api/v1/status/{id}/close` - Закрыть больничный 
 DELETE - `/api/v1/status/last` - Удалить последний статус 
 GET - `/api/v1/status/month` - Статусы за месяц 
 GET - `/api/v1/status/current` - Текущая статистика 

#База данных

#редактирована Таблица `users`
```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    login TEXT UNIQUE,
    password_hash TEXT,
    role TEXT DEFAULT 'employee'
);

#frontend
Компоненты
LoginScreen() - Экран авторизации
HomeView() - Главный экран с дашбордом
MyExamsView() - Список экзаменов
AddExamView() - Добавление экзамена
StatusView() - 	Управление статусом
ManagementView() -	Админ панель
renderModal() -	Модальные окна

Функции API
login() -	POST /auth/login
loadAllData() -	Загрузка всех данных
addExam() -	POST /exams
addStatus() -	POST /status
deleteLastStatus() -	DELETE /status/last
closeSickLeave() -	PATCH /status/{id}/close
logout() -	Выход из системы

Состояния  (Store)
isAuthenticated -	Флаг авторизации
currentUser -	Данные пользователя
authToken -	JWT токен
currentView -	Текущий экран
myExams -	Список экзаменов
myStatuses -	Список статусов
examTypes -	Типы экзаменов
statusStats -	Статистика
isDarkMode -	Тема (светлая/темная)

Dockerfile - шаблон контейнера
dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY test.py .
COPY new_uaiss.html uaiss.html
EXPOSE 8000
CMD ["uvicorn", "test:app", "--host", "0.0.0.0", "--port", "8000"]

docker-compose.yml - упрощает управление Docker контейнером
yaml
services:
  web:
    build: .
    container_name: uaiss_web_app
    ports:
      - "8000:8000"
    volumes:
      - ./exams.db:/app/exams.db
    restart: unless-stopped

requirements.txt - список питон библиотек
text
fastapi==0.104.1
uvicorn==0.24.0
pyjwt==2.8.0
python-multipart==0.0.6

#логика работы

Аутентификация
Пользователь → ввод логина/пароля → POST /auth/login
→ сервер проверяет БД → создает JWT (8 часов)
→ токен в localStorage → заголовок Authorization: Bearer <token>

Добавление экзамена
Выбор типа экзамена → выбор даты → POST /exams
→ сервер рассчитывает срок действия
→ сохраняет в БД → обновляет список

Расчет статуса экзамена
python:
days_left = (end_date - today).days
if days_left < 0: status = "Просрочен"
elif days_left <= 30: status = "Истекает"
else: status = "Действующий"

Управление статусом
Выбор статуса → указание дат → POST /status
→ сохранение в БД → отображение в истории
→ больничный можно закрыть PATCH /status/{id}/close

Тестовые данные

Сотрудник-user@uaiss.ru, пароль:123456
Администратор-admin@uaiss.ru, пароль:admin123