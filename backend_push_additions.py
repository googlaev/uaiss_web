"""
Дополнения к бэкенду (test.py) для поддержки FCM push-уведомлений.
Добавьте этот код в ваш основной файл test.py на сервере.

Зависимости (добавить в requirements.txt):
    firebase-admin==6.5.0
"""

# ── 1. ИМПОРТЫ (добавить в начало test.py) ──────────────────────────
import firebase_admin
from firebase_admin import credentials, messaging

# ── 2. ИНИЦИАЛИЗАЦИЯ FIREBASE (добавить после загрузки CONFIG) ───────
# Скачайте serviceAccountKey.json из Firebase Console:
# Project Settings → Service Accounts → Generate new private key
firebase_app = None
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_app = firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK инициализирован")
except Exception as e:
    print(f"⚠️ Firebase не инициализирован: {e}")

# ── 3. СОЗДАНИЕ ТАБЛИЦЫ FCM ТОКЕНОВ (добавить в init_db()) ──────────
CREATE_FCM_TABLE = """
CREATE TABLE IF NOT EXISTS fcm_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
"""
# В функции init_db() добавьте: cursor.execute(CREATE_FCM_TABLE)

# ── 4. ENDPOINT: сохранить FCM-токен ────────────────────────────────
# Добавить в FastAPI приложение:
#
# @app.post("/api/v1/fcm-token")
# async def save_fcm_token(request: Request, current_user=Depends(get_current_user)):
#     body = await request.json()
#     token = body.get("token")
#     if not token:
#         raise HTTPException(status_code=400, detail="Token required")
#     conn = sqlite3.connect(CONFIG['database']['path'])
#     try:
#         conn.execute(
#             "INSERT OR REPLACE INTO fcm_tokens (user_id, token) VALUES (?, ?)",
#             (current_user["user_id"], token)
#         )
#         conn.commit()
#     finally:
#         conn.close()
#     return {"status": "ok"}

# ── 5. ФУНКЦИЯ ОТПРАВКИ FCM PUSH ─────────────────────────────────────
def send_push_notification(token: str, title: str, body: str, data: dict = None):
    """Отправляет push-уведомление на конкретный FCM-токен."""
    if not firebase_app:
        return False
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="uaiss_exams"
                )
            )
        )
        messaging.send(message)
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки FCM: {e}")
        return False


def send_push_to_user(user_id: str, title: str, body: str, data: dict = None):
    """Отправляет push всем устройствам пользователя."""
    conn = sqlite3.connect(CONFIG['database']['path'])
    try:
        tokens = conn.execute(
            "SELECT token FROM fcm_tokens WHERE user_id = ?", (user_id,)
        ).fetchall()
    finally:
        conn.close()

    sent = 0
    for (token,) in tokens:
        if send_push_notification(token, title, body, data):
            sent += 1
    return sent


# ── 6. ИНТЕГРАЦИЯ В check_and_send_notifications_sync() ──────────────
# Найдите в вашем коде строки где отправляется email и ПОСЛЕ них добавьте:
#
# # Push-уведомление на телефон
# send_push_to_user(
#     user_id=row['user_id'],
#     title="⚠️ Истекает экзамен",
#     body=f"{row['exam_name']} истекает через {nd} дней ({end_date.strftime('%d.%m.%Y')})",
#     data={"view": "exams"}
# )
#
# И для просроченных:
# send_push_to_user(
#     user_id=row['user_id'],
#     title="🔴 Экзамен просрочен!",
#     body=f"{row['exam_name']} просрочен на {abs(days_left)} дней",
#     data={"view": "exams"}
# )
