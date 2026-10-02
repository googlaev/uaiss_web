from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime, timedelta, date
from calendar import monthrange
import hashlib
import hmac
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
import random
import string
import requests
import time
from urllib.parse import parse_qsl

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
        "max": {
            "enabled": False,
            "token": "",
            "api_url": "https://botapi.max.ru",
            "bot_username": "",
            "link_code_ttl_minutes": 15,
            "allow_name_link": True
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

SECRET_KEY = CONFIG['auth'].get('jwt_secret_key', secrets.token_hex(32))
ALGORITHM = "HS256"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

SMTP_HOST = CONFIG['smtp']['host']
SMTP_PORT = CONFIG['smtp']['port']
SMTP_USER = CONFIG['smtp']['user']
SMTP_PASSWORD = CONFIG['smtp']['password']
SMTP_USE_TLS = CONFIG['smtp'].get('use_tls', True)

NOTIFICATIONS_ENABLED = CONFIG['notifications']['enabled']
NOTIFY_DAYS = CONFIG['notifications']['notify_days']
NOTIFY_EXPIRED = CONFIG['notifications']['notify_expired']

MAX_CONFIG = CONFIG.get('max', {})
MAX_ENABLED = MAX_CONFIG.get('enabled', False)
MAX_TOKEN = MAX_CONFIG.get('token', '')
MAX_API_URL = MAX_CONFIG.get('api_url', 'https://botapi.max.ru')
MAX_BOT_USERNAME = MAX_CONFIG.get('bot_username', '')
MAX_LINK_CODE_TTL_MINUTES = MAX_CONFIG.get('link_code_ttl_minutes', 15)
MAX_ALLOW_NAME_LINK = MAX_CONFIG.get('allow_name_link', True)

class LoginRequest(BaseModel):
    login: str
    password: str
    max_init_data: Optional[str] = None

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

class MaxWebAppAuth(BaseModel):
    init_data: str

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
    if 'max_chat_id' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN max_chat_id TEXT")
        print("✅ Колонка max_chat_id добавлена")
    if 'max_user_id' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN max_user_id TEXT")
        print("✅ Колонка max_user_id добавлена")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS max_link_codes (
            code       TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

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

def send_max_message(chat_id: str, text: str) -> bool:
    """Отправка сообщения пользователю через MAX Bot API (botapi.max.ru)."""
    if not MAX_ENABLED or not MAX_TOKEN or not chat_id:
        return False
    try:
        r = requests.post(
            f"{MAX_API_URL}/messages",
            params={"chat_id": chat_id},
            headers={"Authorization": MAX_TOKEN},
            json={"text": text},
            timeout=10,
        )
        r.raise_for_status()
        print(f"✅ MAX-уведомление отправлено на chat_id={chat_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки MAX-сообщения на chat_id={chat_id}: {e}")
        return False

def generate_max_link_code(user_id: int) -> str:
    """Генерирует одноразовый код привязки MAX-аккаунта к пользователю UAISS."""
    conn = get_db()
    try:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        conn.execute("DELETE FROM max_link_codes WHERE user_id = ?", (user_id,))
        conn.execute(
            "INSERT INTO max_link_codes (code, user_id, created_at) VALUES (?, ?, ?)",
            (code, user_id, datetime.now().isoformat()),
        )
        conn.commit()
        return code
    finally:
        conn.close()


# ── MAX Mini App: валидация initData, выдаваемого MAX Bridge на клиенте ──────
# Алгоритм идентичен Telegram WebApp: secret_key = HMAC_SHA256("WebAppData", bot_token),
# затем HMAC_SHA256(data_check_string, secret_key) сравнивается с полем hash.
# https://dev.max.ru/docs/webapps/validation

def verify_max_init_data(init_data: str, max_age_seconds: int = 86400) -> Optional[dict]:
    """Проверяет подпись initData, присланного мини-приложением MAX.
    Возвращает распарсенные поля (user, chat, auth_date, ...) или None, если невалидно."""
    if not MAX_ENABLED or not MAX_TOKEN or not init_data:
        return None
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True)
        data = {k: v for k, v in pairs}
        received_hash = data.pop('hash', None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hmac.new(b"WebAppData", MAX_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_hash, received_hash):
            return None
        auth_date = data.get('auth_date')
        if auth_date:
            try:
                if datetime.now().timestamp() - int(auth_date) > max_age_seconds:
                    return None
            except ValueError:
                pass
        result = dict(data)
        for field in ('user', 'chat', 'receiver'):
            if field in result:
                try:
                    result[field] = json.loads(result[field])
                except (ValueError, TypeError):
                    pass
        return result
    except Exception as e:
        print(f"❌ Ошибка проверки MAX initData: {e}")
        return None


def link_max_account_from_webapp(user_id: int, chat_id, max_user_id):
    """Привязывает MAX-чат к аккаунту UAISS после проверенного входа по логину/паролю
    внутри мини-приложения — личность уже подтверждена паролем, поэтому без доп. проверок."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET max_chat_id = ?, max_user_id = ? WHERE user_id = ?",
            (str(chat_id), str(max_user_id) if max_user_id else None, user_id),
        )
        conn.commit()
    finally:
        conn.close()


# ── MAX Bot: приём входящих сообщений (/link, /фио) в этом же процессе ────────
# Работает как фоновый поток (long polling botapi.max.ru/updates), поэтому
# отдельный процесс/приложение для MAX-бота больше не требуется.

def _max_normalize(s: str) -> str:
    return " ".join(s.split()).strip()

def _max_surname_initials(full_name: str):
    """'Коваленко Александр Викторович' -> ('Коваленко', 'АВ')"""
    parts = _max_normalize(full_name).split(" ")
    if len(parts) < 2:
        return None
    return parts[0], "".join(p[0].upper() for p in parts[1:] if p)

def _max_full_initials(full_name: str):
    """'Гуляев Иван Павлович' -> 'ГИП'"""
    parts = _max_normalize(full_name).split(" ")
    if len(parts) < 2:
        return None
    return "".join(p[0].upper() for p in parts if p)

def consume_max_link_code(code: str):
    """Проверяет код привязки и возвращает user_id, если код валиден и не истёк."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT user_id, created_at FROM max_link_codes WHERE code = ?", (code,)
        ).fetchone()
        if not row:
            return None
        created_at = datetime.fromisoformat(row["created_at"])
        if datetime.now() - created_at > timedelta(minutes=MAX_LINK_CODE_TTL_MINUTES):
            conn.execute("DELETE FROM max_link_codes WHERE code = ?", (code,))
            conn.commit()
            return None
        return row["user_id"]
    finally:
        conn.close()

def max_link_account_by_code(user_id: int, chat_id, max_user_id):
    """Привязка по коду — код мог получить только владелец аккаунта (сгенерирован
    в приложении под его JWT), поэтому переписываем max_chat_id без проверок."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET max_chat_id = ?, max_user_id = ? WHERE user_id = ?",
            (str(chat_id), str(max_user_id) if max_user_id else None, user_id),
        )
        conn.execute("DELETE FROM max_link_codes WHERE user_id = ?", (user_id,))
        conn.commit()
        row = conn.execute("SELECT full_name FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row["full_name"] if row else None
    finally:
        conn.close()

def find_max_user_by_name(query: str):
    """Ищет пользователя по полному ФИО, 'Фамилия И.О.' или слитным инициалам 'ГИП'.
    Возвращает (user_id, full_name), ('ambiguous', None) или (None, None)."""
    query = _max_normalize(query)
    if not query:
        return None, None

    conn = get_db()
    try:
        rows = conn.execute("SELECT user_id, full_name FROM users").fetchall()
    finally:
        conn.close()

    q_lower = query.lower()
    exact = [r for r in rows if _max_normalize(r["full_name"]).lower() == q_lower]
    if len(exact) == 1:
        return exact[0]["user_id"], exact[0]["full_name"]
    if len(exact) > 1:
        return "ambiguous", None

    q_parts = [p for p in query.replace(".", " ").split(" ") if p]

    if len(q_parts) == 1:
        q_compact = q_parts[0].upper()
        if q_compact.isalpha() and 2 <= len(q_compact) <= 4:
            matches = [r for r in rows if _max_full_initials(r["full_name"]) == q_compact]
            if len(matches) == 1:
                return matches[0]["user_id"], matches[0]["full_name"]
            if len(matches) > 1:
                return "ambiguous", None

    if len(q_parts) >= 2:
        q_surname = q_parts[0].lower()
        q_initials = "".join(p[0].upper() for p in q_parts[1:])
        matches = []
        for r in rows:
            si = _max_surname_initials(r["full_name"])
            if si and si[0].lower() == q_surname and si[1] == q_initials:
                matches.append(r)
        if len(matches) == 1:
            return matches[0]["user_id"], matches[0]["full_name"]
        if len(matches) > 1:
            return "ambiguous", None

    return None, None

def max_link_account_by_name(user_id: int, chat_id, max_user_id):
    """Привязка по ФИО/инициалам — личность не подтверждена паролем, поэтому если
    аккаунт уже привязан к другому чату, отказываем (иначе можно перехватить
    чужие уведомления, зная только имя коллеги)."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT max_chat_id, full_name FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return False, "❌ Пользователь не найден."

        if row["max_chat_id"] and str(row["max_chat_id"]) != str(chat_id):
            return False, (
                "⚠️ Этот аккаунт уже привязан к другому чату MAX.\n\n"
                "Если это ваш аккаунт и вы сменили чат — отвяжите MAX в приложении "
                "(профиль → «Уведомления в MAX» → «Отвязать») и повторите попытку, "
                "либо получите код и используйте /link КОД."
            )

        conn.execute(
            "UPDATE users SET max_chat_id = ?, max_user_id = ? WHERE user_id = ?",
            (str(chat_id), str(max_user_id) if max_user_id else None, user_id),
        )
        conn.execute("DELETE FROM max_link_codes WHERE user_id = ?", (user_id,))
        conn.commit()
        return True, (
            f"✅ Готово, {row['full_name']}! Этот чат привязан к вашему аккаунту UAISS.\n\n"
            f"Теперь здесь будут приходить уведомления об истечении экзаменов."
        )
    finally:
        conn.close()

_MAX_WELCOME_BASE = (
    "👋 Привет! Я бот уведомлений UAISS.\n\n"
    "Я буду присылать сюда напоминания об истекающих экзаменах и допусках.\n\n"
    "Есть два способа привязать этот чат к своей учётной записи:\n\n"
    "1️⃣ По коду из приложения (надёжнее):\n"
    "   • Профиль → «Привязать MAX» → скопируйте код\n"
    "   • Отправьте мне: /link КОД\n"
)
_MAX_WELCOME_NAME_HINT = (
    "\n2️⃣ По ФИО или инициалам (без захода в приложение):\n"
    "   • Полностью: /фио Гуляев Иван Павлович\n"
    "   • Фамилия + инициалы: /фио Гуляев И.П.\n"
    "   • Слитные инициалы: /фио ГИП\n"
)

def _max_welcome_text():
    return _MAX_WELCOME_BASE + (_MAX_WELCOME_NAME_HINT if MAX_ALLOW_NAME_LINK else "")

def _max_bot_handle_link_by_code(chat_id, max_user_id, parts):
    if len(parts) != 2:
        send_max_message(chat_id, "⚠️ Формат: /link КОД\n\nКод можно получить в приложении UAISS (профиль → «Привязать MAX»).")
        return
    code = parts[1].strip().upper()
    user_id = consume_max_link_code(code)
    if not user_id:
        send_max_message(chat_id, "❌ Код неверный или истёк. Получите новый код в приложении и повторите попытку.")
        return
    full_name = max_link_account_by_code(user_id, chat_id, max_user_id)
    name_part = f", {full_name}" if full_name else ""
    send_max_message(chat_id, f"✅ Готово{name_part}! Аккаунт UAISS привязан к этому чату.\n\nТеперь вы будете получать здесь уведомления об истечении экзаменов.")

def _max_bot_handle_link_by_name(chat_id, max_user_id, query):
    if not MAX_ALLOW_NAME_LINK:
        send_max_message(chat_id, "⚠️ Привязка по ФИО отключена администратором. Используйте /link КОД из приложения.")
        return
    if not query:
        send_max_message(
            chat_id,
            "⚠️ Формат:\n/фио Фамилия Имя Отчество\n/фио Фамилия И.О.\n/фио ГИП (слитные инициалы)\n\n"
            "Например: /фио Гуляев Иван Павлович или /фио ГИП",
        )
        return
    result_id, full_name = find_max_user_by_name(query)
    if result_id == "ambiguous":
        send_max_message(chat_id, "⚠️ Найдено несколько сотрудников с такими инициалами. Отправьте ФИО полностью, как в системе.")
        return
    if not result_id:
        send_max_message(chat_id, "❌ Сотрудник с таким ФИО не найден. Проверьте написание (как в UAISS) или получите код в приложении: профиль → «Привязать MAX».")
        return
    ok, reply = max_link_account_by_name(result_id, chat_id, max_user_id)
    send_max_message(chat_id, reply)

def _max_bot_handle_message(update: dict):
    msg = update.get("message", {})
    body = msg.get("body", {}).get("text", "").strip()
    chat_id = msg.get("recipient", {}).get("chat_id")
    max_user_id = msg.get("sender", {}).get("user_id")

    if not chat_id:
        return

    lower = body.lower()
    if lower.startswith("/start"):
        send_max_message(chat_id, _max_welcome_text())
    elif lower.startswith("/link"):
        _max_bot_handle_link_by_code(chat_id, max_user_id, body.split())
    elif lower.startswith("/фио") or lower.startswith("/fio") or lower.startswith("/иниц"):
        parts = body.split(maxsplit=1)
        _max_bot_handle_link_by_name(chat_id, max_user_id, parts[1] if len(parts) > 1 else "")
    else:
        send_max_message(chat_id, _max_welcome_text())

def _max_bot_get_updates(marker=None):
    params = {"timeout": 30}
    if marker is not None:
        params["marker"] = marker
    try:
        r = requests.get(
            f"{MAX_API_URL}/updates",
            params=params,
            headers={"Authorization": MAX_TOKEN},
            timeout=35,
        )
        if r.status_code == 401:
            print("❌ MAX-бот: токен недействителен (max.token в config.json). Приём сообщений остановлен.")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[max_bot get_updates] {e}")
        time.sleep(5)
        return {"updates": []}

def _max_bot_loop():
    print("💬 MAX-бот: приём входящих сообщений запущен (в этом же процессе)")
    marker = None
    while True:
        data = _max_bot_get_updates(marker)
        if data is None:
            return
        new_marker = data.get("marker")
        if new_marker:
            marker = new_marker
        for upd in data.get("updates", []):
            if upd.get("update_type") == "message_created":
                try:
                    _max_bot_handle_message(upd)
                except Exception as e:
                    print(f"[max_bot handler error] {e}")
        if not data.get("updates"):
            time.sleep(0.5)

def start_max_bot():
    if not MAX_ENABLED or not MAX_TOKEN:
        return
    thread = Thread(target=_max_bot_loop, daemon=True)
    thread.start()


def check_and_send_notifications_sync():
    """Ежедневная проверка экзаменов: шлёт email и/или MAX по одним и тем же порогам
    (NOTIFY_DAYS + просрочка). Канал считается «отработавшим», если сработал хотя бы
    один из них — last_notification_day общий для обоих, поэтому повторной отправки
    по тому же порогу не будет, даже если у пользователя настроены оба канала."""
    if not NOTIFICATIONS_ENABLED:
        print("ℹ️ Уведомления отключены в конфигурации")
        return 0

    print(f"\n🕐 Проверка экзаменов (email + MAX) в {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    conn = sqlite3.connect(CONFIG['database']['path'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    today = datetime.now().date()
    notifications_sent = 0

    cursor.execute("""
        SELECT u.user_id, u.full_name, u.email, u.max_chat_id,
               e.id as exam_id, e.name as exam_name,
               e.date as exam_date, e.duration,
               e.last_notification_day
        FROM users u
        JOIN exams e ON u.user_id = e.user_id
        WHERE (u.email IS NOT NULL AND u.email != '')
           OR (u.max_chat_id IS NOT NULL AND u.max_chat_id != '')
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
                    max_text = (
                        f"⚠️ Уведомление об экзамене\n\n"
                        f"Здравствуйте, {row['full_name']}!\n\n"
                        f"Ваш экзамен «{row['exam_name']}» истекает через {nd} дн. "
                        f"(до {end_date.strftime('%d.%m.%Y')}).\n\n"
                        f"Пожалуйста, продлите его в приложении UAISS."
                    )
                    email_ok = send_email(row['email'], subject, body) if row['email'] else False
                    max_ok = send_max_message(row['max_chat_id'], max_text) if row['max_chat_id'] else False
                    if email_ok or max_ok:
                        cursor.execute(
                            "UPDATE exams SET last_notification_day = ? WHERE id = ?",
                            (nd, exam_id)
                        )
                        conn.commit()
                        notifications_sent += 1
                        print(f"✅ Уведомление за {nd} дней отправлено для «{row['exam_name']}» "
                              f"(email={email_ok}, max={max_ok})")

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
                max_text = (
                    f"🔴 СРОЧНО! Экзамен просрочен\n\n"
                    f"Здравствуйте, {row['full_name']}!\n\n"
                    f"Экзамен «{row['exam_name']}» просрочен на {abs(days_left)} дн. "
                    f"(действовал до {end_date.strftime('%d.%m.%Y')}).\n\n"
                    f"Необходимо срочно пересдать экзамен."
                )
                email_ok = send_email(row['email'], subject, body) if row['email'] else False
                max_ok = send_max_message(row['max_chat_id'], max_text) if row['max_chat_id'] else False
                if email_ok or max_ok:
                    cursor.execute(
                        "UPDATE exams SET last_notification_day = -1 WHERE id = ?",
                        (exam_id,)
                    )
                    conn.commit()
                    notifications_sent += 1

        except Exception as e:
            print(f"Ошибка обработки экзамена: {e}")
            continue

    conn.close()
    print(f"📊 Отправлено уведомлений (email + MAX): {notifications_sent}")
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
        if auth_data.max_init_data:
            parsed = verify_max_init_data(auth_data.max_init_data)
            if parsed:
                max_user = parsed.get('user') or {}
                max_user_id = max_user.get('id')
                chat = parsed.get('chat') or {}
                chat_id = chat.get('id') or max_user_id
                if max_user_id:
                    link_max_account_from_webapp(user['user_id'], chat_id, max_user_id)
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

@app.post("/api/v1/notifications/send")
async def send_notifications_manual(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    thread = Thread(target=check_and_send_notifications_sync)
    thread.daemon = True
    thread.start()

    return {"message": "Уведомления начали отправляться в фоновом режиме"}

@app.post("/api/v1/max/notifications/send")
async def send_max_notifications_manual(current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    # MAX-уведомления теперь шлются в общей проверке (email + MAX) по тем же порогам дней
    thread = Thread(target=check_and_send_notifications_sync)
    thread.daemon = True
    thread.start()

    return {"message": "Проверка и отправка уведомлений (email + MAX) запущена в фоновом режиме"}

@app.post("/api/v1/max/webapp-auth")
async def max_webapp_auth(data: MaxWebAppAuth):
    """Автовход для мини-приложения MAX: если этот MAX-аккаунт уже привязан
    к пользователю UAISS, выдаёт JWT без логина/пароля."""
    parsed = verify_max_init_data(data.init_data)
    if not parsed:
        raise HTTPException(status_code=401, detail="Невалидные данные MAX WebApp")
    max_user = parsed.get('user') or {}
    max_user_id = max_user.get('id')
    if not max_user_id:
        raise HTTPException(status_code=400, detail="Нет данных пользователя MAX")
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT user_id, full_name, role, email FROM users WHERE max_user_id = ?",
            (str(max_user_id),),
        ).fetchone()
        if not row:
            return {"linked": False}
        access_token = create_token(row['user_id'], row['role'])
        return {
            "linked": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": row['user_id'],
            "full_name": row['full_name'],
            "role": row['role'],
            "email": row['email'] if row['email'] else None,
        }
    finally:
        conn.close()

@app.get("/api/v1/max/status")
async def max_status(current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        cursor = conn.execute("SELECT max_chat_id FROM users WHERE user_id = ?", (current_user["user_id"],))
        user = cursor.fetchone()
        linked = bool(user and user["max_chat_id"])
        return {
            "enabled": MAX_ENABLED,
            "linked": linked,
            "bot_username": MAX_BOT_USERNAME,
            "allow_name_link": MAX_ALLOW_NAME_LINK,
        }
    finally:
        conn.close()

@app.post("/api/v1/max/link-code")
async def max_link_code(current_user=Depends(get_current_user)):
    if not MAX_ENABLED:
        raise HTTPException(status_code=400, detail="MAX-уведомления не настроены на сервере")
    code = generate_max_link_code(current_user["user_id"])
    return {
        "code": code,
        "expires_in_minutes": MAX_LINK_CODE_TTL_MINUTES,
        "bot_username": MAX_BOT_USERNAME,
        "allow_name_link": MAX_ALLOW_NAME_LINK,
        "instructions": f"Откройте бота MAX{(' ' + MAX_BOT_USERNAME) if MAX_BOT_USERNAME else ''} и отправьте команду: /link {code}",
    }

@app.delete("/api/v1/max/link")
async def max_unlink(current_user=Depends(get_current_user)):
    conn = get_db()
    try:
        conn.execute("UPDATE users SET max_chat_id = NULL, max_user_id = NULL WHERE user_id = ?",
                      (current_user["user_id"],))
        conn.execute("DELETE FROM max_link_codes WHERE user_id = ?", (current_user["user_id"],))
        conn.commit()
        return {"message": "MAX-аккаунт отвязан", "success": True}
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

@app.get("/")
async def root():
    if os.path.exists('new_uaiss.html'):
        return FileResponse('new_uaiss.html')
    return {"message": "UAISS Web API работает. Добавьте файл new_uaiss.html"}

# Мини-приложение MAX: тот же SPA, что и в www/index.html (используется и в APK),
# отдаётся по HTTPS с того же домена, что и API — укажите этот URL в настройках
# бота в business.max.ru/self (Чат-боты → ваш бот → ⋮ → Настройки → URL мини-приложения).
_WWW_DIR = os.path.join(os.path.dirname(__file__), 'www')
if os.path.isdir(_WWW_DIR):
    app.mount("/maxapp", StaticFiles(directory=_WWW_DIR, html=True), name="maxapp")

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
    print(f"   • Email + MAX: КАЖДЫЙ ДЕНЬ в {send_hour:02d}:{send_minute:02d} (один и тот же порог дней для обоих каналов)")
    print(f"   • Дни уведомлений: {NOTIFY_DAYS}")
    print(f"   • Работает в фоне, не зависит от активности пользователей")
    
    atexit.register(lambda: scheduler.shutdown() if scheduler else None)
    
    return scheduler

print("🚀 Инициализация UAISS Web API...")
start_scheduler()
start_max_bot()

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
    print(f"\n💬 MAX уведомления: {'ВКЛЮЧЕНЫ' if MAX_ENABLED else 'выключены (заполните max.token и max.enabled в config.json)'}")
    if MAX_ENABLED:
        print("   • Приём входящих сообщений бота работает в этом же процессе (отдельный скрипт не нужен)")
        print("   • Привязка аккаунта: профиль → «Привязать MAX» → код → команда /link <код> боту")
        print("   • Либо в самом боте: /фио Фамилия И.О. (например /фио ГИП)")
    print(f"\n🔧 Файл конфигурации: config.json")
    print("\n🔑 Тестовые учетные записи:")
    print("👤 Сотрудник: коваленко / 123456")
    print("👤 Сотрудник: смирнов / 123456")
    print("👑 Администратор: морозова / admin123")
    print()
    uvicorn.run(app, host=CONFIG['server']['host'], port=CONFIG['server']['port'])