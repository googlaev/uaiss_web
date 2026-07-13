from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime, timedelta, date, timezone
from calendar import monthrange
import hashlib
import jwt
import secrets
import os
import csv
from io import StringIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
import json
import time
import firebase_admin
from firebase_admin import credentials, messaging

# Загрузка конфигурации
def load_config():
    """Загрузка конфигурации из файла config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    default_config = {
        "smtp": {
            "host": "smtp.gmail.com",
            "port": 587,
            "user": "uaiss.gpn@gmail.com",
            "password": "ywtpwwulycpalogd",
            "use_tls": True
        },
        "notifications": {
            "enabled": True,
            "send_time_hour": 9,
            "send_time_minute": 0,
            "notify_days": [30, 7, 3, 2, 1],
            "notify_expired": True
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "reload": False
        },
        "database": {
            "path": "exams.db"
        },
        "auth": {
            "token_expire_hours": 8,
            "jwt_secret_key": secrets.token_hex(32)
        },
        "app": {
            "name": "UAISS Web API",
            "version": "1.0.0"
        }
    }
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            for key in default_config:
                if key not in config:
                    config[key] = default_config[key]
            return config
    else:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        print(f"✅ Создан файл конфигурации: {config_path}")
        return default_config

# Загружаем конфигурацию
CONFIG = load_config()

app = FastAPI(title=CONFIG['app']['name'], version=CONFIG['app']['version'])

try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK инициализирован")
except Exception as e:
    print(f"⚠️ Firebase не инициализирован: {e}")

# Создаём таблицу fcm_tokens при загрузке модуля — до любых роутеров
try:
    _conn = sqlite3.connect(CONFIG['database']['path'])
    _conn.execute("""
        CREATE TABLE IF NOT EXISTS fcm_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            token      TEXT NOT NULL UNIQUE,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    _conn.commit()
    _conn.close()
    print("✅ Таблица fcm_tokens готова")
except Exception as _e:
    print(f"❌ Ошибка создания fcm_tokens: {_e}")

SECRET_KEY = CONFIG['auth'].get('jwt_secret_key', secrets.token_hex(32))
ALGORITHM = "HS256"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        check_and_fix_database()
    except Exception as e:
        print(f"⚠️ check_and_fix_database: {e}")
    try:
        conn = sqlite3.connect(CONFIG['database']['path'])
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fcm_tokens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                token      TEXT NOT NULL UNIQUE,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_at       TEXT DEFAULT (datetime('now', 'localtime')),
                type          TEXT NOT NULL,
                title         TEXT NOT NULL,
                body          TEXT NOT NULL,
                user_id       TEXT,
                user_name     TEXT,
                sent_by       TEXT DEFAULT 'system',
                sent_by_name  TEXT DEFAULT 'Система'
            )
        """)
        conn.commit()
        conn.close()
        print("✅ Таблицы fcm_tokens, notification_logs готовы")
    except Exception as e:
        print(f"❌ Ошибка создания таблиц: {e}")

security = HTTPBearer()

SMTP_HOST = CONFIG['smtp']['host']
SMTP_PORT = CONFIG['smtp']['port']
SMTP_USER = CONFIG['smtp']['user']
SMTP_PASSWORD = CONFIG['smtp']['password']
SMTP_USE_TLS = CONFIG['smtp'].get('use_tls', True)

NOTIFICATIONS_ENABLED = CONFIG['notifications']['enabled']
NOTIFY_DAYS = CONFIG['notifications']['notify_days']
NOTIFY_EXPIRED = CONFIG['notifications']['notify_expired']

class LoginRequest(BaseModel):
    login: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    full_name: str
    role: str
    email: Optional[str] = None

class ExamAdd(BaseModel):
    exam_type_id: int
    date: str

class StatusAdd(BaseModel):
    status: str
    start_date: str
    end_date: Optional[str] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class EmailUpdate(BaseModel):
    email: str

def check_and_fix_database():
    print("\n🔍 Проверка структуры базы данных...")
    conn = sqlite3.connect(CONFIG['database']['path'])
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("❌ Таблица users не найдена!")
        return False
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"📋 Существующие колонки: {columns}")
    
    if 'login' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN login TEXT")
        print("✅ Колонка login добавлена")
    if 'password_hash' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        print("✅ Колонка password_hash добавлена")
    if 'role' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'employee'")
        print("✅ Колонка role добавлена")
    if 'email' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
        print("✅ Колонка email добавлена")
    
    cursor.execute("PRAGMA table_info(exams)")
    exam_columns = [col[1] for col in cursor.fetchall()]
    if 'last_notification_day' not in exam_columns:
        cursor.execute("ALTER TABLE exams ADD COLUMN last_notification_day INTEGER DEFAULT 0")
        print("✅ Колонка last_notification_day добавлена")
    
    def hash_password(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'коваленко'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (full_name, login, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                       ("Коваленко Александр Викторович", "коваленко", hash_password("123456"), "employee", "kovalenko@example.com"))
        print("✅ Добавлен: коваленко / 123456")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'морозова'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (full_name, login, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                       ("Екатерина Морозова", "морозова", hash_password("admin123"), "admin", "morozova@example.com"))
        print("✅ Добавлен: морозова / admin123")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'смирнов'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (full_name, login, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                       ("Алексей Смирнов", "смирнов", hash_password("123456"), "employee", "smirnov@example.com"))
        print("✅ Добавлен: смирнов / 123456")
    
    conn.commit()
    conn.close()

    conn2 = sqlite3.connect(CONFIG['database']['path'])
    conn2.execute("""
        CREATE TABLE IF NOT EXISTS fcm_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            token      TEXT NOT NULL UNIQUE,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn2.commit()
    conn2.close()

    print("\n✅ База данных готова к работе!")
    print("\n🔑 Тестовые учетные записи:")
    print("   Сотрудник:   логин: коваленко / пароль: 123456")
    print("   Сотрудник:   логин: смирнов / пароль: 123456")
    print("   Администратор: логин: морозова / пароль: admin123")
    print()
    return True

def get_db():
    conn = sqlite3.connect(CONFIG['database']['path'])
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def create_token(user_id: int, role: str) -> str:
    expire_hours = CONFIG['auth'].get('token_expire_hours', 8)
    payload = {"sub": str(user_id), "role": role, "exp": datetime.utcnow() + timedelta(hours=expire_hours)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Неверный токен")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    return {"user_id": int(payload["sub"]), "role": payload["role"]}

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, '%d.%m.%Y')

