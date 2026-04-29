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
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'user@uaiss.ru'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (full_name, login, password_hash, role) VALUES (?, ?, ?, ?)",
                       ("Алексей Смирнов", "user@uaiss.ru", hash_password("123456"), "employee"))
        print("✅ Добавлен: user@uaiss.ru / 123456")
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE login = 'admin@uaiss.ru'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (full_name, login, password_hash, role) VALUES (?, ?, ?, ?)",
                       ("Екатерина Морозова", "admin@uaiss.ru", hash_password("admin123"), "admin"))
        print("✅ Добавлен: admin@uaiss.ru / admin123")
    
    cursor.execute("SELECT user_id, full_name FROM users WHERE login IS NULL")
    users_without_login = cursor.fetchall()
    for user in users_without_login:
        name_parts = user[1].split()
        login = f"{name_parts[0].lower() if name_parts else f'user_{user[0]}'}@uaiss.ru"
        cursor.execute("UPDATE users SET login = ?, password_hash = ?, role = 'employee' WHERE user_id = ?",
                       (login, hash_password("123456"), user[0]))
        print(f"✅ Обновлен: {user[1]} -> {login} / 123456")
    
    conn.commit()
    conn.close()
    print("\n✅ База данных готова к работе!\n")
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
    """Проверяет, активен ли статус (дата окончания не наступила)"""
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

@app.get("/api/v1/exam-types")
async def get_exam_types():
    conn = get_db()
    cursor = conn.execute("SELECT id, name, duration, emoji FROM exam_types ORDER BY name")
    types = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return types

@app.get("/api/v1/status/my")
async def get_my_status(current_user=Depends(get_current_user)):
    """Возвращает статусы пользователя с правильным определением активного (с учетом даты окончания)"""
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
        # Статус активен если:
        # 1. Нет даты окончания (открытый статус)
        # 2. ИЛИ дата окончания есть, но еще не наступила (>= сегодня)
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
            
            # Определяем тип статуса
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

if __name__ == "__main__":
    import uvicorn
    check_and_fix_database()
    print("=" * 50)
    print(" UAISS Web API Сервер запущен!")
    print(" http://localhost:8000")
    print(" Документация: http://localhost:8000/docs")
    print("=" * 50)
    print("\nТестовые учетные записи:")
    print("Сотрудник: user@uaiss.ru / 123456")
    print("Администратор: admin@uaiss.ru / admin123")
    print()
    uvicorn.run(app, host="127.0.0.1", port=8000)