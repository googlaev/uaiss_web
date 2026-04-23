from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime, timedelta
import hashlib
import jwt
import secrets
import os

#экземпляр FastAPI
app = FastAPI(title="UAISS Web API", version="1.0.0")

# шифр
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"

# CORS для браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#извлечение токена из заголовка 
security = HTTPBearer()

#модели данных 
class LoginRequest(BaseModel):
    login: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    full_name: str
    role: str

class ExamAdd(BaseModel):
    exam_type_id: int
    date: str

class StatusAdd(BaseModel):
    status: str
    start_date: str
    end_date: Optional[str] = None

#работа с БД
def check_and_fix_database():
    """Проверяет и добавляет недостающие колонки в БД"""
    print("\n Проверка структуры базы данных...")
    
    conn = sqlite3.connect('exams.db')
    cursor = conn.cursor()
    
    # проверяет наличие таблицы users
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("❌ Таблица users не найдена!")
        return False
    
    # получаем список существующих колонок в таблице users
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f" Существующие колонки: {columns}")
    
    # добавляем недостающие колонки 
    if 'login' not in columns:
        print("➕ Добавляем колонку 'login'...")
        cursor.execute("ALTER TABLE users ADD COLUMN login TEXT")
        print("✅ Колонка login добавлена")
    
    if 'password_hash' not in columns:
        print("➕ Добавляем колонку 'password_hash'...")
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        print("✅ Колонка password_hash добавлена")
    
    if 'role' not in columns:
        print("➕ Добавляем колонку 'role'...")
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'employee'")
        print("✅ Колонка role добавлена")
    
    # функция хэширования
    def hash_password(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()
    
    # добавляем тестовых пользователей
    print("\n👤 Проверка тестовых пользователей...")
    
    # добавляем сотрудника
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'user@uaiss.ru'")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (full_name, login, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ("Алексей Смирнов", "user@uaiss.ru", hash_password("123456"), "employee"))
        print("✅ Добавлен: user@uaiss.ru / 123456")
    
    # добавляем администратора
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'admin@uaiss.ru'")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (full_name, login, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ("Екатерина Морозова", "admin@uaiss.ru", hash_password("admin123"), "admin"))
        print("✅ Добавлен: admin@uaiss.ru / admin123")
    
    # обновляем существующих пользователей (у кого нет логина)
    cursor.execute("SELECT user_id, full_name FROM users WHERE login IS NULL")
    users_without_login = cursor.fetchall()
    
    for user in users_without_login:
        name_parts = user[1].split()
        if name_parts:
            login = name_parts[0].lower() + "@uaiss.ru"
        else:
            login = f"user_{user[0]}@uaiss.ru"
        
        cursor.execute('''
            UPDATE users SET login = ?, password_hash = ?, role = 'employee'
            WHERE user_id = ?
        ''', (login, hash_password("123456"), user[0]))
        print(f"✅ Обновлен: {user[1]} -> {login} / 123456")
    
    conn.commit()
    
    # итоговый список пользователей
    print("\n📋 Пользователи в БД:")
    cursor.execute("SELECT user_id, full_name, login, role FROM users")
    users = cursor.fetchall()
    for user in users:
        print(f"   ID: {user[0]}, Имя: {user[1]}, Логин: {user[2]}, Роль: {user[3]}")
    
    conn.close()
    print("\n✅ База данных готова к работе!\n")
    return True

# БД
def get_db():
    conn = sqlite3.connect('exams.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed

def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
#проверка и декодирование пользователя
def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Неверный токен")

#текущий пользователь
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    return {"user_id": int(payload["sub"]), "role": payload["role"]}
#API эндпоинты 
# авторизация
@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(auth_data: LoginRequest):
    """POST /auth/login - Вход по логину и паролю"""
    conn = get_db()
    
    try:
        # Ищем пользователя
        cursor = conn.execute(
            "SELECT user_id, full_name, login, password_hash, role FROM users WHERE login = ?",
            (auth_data.login,)
        )
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        if not verify_password(auth_data.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        # Создаем JWT токен
        access_token = create_token(user['user_id'], user['role'])
        
        return LoginResponse(
            access_token=access_token,
            user_id=user['user_id'],
            full_name=user['full_name'],
            role=user['role']
        )
    finally:
        conn.close()

@app.post("/api/v1/auth/logout")
async def logout(current_user=Depends(get_current_user)):
    return {"message": "Успешный выход"}

@app.get("/api/v1/auth/me")
async def get_me(current_user=Depends(get_current_user)):
    conn = get_db()
    cursor = conn.execute(
        "SELECT user_id, full_name, login, role FROM users WHERE user_id = ?",
        (current_user["user_id"],)
    )
    user = cursor.fetchone()
    conn.close()
    return dict(user)

#экзамены
@app.get("/api/v1/exams/my")
async def get_my_exams(current_user=Depends(get_current_user)):
    conn = get_db()
    
    cursor = conn.execute("""
        SELECT e.id, e.name, e.date, e.duration,
               et.emoji, et.duration as duration_months
        FROM exams e
        LEFT JOIN exam_types et ON e.name = et.name
        WHERE e.user_id = ?
        ORDER BY e.date DESC
    """, (current_user["user_id"],))
    
    exams = []
    today = datetime.now()
    
    for row in cursor:
        try:
            exam_date = datetime.strptime(row['date'], '%d.%m.%Y')
            duration_months = int(row['duration_months']) if row['duration_months'] else int(row['duration'])
            end_date = exam_date + timedelta(days=duration_months * 30)
            days_left = (end_date - today).days
            
            if days_left < 0:
                status = "Просрочен"
                status_color = "danger"
            elif days_left <= 30:
                status = "Истекает"
                status_color = "warning"
            else:
                status = "Действующий"
                status_color = "success"
            
            exams.append({
                "id": row['id'],
                "type": row['name'],
                "emoji": row['emoji'] or "📚",
                "date": row['date'],
                "expires_at": end_date.strftime('%d.%m.%Y'),
                "days_left": days_left,
                "status": status,
                "status_color": status_color
            })
        except Exception as e:
            print(f"Ошибка обработки экзамена: {e}")
            continue
    
    conn.close()
    return exams

@app.post("/api/v1/exams")
async def add_exam(exam_data: ExamAdd, current_user=Depends(get_current_user)):
    conn = get_db()
    
    cursor = conn.execute(
        "SELECT name, duration FROM exam_types WHERE id = ?",
        (exam_data.exam_type_id,)
    )
    exam_type = cursor.fetchone()
    
    if not exam_type:
        raise HTTPException(status_code=404, detail="Тип экзамена не найден")
    
    exam_date = datetime.strptime(exam_data.date, '%Y-%m-%d')
    if exam_date > datetime.now():
        raise HTTPException(status_code=400, detail="Нельзя выбрать дату из будущего")
    
    formatted_date = exam_date.strftime('%d.%m.%Y')
    
    conn.execute("""
        INSERT INTO exams (user_id, name, date, duration, 
                          notification_sent, month_notification_sent, 
                          week_notification_sent, exam_day_notification_sent, 
                          end_day_notification_sent)
        VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0)
    """, (current_user["user_id"], exam_type['name'], formatted_date, str(exam_type['duration'])))
    
    conn.commit()
    conn.close()
    return {"message": "Экзамен успешно добавлен", "success": True}

@app.delete("/api/v1/exams/{exam_id}")
async def delete_exam(exam_id: int, current_user=Depends(get_current_user)):
    conn = get_db()
    
    if current_user["role"] == "admin":
        conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    else:
        conn.execute(
            "DELETE FROM exams WHERE id = ? AND user_id = ?",
            (exam_id, current_user["user_id"])
        )
    
    conn.commit()
    conn.close()
    return {"message": "Экзамен удален"}

@app.get("/api/v1/exams/expiring")
async def get_expiring_exams(current_user=Depends(get_current_user)):
    conn = get_db()
    
    cursor = conn.execute("""
        SELECT u.full_name, e.name, e.date, e.duration,
               et.duration as duration_months
        FROM exams e
        JOIN users u ON e.user_id = u.user_id
        LEFT JOIN exam_types et ON e.name = et.name
        ORDER BY e.date DESC
    """)
    
    expiring = []
    today = datetime.now()
    month_end = today + timedelta(days=30)
    
    for row in cursor:
        try:
            exam_date = datetime.strptime(row['date'], '%d.%m.%Y')
            duration_months = int(row['duration_months']) if row['duration_months'] else int(row['duration'])
            end_date = exam_date + timedelta(days=duration_months * 30)
            
            if today <= end_date <= month_end:
                days_left = (end_date - today).days
                expiring.append({
                    "employee_name": row['full_name'],
                    "exam_type": row['name'],
                    "expires_at": end_date.strftime('%d.%m.%Y'),
                    "days_left": days_left
                })
        except Exception as e:
            print(f"Ошибка: {e}")
            continue
    
    conn.close()
    return expiring

@app.get("/api/v1/exam-types")
async def get_exam_types():
    conn = get_db()
    cursor = conn.execute("SELECT id, name, duration, emoji FROM exam_types ORDER BY name")
    types = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return types

#статусы
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
        statuses.append({
            "id": row['id'],
            "status": row['status'],
            "start_date": row['start_date'],
            "end_date": row['end_date'] if row['end_date'] else None,
            "is_active": row['end_date'] is None or row['end_date'] == ''
        })
    
    conn.close()
    return statuses

@app.post("/api/v1/status")
async def add_status(status_data: StatusAdd, current_user=Depends(get_current_user)):
    conn = get_db()
    end_date = status_data.end_date if status_data.end_date else None
    
    conn.execute("""
        INSERT INTO user_status (user_id, status, start_date, end_date)
        VALUES (?, ?, ?, ?)
    """, (current_user["user_id"], status_data.status, status_data.start_date, end_date))
    
    conn.commit()
    conn.close()
    return {"message": "Статус успешно добавлен", "success": True}

@app.patch("/api/v1/status/{status_id}/close")
async def close_status(status_id: int, current_user=Depends(get_current_user)):
    conn = get_db()
    today = datetime.now().strftime('%d.%m.%Y')
    
    if current_user["role"] == "admin":
        conn.execute("UPDATE user_status SET end_date = ? WHERE id = ?", (today, status_id))
    else:
        conn.execute("UPDATE user_status SET end_date = ? WHERE id = ? AND user_id = ?", 
                     (today, status_id, current_user["user_id"]))
    
    conn.commit()
    conn.close()
    return {"message": "Больничный закрыт", "success": True}

@app.delete("/api/v1/status/last")
async def delete_last_status(current_user=Depends(get_current_user)):
    conn = get_db()
    
    cursor = conn.execute("""
        SELECT id FROM user_status 
        WHERE user_id = ? 
        ORDER BY start_date DESC LIMIT 1
    """, (current_user["user_id"],))
    
    last = cursor.fetchone()
    if last:
        conn.execute("DELETE FROM user_status WHERE id = ?", (last['id'],))
        conn.commit()
    
    conn.close()
    return {"message": "Последний статус удален", "success": True}

@app.get("/api/v1/status/month")
async def get_month_statuses(current_user=Depends(get_current_user)):
    conn = get_db()
    today = datetime.now()
    month_start = today.replace(day=1).strftime('%d.%m.%Y')
    month_end = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    month_end_str = month_end.strftime('%d.%m.%Y')
    
    cursor = conn.execute("""
        SELECT u.user_id, u.full_name, us.status, us.start_date, us.end_date
        FROM users u
        LEFT JOIN user_status us ON u.user_id = us.user_id
        WHERE us.start_date <= ? AND (us.end_date >= ? OR us.end_date IS NULL)
        ORDER BY u.full_name
    """, (month_end_str, month_start))
    
    statuses = []
    for row in cursor:
        statuses.append({
            "user_id": row['user_id'],
            "full_name": row['full_name'],
            "status": row['status'] if row['status'] else "На рабочем месте 🟢",
            "period": f"{row['start_date']} - {row['end_date'] if row['end_date'] else 'по настоящее время'}"
        })
    
    conn.close()
    return statuses

@app.get("/api/v1/status/current")
async def get_current_status_stats(current_user=Depends(get_current_user)):
    conn = get_db()
    
    cursor = conn.execute("SELECT user_id, full_name FROM users")
    users = cursor.fetchall()
    
    stats = {
        "total": len(users),
        "working": 0,
        "sick": 0,
        "trip": 0,
        "vacation": 0,
        "employees": []
    }
    
    for user in users:
        cursor = conn.execute("""
            SELECT status FROM user_status 
            WHERE user_id = ? AND (end_date IS NULL OR end_date = '')
            ORDER BY start_date DESC LIMIT 1
        """, (user['user_id'],))
        
        status_row = cursor.fetchone()
        
        if status_row:
            status = status_row['status']
            if "Больничный" in status:
                stats["sick"] += 1
                status_type = "sick"
            elif "Командировка" in status:
                stats["trip"] += 1
                status_type = "trip"
            elif "Отпуск" in status:
                stats["vacation"] += 1
                status_type = "vacation"
            else:
                stats["working"] += 1
                status_type = "working"
        else:
            stats["working"] += 1
            status_type = "working"
        
        stats["employees"].append({
            "id": user['user_id'],
            "name": user['full_name'],
            "status_type": status_type
        })
    
    if stats["total"] > 0:
        stats["working_percent"] = round(stats["working"] / stats["total"] * 100)
        stats["sick_percent"] = round(stats["sick"] / stats["total"] * 100)
        stats["trip_percent"] = round(stats["trip"] / stats["total"] * 100)
        stats["vacation_percent"] = round(stats["vacation"] / stats["total"] * 100)
    
    conn.close()
    return stats

#главная стр
@app.get("/")
async def root():
    if os.path.exists('uaiss.html'):
        return FileResponse('uaiss.html')
    return {"message": "UAISS Web API работает. Добавьте файл uaiss.html"}


if __name__ == "__main__":
    import uvicorn
    
    # проверяем и исправляем БД перед запуском
    check_and_fix_database()
    
    
    print("UAISS Web API Сервер запущен!")
    print("Интерфейс: http://localhost:8000")
    print("Документация API: http://localhost:8000/docs")
    print("="*60)
    print("\nТестовые учетные записи:")
    print("Сотрудник: user@uaiss.ru / 123456")
    print("Администратор: admin@uaiss.ru / admin123")
    print("\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)