def format_date(date: datetime) -> str:
    return date.strftime('%d.%m.%Y')

def is_status_active(start_date_str: str, end_date_str: Optional[str]) -> bool:
    try:
        today = datetime.now()
        start_date = datetime.strptime(start_date_str, '%d.%m.%Y')
        
        if start_date > today:
            return False
        
        if end_date_str is None or end_date_str == '':
            return True
        
        end_date = datetime.strptime(end_date_str, '%d.%m.%Y')
        return end_date >= today
    except:
        return False

def check_status_overlap(user_id: int, start_date: str, end_date: Optional[str] = None, exclude_status_id: Optional[int] = None) -> tuple:
    conn = get_db()
    try:
        new_start = parse_date(start_date)
        new_end = parse_date(end_date) if end_date else None
        
        if exclude_status_id:
            cursor = conn.execute(
                "SELECT id, status, start_date, end_date FROM user_status WHERE user_id = ? AND id != ?",
                (user_id, exclude_status_id)
            )
        else:
            cursor = conn.execute(
                "SELECT id, status, start_date, end_date FROM user_status WHERE user_id = ?",
                (user_id,)
            )
        
        statuses = cursor.fetchall()
        
        for status in statuses:
            status_start = parse_date(status['start_date'])
            status_end = parse_date(status['end_date']) if status['end_date'] else None
            
            status_text = status['status']
            status_text = status_text.replace('🤒', '').replace('✈️', '').replace('🏖️', '').replace('🟢', '').strip()
            
            if new_end is None and status_end is None:
                return (True, status_text)
            elif new_end is None:
                if new_start <= status_end:
                    return (True, status_text)
            elif status_end is None:
                if status_start <= new_end:
                    return (True, status_text)
            else:
                if not (new_end < status_start or new_start > status_end):
                    return (True, status_text)
        
        return (False, None)
    finally:
        conn.close()

def send_email(to_email: str, subject: str, body: str):
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"⚠️ SMTP не настроен. Письмо на {to_email} не отправлено.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            if SMTP_USE_TLS:
                server.starttls()
        
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email отправлен на {to_email}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки email на {to_email}: {e}")
        return False

def send_email_async(to_email: str, subject: str, body: str):
    thread = Thread(target=send_email, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()

def send_fcm_push(token: str, title: str, body: str, data: dict = None) -> bool:
    try:
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    channel_id="uaiss_exams",
                    sound="default"
                )
            )
        )
        messaging.send(msg)
        print(f"✅ FCM отправлен: {title}")
        return True
    except Exception as e:
        print(f"❌ FCM ошибка: {e}")
        return False

def _ensure_fcm_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fcm_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

def send_push_to_user(user_id: str, title: str, body: str, data: dict = None):
    conn = sqlite3.connect(CONFIG['database']['path'])
    try:
        _ensure_fcm_table(conn)
        rows = conn.execute(
            "SELECT token FROM fcm_tokens WHERE user_id = ?", (user_id,)
        ).fetchall()
    finally:
        conn.close()
    for (token,) in rows:
        send_fcm_push(token, title, body, data)

YEKATERINBURG = timezone(timedelta(hours=5))

def log_notification(type_: str, title: str, body: str,
                     user_id: str = None, user_name: str = None,
                     sent_by: str = 'system', sent_by_name: str = 'Система'):
    try:
        conn = sqlite3.connect(CONFIG['database']['path'])
        now_str = datetime.now(YEKATERINBURG).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """INSERT INTO notification_logs
               (type, title, body, user_id, user_name, sent_by, sent_by_name, sent_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (type_, title, body, user_id, user_name, sent_by, sent_by_name, now_str)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ log_notification error: {e}")

def check_and_send_notifications_sync():
    if not NOTIFICATIONS_ENABLED:
        print("ℹ️ Уведомления отключены в конфигурации")
        return 0
    
    print(f"\n🕐 Проверка экзаменов в {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    conn = sqlite3.connect(CONFIG['database']['path'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    today = datetime.now().date()
    notifications_sent = 0
    
    cursor.execute("""
        SELECT u.user_id, u.full_name, u.email, 
               e.id as exam_id, e.name as exam_name, 
               e.date as exam_date, e.duration,
               e.last_notification_day
        FROM users u
        JOIN exams e ON u.user_id = e.user_id
        WHERE u.email IS NOT NULL AND u.email != ''
    """)
    
    for row in cursor.fetchall():
        try:
            exam_date = datetime.strptime(row['exam_date'], '%d.%m.%Y').date()
            duration_months = int(row['duration'])
            
            year = exam_date.year + (exam_date.month + duration_months - 1) // 12
            month = (exam_date.month + duration_months - 1) % 12 + 1
            day = exam_date.day
            last_day = monthrange(year, month)[1]
            end_day = min(day, last_day)
            end_date = date(year, month, end_day)
            
            days_left = (end_date - today).days
            exam_id = row['exam_id']
            last_sent = row['last_notification_day'] or 0
            
            for nd in NOTIFY_DAYS:
                if days_left == nd and last_sent != nd:
                    subject = f"⚠️ Уведомление об экзамене - {row['full_name']}"
                    body = f"""
Здравствуйте, {row['full_name']}!

Ваш экзамен "{row['exam_name']}" истекает через {nd} дней!

• Дата окончания: {end_date.strftime('%d.%m.%Y')}
• Осталось дней: {days_left}

Пожалуйста, продлите экзамен в системе:
http://localhost:{CONFIG['server']['port']}

---
Это автоматическое уведомление.
"""
                    if send_email(row['email'], subject, body):
                        cursor.execute(
                            "UPDATE exams SET last_notification_day = ? WHERE id = ?",
                            (nd, exam_id)
                        )
                        conn.commit()
                        notifications_sent += 1
                        print(f"✅ Уведомление за {nd} дней отправлено для {row['exam_name']} -> {row['email']}")
                    push_title = f"⚠️ Экзамен истекает через {nd} дней"
                    push_body = f"{row['exam_name']} — до {end_date.strftime('%d.%m.%Y')}"
                    send_push_to_user(row['user_id'], push_title, push_body, {"view": "exams"})
                    log_notification('exam_expiry', push_title, push_body,
                                     user_id=row['user_id'], user_name=row['full_name'])
                    
            if NOTIFY_EXPIRED and days_left < 0 and last_sent != -1:
                subject = f"🔴 СРОЧНО! Экзамен просрочен - {row['full_name']}"
                body = f"""
