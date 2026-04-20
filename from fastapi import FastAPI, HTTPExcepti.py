from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import hashlib
from datetime import datetime, timedelta

app = FastAPI()

# Разрешаем все запросы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель для логина
class LoginRequest(BaseModel):
    login: str
    password: str

# Функция хэширования
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Функция подключения к БД
def get_db():
    conn = sqlite3.connect('exams.db')
    conn.row_factory = sqlite3.Row
    return conn

# ============= ЭНДПОИНТ ЛОГИНА (упрощенный) =============
@app.post("/api/v1/auth/login")
async def login(login_data: LoginRequest):
    print(f"Попытка входа: {login_data.login}")
    
    try:
        conn = get_db()
        cursor = conn.execute(
            "SELECT user_id, full_name, login, password_hash, role FROM users WHERE login = ?",
            (login_data.login,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            print(f"Пользователь не найден: {login_data.login}")
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        # Проверяем пароль
        if user['password_hash'] != hash_password(login_data.password):
            print(f"Неверный пароль для: {login_data.login}")
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        print(f"Успешный вход: {user['full_name']}")
        
        # Простой токен (без JWT для теста)
        return {
            "access_token": f"test_token_{user['user_id']}",
            "token_type": "bearer",
            "user_id": user['user_id'],
            "full_name": user['full_name'],
            "role": user['role']
        }
    
    except Exception as e:
        print(f"Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= ПРОСТОЙ ЭНДПОИНТ ДЛЯ ПРОВЕРКИ =============
@app.get("/api/v1/exam-types")
async def get_exam_types():
    conn = get_db()
    cursor = conn.execute("SELECT id, name, duration, emoji FROM exam_types")
    types = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return types

# ============= ГЛАВНАЯ =============
@app.get("/")
async def root():
    return {"message": "Сервер работает! Перейдите на /docs для тестирования"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("🚀 ПРОСТОЙ СЕРВЕР ЗАПУЩЕН!")
    print("📱 Swagger: http://localhost:8000/docs")
    print("="*50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)