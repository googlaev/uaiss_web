from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime, timedelta
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

app = FastAPI(title="UAISS Web API", version="1.0.0")

SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


SMTP_HOST = "smtp.gmail.com"        # Адрес SMTP сервера
SMTP_PORT = 587                      # Порт (587 для STARTTLS, 465 для SSL)
SMTP_USER = "uaiss.gpn@gmail.com"   
SMTP_PASSWORD = "ywtpwwulycpalogd"  

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

# Найдите функцию check_and_fix_database() и замените добавление тестовых пользователей:

def check_and_fix_database():
    print("\n🔍 Проверка структуры базы данных...")
    conn = sqlite3.connect('exams.db')
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
    
    def hash_password(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()
    
    # ИЗМЕНЕНО: логины теперь без @uaiss.ru
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'smirnov'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (full_name, login, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                       ("Алексей Смирнов", "smirnov", hash_password("123456"), "employee", "user@example.com"))
        print("✅ Добавлен: smirnov / 123456 (Алексей Смирнов)")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'morozova'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (full_name, login, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                       ("Екатерина Морозова", "morozova", hash_password("admin123"), "admin", "admin@example.com"))
        print("✅ Добавлен: morozova / admin123 (Екатерина Морозова - Администратор)")
    
    # Обновление существующих пользователей (убираем @uaiss.ru из логинов)
    cursor.execute("SELECT user_id, login FROM users WHERE login LIKE '%@uaiss.ru'")
    users_with_email_login = cursor.fetchall()
    for user in users_with_email_login:
        # Извлекаем фамилию из full_name или логина
        cursor.execute("SELECT full_name FROM users WHERE user_id = ?", (user['user_id'],))
        user_data = cursor.fetchone()
        if user_data:
            # Берем фамилию из полного имени
            name_parts = user_data['full_name'].split()
            if len(name_parts) >= 1:
                # Транслитерация или直接用 фамилия
                surname = name_parts[-1].lower()  # Берем последнюю часть как фамилию
                # Для кириллицы можно оставить как есть
                new_login = surname
                
                # Проверяем, что такой логин еще не существует
                cursor.execute("SELECT COUNT(*) FROM users WHERE login = ? AND user_id != ?", (new_login, user['user_id']))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("UPDATE users SET login = ? WHERE user_id = ?", (new_login, user['user_id']))
                    print(f"✅ Логин обновлен: {user['login']} -> {new_login}")
    
    conn.commit()
    conn.close()
    print("\n✅ База данных готова к работе!")
    print("\n🔑 Тестовые учетные записи:")
    print("   Сотрудник:   login: smirnov   / password: 123456")
    print("   Администратор: login: morozova / password: admin123")
    print()
    return True

def get_db():
    conn = sqlite3.connect('exams.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def create_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": datetime.utcnow() + timedelta(hours=8)}
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

def is_status_active(end_date_str: Optional[str]) -> bool:
    if end_date_str is None or end_date_str == '':
        return True
    try:
        end_date = datetime.strptime(end_date_str, '%d.%m.%Y')
        return end_date >= datetime.now()
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

# ============= ФУНКЦИИ EMAIL УВЕДОМЛЕНИЙ =============
def send_email(to_email: str, subject: str, body: str):
    """Отправка email (синхронная версия)"""
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
    """Асинхронная отправка email (в фоновом потоке)"""
    thread = Thread(target=send_email, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()

def check_and_send_notifications_sync():
    """Проверка экзаменов и отправка уведомлений"""
    print(f"\n🕐 Проверка экзаменов в {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    conn = sqlite3.connect('exams.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Получаем всех пользователей с email
    cursor.execute("""
        SELECT u.user_id, u.full_name, u.email, 
               e.id as exam_id, e.name as exam_name, 
               e.date as exam_date, e.duration,
               e.last_notification_day
        FROM users u
        JOIN exams e ON u.user_id = e.user_id
        WHERE u.email IS NOT NULL AND u.email != ''
    """)
    
    today = datetime.now().date()
    notifications_sent = 0
    
    # Словарь для хранения уведомлений по дням
    notifications_map = {}  # {user_email: {'name': '', 'exams': {30: [], 7: [], 3: [], 2: [], 1: []}}}
    
    for row in cursor.fetchall():
        try:
            exam_date = datetime.strptime(row['exam_date'], '%d.%m.%Y').date()
            duration_months = int(row['duration'])
            
            # Вычисляем дату окончания
            # Простое добавление месяцев (приблизительно)
            year = exam_date.year + (exam_date.month + duration_months - 1) // 12
            month = (exam_date.month + duration_months - 1) % 12 + 1
            day = exam_date.day
            # Корректировка дня для последних чисел месяца
            from calendar import monthrange
            last_day = monthrange(year, month)[1]
            end_day = min(day, last_day)
            end_date = date(year, month, end_day)
            
            days_left = (end_date - today).days
            
            # Определяем, нужно ли отправить уведомление (точные дни: 30, 7, 3, 2, 1)
            notify_days = [30, 7, 3, 2, 1]
            notify_day = None
            
            for nd in notify_days:
                if days_left == nd:
                    notify_day = nd
                    break
            
            # Также проверяем просроченные экзамены (days_left < 0)
            is_expired = days_left < 0
            
            if notify_day is not None or is_expired:
                email = row['email']
                if email not in notifications_map:
                    notifications_map[email] = {
                        'name': row['full_name'],
                        'exams': {30: [], 7: [], 3: [], 2: [], 1: [], 'expired': []}
                    }
                
                exam_info = {
                    'name': row['exam_name'],
                    'end_date': end_date.strftime('%d.%m.%Y'),
                    'days_left': days_left
                }
                
                if is_expired:
                    notifications_map[email]['exams']['expired'].append(exam_info)
                elif notify_day is not None:
                    notifications_map[email]['exams'][notify_day].append(exam_info)
                    
        except Exception as e:
            print(f"Ошибка обработки экзамена: {e}")
            continue
    
    conn.close()
    
    # Отправляем уведомления
    for email, data in notifications_map.items():
        subject = f"📋 Уведомление об экзаменах - {data['name']}"
        
        body = f"""
Здравствуйте, {data['name']}!

Система уведомляет вас о статусе ваших экзаменов.

{'=' * 50}

"""
        # Просроченные экзамены
        if data['exams']['expired']:
            body += "🔴 ПРОСРОЧЕННЫЕ ЭКЗАМЕНЫ:\n"
            for exam in data['exams']['expired']:
                body += f"""
   ❌ {exam['name']}
      • Просрочен на {abs(exam['days_left'])} дней
      • Действовал до: {exam['end_date']}
      • НЕОБХОДИМО СРОЧНО ПЕРЕСДАТЬ!

"""
        
        # Уведомление за 30 дней
        if data['exams'][30]:
            body += "📅 ИСТЕКАЕТ ЧЕРЕЗ 30 ДНЕЙ:\n"
            for exam in data['exams'][30]:
                body += f"""
   🟡 {exam['name']}
      • Истекает через: {exam['days_left']} дней
      • Действует до: {exam['end_date']}
      • Рекомендуется запланировать пересдачу

"""
        
        # Уведомление за 7 дней
        if data['exams'][7]:
            body += "🟠 ИСТЕКАЕТ ЧЕРЕЗ 7 ДНЕЙ:\n"
            for exam in data['exams'][7]:
                body += f"""
   🟠 {exam['name']}
      • Истекает через: {exam['days_left']} дней
      • Действует до: {exam['end_date']}
      • Рекомендуется запланировать пересдачу

"""
        
        # Уведомление за 3 дня
        if data['exams'][3]:
            body += "🔴 ИСТЕКАЕТ ЧЕРЕЗ 3 ДНЯ:\n"
            for exam in data['exams'][3]:
                body += f"""
   🔴 {exam['name']}
      • Истекает через: {exam['days_left']} дней
      • Действует до: {exam['end_date']}
      • СРОЧНО ПРОДЛИТЕ ЭКЗАМЕН!

"""
        
        # Уведомление за 2 дня
        if data['exams'][2]:
            body += "🔴 ИСТЕКАЕТ ЧЕРЕЗ 2 ДНЯ:\n"
            for exam in data['exams'][2]:
                body += f"""
   🔴 {exam['name']}
      • Истекает через: {exam['days_left']} дней
      • Действует до: {exam['end_date']}
      • СРОЧНО ПРОДЛИТЕ ЭКЗАМЕН!

"""
        
        # Уведомление за 1 день
        if data['exams'][1]:
            body += "🔴 ИСТЕКАЕТ ЗАВТРА! (1 день):\n"
            for exam in data['exams'][1]:
                body += f"""
   🔴 {exam['name']}
      • Истекает через: {exam['days_left']} дней
      • Действует до: {exam['end_date']}
      • СРОЧНО ПРОДЛИТЕ ЭКЗАМЕН!

"""
        
        body += f"""
{'=' * 50}

📌 Действия:
• Просроченные экзамены - срочно пересдайте
• Экзамены с остатком 7-30 дней - запланируйте продление
• Экзамены с остатком 1-3 дня - срочно продлите

➡️ Для продления экзамена войдите в систему:
   http://localhost:8000

---
Это автоматическое уведомление. Пожалуйста, не отвечайте на это письмо.
"""
        
        if send_email(email, subject, body):
            notifications_sent += 1
            print(f"✅ Уведомление отправлено на {email}")
    
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

# Ручная отправка уведомлений (для админа)
@app.post("/api/v1/notifications/send")
async def send_notifications_manual(current_user=Depends(get_current_user)):
    """Ручная отправка уведомлений (только для админа)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    # Запускаем в фоновом потоке
    thread = Thread(target=check_and_send_notifications_sync)
    thread.daemon = True
    thread.start()
    
    return {"message": "Уведомления начали отправляться в фоновом режиме"}

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
    cursor = conn.execute("SELECT name, duration FROM exam_types WHERE id = ?", (exam_data.exam_type_id,))
    exam_type = cursor.fetchone()
    if not exam_type:
        raise HTTPException(status_code=404, detail="Тип экзамена не найден")
    exam_date = datetime.strptime(exam_data.date, '%Y-%m-%d')
    if exam_date > datetime.now():
        raise HTTPException(status_code=400, detail="Нельзя выбрать дату из будущего")
    formatted_date = exam_date.strftime('%d.%m.%Y')
    conn.execute("""
        INSERT INTO exams (user_id, name, date, duration, notification_sent, month_notification_sent,
                          week_notification_sent, exam_day_notification_sent, end_day_notification_sent)
        VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0)
    """, (current_user["user_id"], exam_type['name'], formatted_date, str(exam_type['duration'])))
    conn.commit()
    conn.close()
    return {"message": "Экзамен успешно добавлен", "success": True}

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
    today = datetime.now()
    
    for row in cursor:
        is_active = False
        if row['end_date'] is None or row['end_date'] == '':
            is_active = True
        else:
            try:
                end_date = datetime.strptime(row['end_date'], '%d.%m.%Y')
                if end_date >= today:
                    is_active = True
            except:
                pass
        
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
        
        return {"message": "Больничный закрыт", "success": True}
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
        
        return {"message": "Больничный продлен", "success": True}
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
            is_active = False
            if row['end_date'] is None or row['end_date'] == '':
                is_active = True
            else:
                try:
                    end_date = datetime.strptime(row['end_date'], '%d.%m.%Y')
                    if end_date >= today:
                        is_active = True
                except:
                    pass
            
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
    if os.path.exists('uaiss.html'):
        return FileResponse('uaiss.html')
    return {"message": "UAISS Web API работает. Добавьте файл uaiss.html"}

# ============= ПЛАНИРОВЩИК ДЛЯ ЕЖЕДНЕВНОЙ ОТПРАВКИ В 09:00 =============
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

# Глобальная переменная для планировщика
scheduler = None

def start_scheduler():
    """Запуск планировщика уведомлений - работает в фоне независимо от запросов"""
    global scheduler
    scheduler = BackgroundScheduler()
    
    # Ежедневно в 09:00
    scheduler.add_job(
        func=check_and_send_notifications_sync,
        trigger=CronTrigger(hour=9, minute=0),
        id='daily_notifications_9am',
        name='Ежедневная отправка уведомлений в 09:00',
        replace_existing=True
    )
    
    scheduler.start()
    print("📅 Планировщик уведомлений ЗАПУЩЕН!")
    print("   • Отправка КАЖДЫЙ ДЕНЬ в 09:00")
    print("   • Работает в фоне, не зависит от активности пользователей")
    
    # Регистрируем остановку планировщика при завершении приложения
    atexit.register(lambda: scheduler.shutdown() if scheduler else None)
    
    return scheduler

# Автоматический запуск планировщика при старте приложения
print("🚀 Инициализация UAISS Web API...")
start_scheduler()

if __name__ == "__main__":
    import uvicorn
    check_and_fix_database()
    print("=" * 50)
    print(" UAISS Web API Сервер запущен!")
    print(" http://localhost:8000")
    print(" Документация: http://localhost:8000/docs")
    print("=" * 50)
    print("\n📧 Email уведомления:")
    print("   • Планировщик автоматически отправляет уведомления каждый день в 09:00")
    print("   • Отправка происходит независимо от активности пользователей")
    print("   • Для ручной отправки: POST /api/v1/notifications/send (только админ)")
    print("\nТестовые учетные записи:")
    print("👤 Сотрудник: user@uaiss.ru / 123456")
    print("👑 Администратор: admin@uaiss.ru / admin123")
    print()
    uvicorn.run(app, host="127.0.0.1", port=8000)