Здравствуйте, {row['full_name']}!

ВАШ ЭКЗАМЕН ПРОСРОЧЕН!

• Экзамен: {row['exam_name']}
• Действовал до: {end_date.strftime('%d.%m.%Y')}
• Просрочен на: {abs(days_left)} дней

НЕОБХОДИМО СРОЧНО ПЕРЕСДАТЬ ЭКЗАМЕН!

Перейдите в систему: http://localhost:{CONFIG['server']['port']}

---
Это автоматическое уведомление.
"""
                if send_email(row['email'], subject, body):
                    cursor.execute(
                        "UPDATE exams SET last_notification_day = -1 WHERE id = ?",
                        (exam_id,)
                    )
                    conn.commit()
                    notifications_sent += 1
                expired_title = "🔴 Экзамен просрочен!"
                expired_body = f"{row['exam_name']} просрочен на {abs(days_left)} дней"
                send_push_to_user(row['user_id'], expired_title, expired_body, {"view": "exams"})
                log_notification('exam_expired', expired_title, expired_body,
                                 user_id=row['user_id'], user_name=row['full_name'])
                    
        except Exception as e:
            print(f"Ошибка обработки экзамена: {e}")
            continue
    
    conn.close()
    print(f"📊 Отправлено уведомлений: {notifications_sent}")
    return notifications_sent

@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(auth_data: LoginRequest):
    conn = get_db()
    try:
        cursor = conn.execute("SELECT user_id, full_name, login, email, password_hash, role FROM users WHERE login = ?",
                              (auth_data.login,))
        user = cursor.fetchone()
        if not user or not verify_password(auth_data.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        access_token = create_token(user['user_id'], user['role'])
        return LoginResponse(
            access_token=access_token,
            user_id=user['user_id'],
            full_name=user['full_name'],
            role=user['role'],
            email=user['email'] if user['email'] else None
        )
    finally:
        conn.close()

@app.post("/api/v1/auth/logout")
async def logout(current_user=Depends(get_current_user)):
    return {"message": "Успешный выход"}

@app.get("/api/v1/auth/me")
async def get_me(current_user=Depends(get_current_user)):
    conn = get_db()
    cursor = conn.execute("SELECT user_id, full_name, login, email, role FROM users WHERE user_id = ?",
                          (current_user["user_id"],))
    user = cursor.fetchone()
    conn.close()
    return dict(user)

@app.post("/api/v1/auth/change-password")
async def change_password(password_data: PasswordChange, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute("SELECT password_hash FROM users WHERE user_id = ?", (current_user["user_id"],))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        if not verify_password(password_data.old_password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Неверный старый пароль")
        if len(password_data.new_password) < 4:
            raise HTTPException(status_code=400, detail="Пароль должен быть не менее 4 символов")
        new_password_hash = hash_password(password_data.new_password)
        conn.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (new_password_hash, current_user["user_id"]))
        conn.commit()
        return {"message": "Пароль успешно изменен", "success": True}
    finally:
        conn.close()

@app.put("/api/v1/auth/update-email")
async def update_email(email_data: EmailUpdate, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute("SELECT user_id FROM users WHERE email = ? AND user_id != ?",
                              (email_data.email, current_user["user_id"]))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email уже используется")
        conn.execute("UPDATE users SET email = ? WHERE user_id = ?", (email_data.email, current_user["user_id"]))
        conn.commit()
        return {"message": "Email успешно обновлен", "success": True}
    finally:
        conn.close()

@app.post("/api/v1/fcm-token")
async def save_fcm_token(request: Request, current_user=Depends(get_current_user)):
    body = await request.json()
    token = body.get("token", "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
    conn = get_db()
    try:
        _ensure_fcm_table(conn)
        conn.execute(
            """INSERT INTO fcm_tokens (user_id, token, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(token) DO UPDATE SET
               user_id=excluded.user_id, updated_at=excluded.updated_at""",
            (current_user["user_id"], token)
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok"}

@app.post("/api/v1/notifications/test-push")
async def test_push_notification(current_user=Depends(get_current_user)):
    uid = current_user["user_id"]
    conn = get_db()
    row = conn.execute("SELECT full_name FROM users WHERE user_id = ?", (uid,)).fetchone()
    conn.close()
    uname = row['full_name'] if row else ''
    def _delayed():
        time.sleep(30)
        title = "🔔 Тест UAISS"
        body  = "FCM работает! Уведомления приходят при закрытом приложении."
        send_push_to_user(uid, title, body, {"view": "exams"})
        log_notification('test', title, body, user_id=uid, user_name=uname)
    thread = Thread(target=_delayed)
    thread.daemon = True
    thread.start()
    return {"status": "ok"}

@app.delete("/api/v1/notifications/log/{notif_id}")
async def delete_notification(notif_id: int, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        if current_user["role"] == "admin":
            conn.execute("DELETE FROM notification_logs WHERE id = ?", (notif_id,))
        else:
            conn.execute(
                "DELETE FROM notification_logs WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
                (notif_id, current_user["user_id"])
            )
        conn.commit()
        return {"status": "deleted"}
    finally:
        conn.close()

@app.post("/api/v1/notifications/send")
async def send_notifications_manual(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    thread = Thread(target=check_and_send_notifications_sync)
    thread.daemon = True
    thread.start()

    return {"message": "Уведомления начали отправляться в фоновом режиме"}

class BroadcastRequest(BaseModel):
    title: str = "UAISS"
    message: str

@app.post("/api/v1/notifications/broadcast")
async def broadcast_push(body: BroadcastRequest, current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Текст сообщения не может быть пустым")

    conn = get_db()
    try:
        _ensure_fcm_table(conn)
        rows = conn.execute("SELECT DISTINCT token FROM fcm_tokens").fetchall()
    finally:
        conn.close()

    tokens = [row[0] for row in rows]
    if not tokens:
        raise HTTPException(status_code=404, detail="Нет зарегистрированных устройств")

    admin_name = current_user.get("name", current_user.get("user_id", "Админ"))

    def _send_all():
        sent = 0
        for token in tokens:
            if send_fcm_push(token, body.title, body.message, {"view": "home"}):
                sent += 1
        print(f"✅ Broadcast: {sent}/{len(tokens)} устройств")

    thread = Thread(target=_send_all)
    thread.daemon = True
    thread.start()

    log_notification('broadcast', body.title, body.message,
                     user_id=None, user_name=None,
                     sent_by=current_user["user_id"], sent_by_name=admin_name)

    return {"sent": len(tokens), "message": f"Рассылка запущена для {len(tokens)} устройств"}

@app.get("/api/v1/notifications/log")
async def get_notification_log(current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        if current_user["role"] == "admin":
            rows = conn.execute(
                "SELECT * FROM notification_logs ORDER BY sent_at DESC LIMIT 300"
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM notification_logs
                   WHERE user_id = ? OR user_id IS NULL
                   ORDER BY sent_at DESC LIMIT 100""",
                (current_user["user_id"],)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.get("/api/v1/exams/report/csv")
async def export_exams_report(current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute("""
            SELECT 
                u.full_name,
                e.name as exam_name,
                e.date as exam_date,
                e.duration,
                et.duration as duration_months
            FROM users u
            LEFT JOIN exams e ON u.user_id = e.user_id
            LEFT JOIN exam_types et ON e.name = et.name
            WHERE e.name IS NOT NULL
            ORDER BY u.full_name, e.date DESC
        """)
        
        rows = cursor.fetchall()
        
        output = StringIO()
        output.write('\uFEFF')
        writer = csv.writer(output, delimiter=';')
        
        writer.writerow(['Фамилия', 'Тип экзамена', 'Дата сдачи', 'Действителен до'])
        
        for row in rows:
            try:
                exam_date = datetime.strptime(row['exam_date'], '%d.%m.%Y')
                duration_months = int(row['duration_months']) if row['duration_months'] else int(row['duration']) if row['duration'] else 0
                end_date = exam_date + timedelta(days=duration_months * 30)
                
                writer.writerow([
                    row['full_name'],
                    row['exam_name'],
                    row['exam_date'],
                    end_date.strftime('%d.%m.%Y')
                ])
            except Exception as e:
                print(f"Ошибка обработки: {e}")
                continue
        
        filename = f"exams_{datetime.now().strftime('%d_%m_%Y')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    finally:
        conn.close()

@app.get("/api/v1/exams/expiring")
async def get_expiring_exams(current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute("""
            SELECT u.full_name, e.user_id, e.name AS exam_name, e.date AS exam_date,
                   COALESCE(CAST(et.duration AS TEXT), e.duration) AS duration_months,
                   COALESCE(et.emoji, '📚') AS emoji
            FROM exams e
            JOIN users u ON e.user_id = u.user_id
            LEFT JOIN exam_types et ON e.name = et.name
            WHERE e.id IN (SELECT MAX(id) FROM exams GROUP BY user_id, name)
            ORDER BY e.date ASC
        """)
        rows = cursor.fetchall()
        today = datetime.now().date()
        cutoff = today + timedelta(days=30)
        result = []
        for row in rows:
            try:
                exam_date = datetime.strptime(row['exam_date'], '%d.%m.%Y').date()
                months = int(row['duration_months']) if row['duration_months'] else 12
                expires = exam_date + timedelta(days=months * 30)
                days_left = (expires - today).days
                if expires <= cutoff:
                    result.append({
                        'user_name': row['full_name'],
                        'user_id': row['user_id'],
                        'exam_name': row['exam_name'],
                        'exam_date': row['exam_date'],
                        'expires_at': expires.strftime('%d.%m.%Y'),
                        'days_left': days_left,
                        'emoji': row['emoji']
                    })
            except Exception:
                continue
        result.sort(key=lambda x: x['days_left'])
        return result
    finally:
        conn.close()

@app.get("/api/v1/exams/my")
async def get_my_exams(current_user=Depends(get_current_user)):
    conn = get_db()
    cursor = conn.execute("""
        SELECT e.id, e.name, e.date, e.duration, et.emoji, et.duration as duration_months
        FROM exams e LEFT JOIN exam_types et ON e.name = et.name
        WHERE e.user_id = ? ORDER BY e.date DESC
    """, (current_user["user_id"],))
    exams, today = [], datetime.now()
    for row in cursor:
        try:
            exam_date = datetime.strptime(row['date'], '%d.%m.%Y')
            duration_months = int(row['duration_months']) if row['duration_months'] else int(row['duration'])
            end_date = exam_date + timedelta(days=duration_months * 30)
            days_left = (end_date - today).days
            status = "Просрочен" if days_left < 0 else ("Истекает" if days_left <= 30 else "Действующий")
            exams.append({
                "id": row['id'], "type": row['name'], "emoji": row['emoji'] or "📚",
                "date": row['date'], "expires_at": end_date.strftime('%d.%m.%Y'),
                "days_left": days_left, "status": status
            })
        except Exception as e:
            continue
    conn.close()
    return exams

@app.post("/api/v1/exams")
async def add_exam(exam_data: ExamAdd, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute("SELECT name, duration FROM exam_types WHERE id = ?", (exam_data.exam_type_id,))
        exam_type = cursor.fetchone()
        if not exam_type:
            raise HTTPException(status_code=404, detail="Тип экзамена не найден")
        
        cursor = conn.execute(
            "SELECT id, date FROM exams WHERE user_id = ? AND name = ?",
            (current_user["user_id"], exam_type['name'])
        )
        existing_exam = cursor.fetchone()
        
        if existing_exam:
            raise HTTPException(
                status_code=409, 
                detail=f"Экзамен '{exam_type['name']}' уже существует. Используйте продление."
            )
        
        exam_date = datetime.strptime(exam_data.date, '%Y-%m-%d')
        if exam_date > datetime.now():
            raise HTTPException(status_code=400, detail="Нельзя выбрать дату из будущего")
        
        formatted_date = exam_date.strftime('%d.%m.%Y')
        
        conn.execute("""
            INSERT INTO exams (user_id, name, date, duration, notification_sent, month_notification_sent,
                              week_notification_sent, exam_day_notification_sent, end_day_notification_sent, last_notification_day)
            VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0, 0)
        """, (current_user["user_id"], exam_type['name'], formatted_date, str(exam_type['duration'])))
        
        conn.commit()
        return {"message": "Экзамен успешно добавлен", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/v1/exams/{exam_id}/extend")
async def extend_exam(exam_id: int, request: Request, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        data = await request.json()
        new_date_str = data.get('date')
        
        cursor = conn.execute(
            "SELECT user_id, name, date FROM exams WHERE id = ?",
            (exam_id,)
        )
        exam = cursor.fetchone()
        
        if not exam:
            raise HTTPException(status_code=404, detail="Экзамен не найден")
        
        if exam['user_id'] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        try:
            new_date = datetime.strptime(new_date_str, '%d.%m.%Y')
            if new_date > datetime.now():
                raise HTTPException(status_code=400, detail="Нельзя выбрать дату из будущего")
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        
        conn.execute(
            "UPDATE exams SET date = ? WHERE id = ?",
            (new_date_str, exam_id)
        )
        conn.commit()
        
        try:
            conn.execute(
                "UPDATE exams SET last_notification_day = 0 WHERE id = ?",
                (exam_id,)
            )
            conn.commit()
        except:
            pass
        
        return {"message": "Экзамен успешно продлен", "success": True}
    finally:
        conn.close()

@app.put("/api/v1/exams/{exam_id}")
async def update_exam_date(exam_id: int, request: Request, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        data = await request.json()
        new_date_str = data.get('date')
        
        cursor = conn.execute(
            "SELECT user_id FROM exams WHERE id = ?",
            (exam_id,)
        )
        exam = cursor.fetchone()
        
        if not exam:
            raise HTTPException(status_code=404, detail="Экзамен не найден")
        
        if exam['user_id'] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        try:
            new_date = datetime.strptime(new_date_str, '%d.%m.%Y')
            if new_date > datetime.now():
                raise HTTPException(status_code=400, detail="Нельзя выбрать дату из будущего")
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        
        conn.execute(
            "UPDATE exams SET date = ? WHERE id = ?",
            (new_date_str, exam_id)
        )
        conn.commit()
        
        return {"message": "Дата экзамена обновлена", "success": True}
    finally:
        conn.close()

@app.delete("/api/v1/exams/{exam_id}")
async def delete_exam(exam_id: int, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT user_id FROM exams WHERE id = ?",
            (exam_id,)
        )
        exam = cursor.fetchone()
        
        if not exam:
            raise HTTPException(status_code=404, detail="Экзамен не найден")
        
        if exam['user_id'] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        conn.commit()
        
        return {"message": "Экзамен удален", "success": True}
    finally:
        conn.close()

@app.get("/api/v1/exams/check-duplicate")
async def check_exam_duplicate(exam_type_id: int, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute("SELECT name, duration FROM exam_types WHERE id = ?", (exam_type_id,))
        exam_type = cursor.fetchone()
        if not exam_type:
            return {"exists": False}
        
        cursor = conn.execute(
            "SELECT id, date FROM exams WHERE user_id = ? AND name = ?",
            (current_user["user_id"], exam_type['name'])
        )
        existing = cursor.fetchone()
        
        if existing:
            return {
                "exists": True,
                "exam_id": existing['id'],
                "exam_date": existing['date']
            }
        return {"exists": False}
    finally:
        conn.close()

@app.get("/api/v1/exam-types")
async def get_exam_types():
    conn = get_db()
    cursor = conn.execute("SELECT id, name, duration, emoji FROM exam_types ORDER BY name")
    types = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return types

@app.get("/api/v1/status/my")
async def get_my_status(current_user=Depends(get_current_user)):
    conn = get_db()
    cursor = conn.execute("""
        SELECT id, status, start_date, end_date 
        FROM user_status 
        WHERE user_id = ? 
        ORDER BY start_date DESC
    """, (current_user["user_id"],))
    
    statuses = []
    
    for row in cursor:
        is_active = is_status_active(row['start_date'], row['end_date'])
        
        statuses.append({
            "id": row['id'],
            "status": row['status'],
            "start_date": row['start_date'],
            "end_date": row['end_date'] if row['end_date'] else None,
            "is_active": is_active
        })
    conn.close()
    return statuses

@app.post("/api/v1/status")
async def add_status(status_data: StatusAdd, current_user=Depends(get_current_user)):
    conn = get_db()
    
    has_overlap, overlapping_status = check_status_overlap(current_user["user_id"], status_data.start_date, status_data.end_date)
    
    if has_overlap:
        raise HTTPException(
            status_code=400, 
            detail=f"Пересечение с {overlapping_status}"
        )
    
    end_date = status_data.end_date if status_data.end_date else None
    
    conn.execute("""
        INSERT INTO user_status (user_id, status, start_date, end_date)
        VALUES (?, ?, ?, ?)
    """, (current_user["user_id"], status_data.status, status_data.start_date, end_date))
    
    conn.commit()
    conn.close()
    return {"message": "Статус успешно добавлен", "success": True}

@app.patch("/api/v1/status/{status_id}/close")
async def close_status(status_id: int, request: Request, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        data = await request.json() if request.headers.get("content-type") else {}
        today = datetime.now().strftime('%d.%m.%Y')
        end_date = data.get('end_date', today)
        
        cursor = conn.execute(
            "SELECT user_id, start_date, status FROM user_status WHERE id = ?",
            (status_id,)
        )
        status = cursor.fetchone()
        
        if not status:
            raise HTTPException(status_code=404, detail="Статус не найден")
        
        if status['user_id'] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        try:
            start_date_obj = parse_date(status['start_date'])
            end_date_obj = parse_date(end_date)
            if end_date_obj < start_date_obj:
                raise HTTPException(status_code=400, detail="Дата закрытия не может быть раньше даты начала")
        except ValueError:
            pass
        
        has_overlap, overlapping_status = check_status_overlap(current_user["user_id"], status['start_date'], end_date, status_id)
        
        if has_overlap:
            raise HTTPException(
                status_code=400, 
                detail=f"Пересечение с {overlapping_status}"
            )
        
        conn.execute(
            "UPDATE user_status SET end_date = ? WHERE id = ?",
            (end_date, status_id)
        )
        conn.commit()
        
        return {"message": "Статус закрыт", "success": True}
    finally:
        conn.close()

@app.delete("/api/v1/status/last")
async def delete_last_status(current_user=Depends(get_current_user)):
    conn = get_db()
    cursor = conn.execute("SELECT id FROM user_status WHERE user_id = ? ORDER BY start_date DESC LIMIT 1", (current_user["user_id"],))
    last = cursor.fetchone()
    if last:
        conn.execute("DELETE FROM user_status WHERE id = ?", (last['id'],))
        conn.commit()
    conn.close()
    return {"message": "Последний статус удален", "success": True}

@app.delete("/api/v1/status/{status_id}")
async def delete_status_by_id(status_id: int, current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute(
            "SELECT user_id FROM user_status WHERE id = ?",
            (status_id,)
        )
        status = cursor.fetchone()
        
        if not status:
            raise HTTPException(status_code=404, detail="Статус не найден")
        
        if status['user_id'] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        conn.execute("DELETE FROM user_status WHERE id = ?", (status_id,))
        conn.commit()
        
        return {"message": "Статус удален", "success": True}
    finally:
        conn.close()

@app.put("/api/v1/status/{status_id}")
async def update_status_dates(
    status_id: int,
    request: Request,
    current_user=Depends(get_current_user)
):
    conn = get_db()
    try:
        data = await request.json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        cursor = conn.execute(
            "SELECT user_id, status FROM user_status WHERE id = ?",
            (status_id,)
        )
        status = cursor.fetchone()
        
        if not status:
            raise HTTPException(status_code=404, detail="Статус не найден")
        
        if status['user_id'] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        has_overlap, overlapping_status = check_status_overlap(current_user["user_id"], start_date, end_date, status_id)
        
        if has_overlap:
            raise HTTPException(
                status_code=400, 
                detail=f"Пересечение с {overlapping_status}"
            )
        
        conn.execute(
            "UPDATE user_status SET start_date = ?, end_date = ? WHERE id = ?",
            (start_date, end_date, status_id)
        )
        conn.commit()
        
        return {"message": "Даты обновлены", "success": True}
    finally:
        conn.close()

@app.patch("/api/v1/status/{status_id}/extend")
async def extend_sick_leave(
    status_id: int,
    request: Request,
    current_user=Depends(get_current_user)
):
    conn = get_db()
    try:
        data = await request.json()
        end_date = data.get('end_date')
        
        cursor = conn.execute(
            "SELECT user_id, start_date, status FROM user_status WHERE id = ?",
            (status_id,)
        )
        status = cursor.fetchone()
        
        if not status:
            raise HTTPException(status_code=404, detail="Статус не найден")
        
        if status['user_id'] != current_user["user_id"] and current_user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        has_overlap, overlapping_status = check_status_overlap(current_user["user_id"], status['start_date'], end_date, status_id)
        
        if has_overlap:
            raise HTTPException(
                status_code=400, 
                detail=f"Пересечение с {overlapping_status}"
            )
        
        conn.execute(
            "UPDATE user_status SET end_date = ? WHERE id = ?",
            (end_date, status_id)
        )
        conn.commit()
        
        return {"message": "Статус продлен", "success": True}
    finally:
        conn.close()

@app.get("/api/v1/status/current")
async def get_current_status_stats(current_user=Depends(get_current_user)):
    conn = get_db()
    cursor = conn.execute("SELECT user_id, full_name FROM users")
    users = cursor.fetchall()
    
    stats = {"total": len(users), "working": 0, "sick": 0, "trip": 0, "vacation": 0, "employees": []}
    today = datetime.now()
    
    for user in users:
        cursor = conn.execute("""
            SELECT status, start_date, end_date FROM user_status 
            WHERE user_id = ? 
            ORDER BY start_date DESC
        """, (user['user_id'],))
        
        active_status = None
        for row in cursor:
            is_active = is_status_active(row['start_date'], row['end_date'])
            
            if is_active:
                active_status = row
                break
        
        if active_status:
            status = active_status['status']
            start_date = active_status['start_date']
            end_date = active_status['end_date'] if active_status['end_date'] else 'настоящее время'
            period = f"{start_date} — {end_date}"
            
            if "Больничный" in status:
                stats["sick"] += 1
                status_type = "sick"
                status_text = "🤒 Больничный"
            elif "Командировка" in status:
                stats["trip"] += 1
                status_type = "trip"
                status_text = "✈️ Командировка"
            elif "Отпуск" in status:
                stats["vacation"] += 1
                status_type = "vacation"
                status_text = "🏖️ Отпуск"
            else:
                stats["working"] += 1
                status_type = "working"
                status_text = "🟢 На рабочем месте"
                period = ""
        else:
            stats["working"] += 1
            status_type = "working"
            status_text = "🟢 На рабочем месте"
            period = ""
            start_date = ""
            end_date = ""
        
        stats["employees"].append({
            "id": user['user_id'],
            "name": user['full_name'],
            "status_type": status_type,
            "status_text": status_text,
            "start_date": start_date,
            "end_date": end_date,
            "period": period
        })
    
    if stats["total"] > 0:
        stats["working_percent"] = round(stats["working"] / stats["total"] * 100)
        stats["sick_percent"] = round(stats["sick"] / stats["total"] * 100)
        stats["trip_percent"] = round(stats["trip"] / stats["total"] * 100)
        stats["vacation_percent"] = round(stats["vacation"] / stats["total"] * 100)
    
    conn.close()
    return stats

def require_admin(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ только для администраторов")
    return current_user

# ── Admin: Users ──────────────────────────────────────────────────────────────

@app.get("/api/v1/admin/users")
async def admin_get_users(current_user=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.execute("SELECT user_id, full_name, login, role, email FROM users ORDER BY full_name")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

@app.post("/api/v1/admin/users")
async def admin_create_user(request: Request, current_user=Depends(require_admin)):
    data = await request.json()
    full_name = data.get("full_name", "").strip()
    login = data.get("login", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "employee")
    email = data.get("email", "").strip() or None
    if not full_name or not login or not password:
        raise HTTPException(status_code=400, detail="Имя, логин и пароль обязательны")
    if role not in ("employee", "admin"):
        raise HTTPException(status_code=400, detail="Роль: employee или admin")
    conn = get_db()
    try:
        if conn.execute("SELECT 1 FROM users WHERE login = ?", (login,)).fetchone():
            raise HTTPException(status_code=409, detail="Логин уже занят")
        conn.execute("INSERT INTO users (full_name, login, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                     (full_name, login, hash_password(password), role, email))
        conn.commit()
        return {"message": "Пользователь создан", "success": True}
    finally:
        conn.close()

@app.put("/api/v1/admin/users/{user_id}")
async def admin_update_user(user_id: int, request: Request, current_user=Depends(require_admin)):
    data = await request.json()
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        fields, values = [], []
        if data.get("full_name", "").strip():
            fields.append("full_name = ?"); values.append(data["full_name"].strip())
        if data.get("login", "").strip():
            if conn.execute("SELECT 1 FROM users WHERE login = ? AND user_id != ?", (data["login"].strip(), user_id)).fetchone():
                raise HTTPException(status_code=409, detail="Логин уже занят")
            fields.append("login = ?"); values.append(data["login"].strip())
        if data.get("role") in ("employee", "admin"):
            fields.append("role = ?"); values.append(data["role"])
        if "email" in data:
            fields.append("email = ?"); values.append(data["email"].strip() or None)
        if data.get("password", "").strip():
            fields.append("password_hash = ?"); values.append(hash_password(data["password"].strip()))
        if not fields:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")
        values.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?", values)
        conn.commit()
        return {"message": "Пользователь обновлён", "success": True}
    finally:
        conn.close()

@app.delete("/api/v1/admin/users/{user_id}")
async def admin_delete_user(user_id: int, current_user=Depends(require_admin)):
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        conn.execute("DELETE FROM exams WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_status WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM fcm_tokens WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        return {"message": "Пользователь удалён", "success": True}
    finally:
        conn.close()

# ── Admin: Exams ──────────────────────────────────────────────────────────────

@app.get("/api/v1/admin/exams")
async def admin_get_exams(current_user=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.execute("""
            SELECT e.id, e.user_id, u.full_name, e.name, e.date, e.duration
            FROM exams e JOIN users u ON e.user_id = u.user_id
            ORDER BY u.full_name, e.date DESC
        """)
        result = []
        today = datetime.now()
        for row in cursor.fetchall():
            try:
                exam_date = datetime.strptime(row['date'], '%d.%m.%Y')
                duration_months = int(row['duration'])
                end_date = exam_date + timedelta(days=duration_months * 30)
                days_left = (end_date - today).days
                status = "Просрочен" if days_left < 0 else ("Истекает" if days_left <= 30 else "Действующий")
                expires = end_date.strftime('%d.%m.%Y')
            except:
                days_left = 0; status = ""; expires = ""
            result.append({"id": row['id'], "user_id": row['user_id'], "user_name": row['full_name'],
                           "name": row['name'], "date": row['date'], "duration": row['duration'],
                           "expires_at": expires, "days_left": days_left, "status": status})
        return result
    finally:
        conn.close()

@app.post("/api/v1/admin/exams")
async def admin_create_exam(request: Request, current_user=Depends(require_admin)):
    data = await request.json()
    user_id = data.get("user_id")
    exam_type_id = data.get("exam_type_id")
    date_str = data.get("date", "").strip()
    if not user_id or not exam_type_id or not date_str:
        raise HTTPException(status_code=400, detail="user_id, exam_type_id и date обязательны")
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        exam_type = conn.execute("SELECT name, duration FROM exam_types WHERE id = ?", (exam_type_id,)).fetchone()
        if not exam_type:
            raise HTTPException(status_code=404, detail="Тип экзамена не найден")
        try:
            exam_date = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = exam_date.strftime('%d.%m.%Y')
        except:
            raise HTTPException(status_code=400, detail="Формат даты: YYYY-MM-DD")
        conn.execute("""INSERT INTO exams (user_id, name, date, duration, notification_sent, month_notification_sent,
                          week_notification_sent, exam_day_notification_sent, end_day_notification_sent, last_notification_day)
                          VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0, 0)""",
                     (user_id, exam_type['name'], formatted_date, str(exam_type['duration'])))
        conn.commit()
        return {"message": "Экзамен добавлен", "success": True}
    finally:
        conn.close()

@app.put("/api/v1/admin/exams/{exam_id}")
async def admin_update_exam(exam_id: int, request: Request, current_user=Depends(require_admin)):
    data = await request.json()
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM exams WHERE id = ?", (exam_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Экзамен не найден")
        fields, values = [], []
        if data.get("date", "").strip():
            date_str = data["date"].strip()
            try:
                d = datetime.strptime(date_str, '%Y-%m-%d'); date_str = d.strftime('%d.%m.%Y')
            except:
                try: datetime.strptime(date_str, '%d.%m.%Y')
                except: raise HTTPException(status_code=400, detail="Неверный формат даты")
            fields.append("date = ?"); values.append(date_str)
        if data.get("name", "").strip():
            fields.append("name = ?"); values.append(data["name"].strip())
        if data.get("duration"):
            fields.append("duration = ?"); values.append(str(data["duration"]))
        if not fields:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")
        values.append(exam_id)
        conn.execute(f"UPDATE exams SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        return {"message": "Экзамен обновлён", "success": True}
    finally:
        conn.close()

@app.delete("/api/v1/admin/exams/{exam_id}")
async def admin_delete_exam(exam_id: int, current_user=Depends(require_admin)):
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM exams WHERE id = ?", (exam_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Экзамен не найден")
        conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        conn.commit()
        return {"message": "Экзамен удалён", "success": True}
    finally:
        conn.close()

# ── Admin: Exam Types ─────────────────────────────────────────────────────────

@app.post("/api/v1/admin/exam-types")
async def admin_create_exam_type(request: Request, current_user=Depends(require_admin)):
    data = await request.json()
    name = data.get("name", "").strip()
    duration = data.get("duration")
    emoji = data.get("emoji", "📚").strip() or "📚"
    if not name or not duration:
        raise HTTPException(status_code=400, detail="name и duration обязательны")
    conn = get_db()
    try:
        if conn.execute("SELECT 1 FROM exam_types WHERE name = ?", (name,)).fetchone():
            raise HTTPException(status_code=409, detail="Тип с таким названием уже существует")
        conn.execute("INSERT INTO exam_types (name, duration, emoji) VALUES (?, ?, ?)", (name, duration, emoji))
        conn.commit()
        return {"message": "Тип экзамена создан", "success": True}
    finally:
        conn.close()

@app.put("/api/v1/admin/exam-types/{type_id}")
async def admin_update_exam_type(type_id: int, request: Request, current_user=Depends(require_admin)):
    data = await request.json()
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM exam_types WHERE id = ?", (type_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Тип экзамена не найден")
        fields, values = [], []
        if data.get("name", "").strip():
            fields.append("name = ?"); values.append(data["name"].strip())
        if data.get("duration"):
            fields.append("duration = ?"); values.append(int(data["duration"]))
        if data.get("emoji"):
            fields.append("emoji = ?"); values.append(data["emoji"].strip() or "📚")
        if not fields:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")
        values.append(type_id)
        conn.execute(f"UPDATE exam_types SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        return {"message": "Тип экзамена обновлён", "success": True}
    finally:
        conn.close()

@app.delete("/api/v1/admin/exam-types/{type_id}")
async def admin_delete_exam_type(type_id: int, current_user=Depends(require_admin)):
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM exam_types WHERE id = ?", (type_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Тип экзамена не найден")
        conn.execute("DELETE FROM exam_types WHERE id = ?", (type_id,))
        conn.commit()
        return {"message": "Тип экзамена удалён", "success": True}
    finally:
        conn.close()

# ── Admin: Statuses ───────────────────────────────────────────────────────────

@app.get("/api/v1/admin/statuses")
async def admin_get_statuses(current_user=Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.execute("""
            SELECT s.id, s.user_id, u.full_name, s.status, s.start_date, s.end_date
            FROM user_status s JOIN users u ON s.user_id = u.user_id
            ORDER BY s.start_date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

@app.post("/api/v1/admin/statuses")
async def admin_create_status(request: Request, current_user=Depends(require_admin)):
    data = await request.json()
    user_id = data.get("user_id")
    status = data.get("status", "").strip()
    start_date = data.get("start_date", "").strip()
    end_date = data.get("end_date", "").strip() or None
    if not user_id or not status or not start_date:
        raise HTTPException(status_code=400, detail="user_id, status и start_date обязательны")
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        conn.execute("INSERT INTO user_status (user_id, status, start_date, end_date) VALUES (?, ?, ?, ?)",
                     (user_id, status, start_date, end_date))
        conn.commit()
        return {"message": "Статус добавлен", "success": True}
    finally:
        conn.close()

@app.put("/api/v1/admin/statuses/{status_id}")
async def admin_update_status(status_id: int, request: Request, current_user=Depends(require_admin)):
    data = await request.json()
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM user_status WHERE id = ?", (status_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Статус не найден")
        fields, values = [], []
        if data.get("status", "").strip():
            fields.append("status = ?"); values.append(data["status"].strip())
        if data.get("start_date", "").strip():
            fields.append("start_date = ?"); values.append(data["start_date"].strip())
        if "end_date" in data:
            fields.append("end_date = ?"); values.append(data["end_date"].strip() if data["end_date"] else None)
        if not fields:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")
        values.append(status_id)
        conn.execute(f"UPDATE user_status SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        return {"message": "Статус обновлён", "success": True}
    finally:
        conn.close()

@app.delete("/api/v1/admin/statuses/{status_id}")
async def admin_delete_status(status_id: int, current_user=Depends(require_admin)):
    conn = get_db()
    try:
        if not conn.execute("SELECT 1 FROM user_status WHERE id = ?", (status_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Статус не найден")
        conn.execute("DELETE FROM user_status WHERE id = ?", (status_id,))
        conn.commit()
        return {"message": "Статус удалён", "success": True}
    finally:
        conn.close()

@app.get("/")
async def root():
    if os.path.exists('new_uaiss.html'):
        return FileResponse('new_uaiss.html')
    return {"message": "UAISS Web API работает. Добавьте файл new_uaiss.html"}

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

scheduler = None

def start_scheduler():
    global scheduler
    if scheduler is not None:
        try:
            scheduler.shutdown()
        except:
            pass
    
    scheduler = BackgroundScheduler()
    
    send_hour = CONFIG['notifications']['send_time_hour']
    send_minute = CONFIG['notifications']['send_time_minute']
    
    scheduler.add_job(
        func=check_and_send_notifications_sync,
        trigger=CronTrigger(hour=send_hour, minute=send_minute),
        id='daily_notifications',
        name=f'Ежедневная отправка уведомлений в {send_hour:02d}:{send_minute:02d}',
        replace_existing=True
    )
    
    scheduler.start()
    print(f"📅 Планировщик уведомлений ЗАПУЩЕН!")
    print(f"   • Отправка КАЖДЫЙ ДЕНЬ в {send_hour:02d}:{send_minute:02d}")
    print(f"   • Дни уведомлений: {NOTIFY_DAYS}")
    print(f"   • Работает в фоне, не зависит от активности пользователей")
    
    atexit.register(lambda: scheduler.shutdown() if scheduler else None)
    
    return scheduler

print("🚀 Инициализация UAISS Web API...")
start_scheduler()

if __name__ == "__main__":
    import uvicorn
    check_and_fix_database()
    print("=" * 50)
    print(f" {CONFIG['app']['name']} Сервер запущен!")
    print(f" http://localhost:{CONFIG['server']['port']}")
    print(" Документация: http://localhost:8000/docs")
    print("=" * 50)
    print("\n📧 Email уведомления:")
    print(f"   • Планировщик: каждый день в {CONFIG['notifications']['send_time_hour']:02d}:{CONFIG['notifications']['send_time_minute']:02d}")
    print(f"   • Дни уведомлений: {NOTIFY_DAYS}")
    print("   • Для ручной отправки: POST /api/v1/notifications/send (только админ)")
    print(f"\n🔧 Файл конфигурации: config.json")
    print("\n🔑 Тестовые учетные записи:")
    print("👤 Сотрудник: коваленко / 123456")
    print("👤 Сотрудник: смирнов / 123456")
    print("👑 Администратор: морозова / admin123")
    print()
    uvicorn.run(app, host=CONFIG['server']['host'], port=CONFIG['server']['port'])