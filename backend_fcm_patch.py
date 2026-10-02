# ══════════════════════════════════════════════════════════════════════
# ИНСТРУКЦИЯ: Добавьте эти изменения в test.py на сервере
# ══════════════════════════════════════════════════════════════════════

# ── 1. ДОБАВИТЬ в блок импортов (после строки "from threading import Thread") ──
import firebase_admin
from firebase_admin import credentials, messaging

# ── 2. ДОБАВИТЬ после строки "app = FastAPI(...)" ─────────────────────────────
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK инициализирован")
except Exception as e:
    print(f"⚠️ Firebase не инициализирован: {e}")

# ── 3. ДОБАВИТЬ в функцию check_and_fix_database() — перед conn.close() ───────
#    cursor.execute("""
#        CREATE TABLE IF NOT EXISTS fcm_tokens (
#            id INTEGER PRIMARY KEY AUTOINCREMENT,
#            user_id TEXT NOT NULL,
#            token  TEXT NOT NULL UNIQUE,
#            updated_at TEXT DEFAULT (datetime('now'))
#        )
#    """)
#    conn.commit()

# ── 4. НОВЫЕ ФУНКЦИИ — добавить после функции send_email_async() ──────────────

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
        return True
    except Exception as e:
        print(f"❌ FCM ошибка: {e}")
        return False

def send_push_to_user(user_id: str, title: str, body: str, data: dict = None):
    conn = sqlite3.connect(CONFIG['database']['path'])
    try:
        rows = conn.execute(
            "SELECT token FROM fcm_tokens WHERE user_id = ?", (user_id,)
        ).fetchall()
    finally:
        conn.close()
    for (token,) in rows:
        send_fcm_push(token, title, body, data)

# ── 5. НОВЫЕ ENDPOINTS — добавить после /api/v1/auth/update-email ─────────────

# @app.post("/api/v1/fcm-token")
# async def save_fcm_token(request: Request, current_user=Depends(get_current_user)):
#     body = await request.json()
#     token = body.get("token", "").strip()
#     if not token:
#         raise HTTPException(status_code=400, detail="Token required")
#     conn = get_db()
#     try:
#         conn.execute(
#             """INSERT INTO fcm_tokens (user_id, token, updated_at)
#                VALUES (?, ?, datetime('now'))
#                ON CONFLICT(token) DO UPDATE SET user_id=excluded.user_id, updated_at=excluded.updated_at""",
#             (current_user["user_id"], token)
#         )
#         conn.commit()
#     finally:
#         conn.close()
#     return {"status": "ok"}

# @app.post("/api/v1/notifications/test-push")
# async def test_push_notification(current_user=Depends(get_current_user)):
#     """Отправляет тестовый FCM push через 30 секунд."""
#     import time
#     def _delayed_push():
#         time.sleep(30)
#         send_push_to_user(
#             current_user["user_id"],
#             "🔔 Тест UAISS",
#             "FCM работает! Уведомления придут даже при закрытом приложении.",
#             {"view": "exams"}
#         )
#     thread = Thread(target=_delayed_push)
#     thread.daemon = True
#     thread.start()
#     return {"status": "ok", "message": "Push придёт через 30 секунд"}

# ── 6. ИЗМЕНИТЬ check_and_send_notifications_sync() ───────────────────────────
# После строки:
#   if send_email(row['email'], subject, body):
#       cursor.execute("UPDATE exams SET last_notification_day = ?...", ...)
#       notifications_sent += 1
#
# ДОБАВИТЬ:
#   send_push_to_user(
#       row['user_id'],
#       f"⚠️ Экзамен истекает через {nd} дней",
#       f"{row['exam_name']} — до {end_date.strftime('%d.%m.%Y')}",
#       {"view": "exams"}
#   )
#
# И аналогично для просроченных — после send_email для NOTIFY_EXPIRED:
#   send_push_to_user(
#       row['user_id'],
#       "🔴 Экзамен просрочен!",
#       f"{row['exam_name']} просрочен на {abs(days_left)} дней",
#       {"view": "exams"}
#   )

# ── 7. ДОБАВИТЬ в requirements.txt ────────────────────────────────────────────
# firebase-admin==6.5.0
