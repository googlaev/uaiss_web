import time
import requests

TOKEN = "f9LHodD0cOJfx7ZUhEuV7vZRGOsdcTSkD-0Imc9rhWC_oCakYJCGD1fnIyGCvQMthYUMpaAI_2dFXuz0PdM2"
BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

QUESTIONS = [
    {
        "text": "❓ Вопрос 1 из 5\n\nЧто выведет этот код?\n\nprint(type([]))",
        "options": ["<class 'list'>", "<class 'tuple'>", "<class 'dict'>", "<class 'set'>"],
        "correct": 0,
    },
    {
        "text": "❓ Вопрос 2 из 5\n\nКак правильно объявить функцию в Python?",
        "options": ["function myFunc():", "def myFunc():", "fun myFunc():", "func myFunc():"],
        "correct": 1,
    },
    {
        "text": "❓ Вопрос 3 из 5\n\nЧто выведет этот код?\n\nprint(2 ** 3)",
        "options": ["6", "8", "9", "23"],
        "correct": 1,
    },
    {
        "text": "❓ Вопрос 4 из 5\n\nКакой метод добавляет элемент в конец списка?",
        "options": ["list.add(x)", "list.insert(x)", "list.append(x)", "list.push(x)"],
        "correct": 2,
    },
    {
        "text": "❓ Вопрос 5 из 5\n\nЧто выведет этот код?\n\nprint('abc'[::-1])",
        "options": ["abc", "cba", "c", "Ошибка"],
        "correct": 1,
    },
]

LABELS = ["🅰", "🅱", "🅲", "🅳"]

# user_id -> {"q_idx": int, "score": int, "mid": str, "chat_id": int}
sessions: dict = {}


# ── API ──────────────────────────────────────────────────────────────────────

def get_updates(marker=None):
    params = {"timeout": 30}
    if marker is not None:
        params["marker"] = marker
    try:
        r = requests.get(f"{BASE_URL}/updates", params=params, headers=HEADERS, timeout=35)
        if r.status_code == 401:
            print("\n❌ Токен недействителен. Проверь TOKEN.")
            raise SystemExit(1)
        r.raise_for_status()
        return r.json()
    except SystemExit:
        raise
    except Exception as e:
        print(f"[get_updates] {e}")
        time.sleep(5)
        return {"updates": []}


def send_message(chat_id, text, buttons=None):
    payload = {"text": text}
    if buttons:
        payload["attachments"] = [
            {"type": "inline_keyboard", "payload": {"buttons": buttons}}
        ]
    try:
        r = requests.post(
            f"{BASE_URL}/messages",
            params={"chat_id": chat_id},
            headers=HEADERS,
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("body", {}).get("mid")
    except Exception as e:
        print(f"[send_message] {e}")
        return None


def edit_message(mid, text, buttons=None):
    payload = {"text": text}
    if buttons:
        payload["attachments"] = [
            {"type": "inline_keyboard", "payload": {"buttons": buttons}}
        ]
    else:
        payload["attachments"] = []
    try:
        r = requests.put(
            f"{BASE_URL}/messages",
            params={"message_id": mid},
            headers=HEADERS,
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        print(f"[edit_message] {e}")


def answer_callback(callback_id: str):
    try:
        requests.post(
            f"{BASE_URL}/answers",
            params={"callback_id": callback_id},
            headers=HEADERS,
            json={},
            timeout=10,
        )
    except Exception as e:
        print(f"[answer_callback] {e}")


# ── Quiz ─────────────────────────────────────────────────────────────────────

def make_buttons(q_idx: int, options: list) -> list:
    return [
        [{"type": "callback", "text": f"{LABELS[i]}  {opt}", "payload": f"ans:{q_idx}:{i}"}]
        for i, opt in enumerate(options)
    ]


def show_question(session: dict, q_idx: int, prefix: str = ""):
    q = QUESTIONS[q_idx]
    text = f"{prefix}\n\n{q['text']}" if prefix else q["text"]
    buttons = make_buttons(q_idx, q["options"])

    if session["mid"] is None:
        mid = send_message(session["chat_id"], text, buttons)
        session["mid"] = mid
    else:
        edit_message(session["mid"], text, buttons)


def start_button():
    return [[{"type": "message", "text": "🚀 Начать тест", "payload": "/start"}]]


def handle_start(chat_id, user_id):
    sessions[user_id] = {"q_idx": 0, "score": 0, "mid": None, "chat_id": chat_id}
    show_question(sessions[user_id], 0, prefix="🐍 Тест по Python — 5 вопросов. Поехали!")


def handle_callback(update: dict):
    cb = update.get("callback", {})
    callback_id = cb.get("callback_id")
    payload = cb.get("payload", "")
    user_id = cb.get("user", {}).get("user_id")
    chat_id = update.get("message", {}).get("recipient", {}).get("chat_id")

    answer_callback(callback_id)

    if not payload.startswith("ans:") or not user_id or not chat_id:
        return

    parts = payload.split(":")
    if len(parts) != 3:
        return
    q_idx, chosen = int(parts[1]), int(parts[2])

    session = sessions.get(user_id)
    if not session or session["q_idx"] != q_idx:
        return

    q = QUESTIONS[q_idx]
    correct = q["correct"]

    if chosen == correct:
        session["score"] += 1
        result_line = f"✅ Правильно!  {LABELS[correct]}  {q['options'][correct]}"
    else:
        result_line = (
            f"❌ Неверно!\n"
            f"Твой ответ:      {LABELS[chosen]}  {q['options'][chosen]}\n"
            f"Правильный:   {LABELS[correct]}  {q['options'][correct]}"
        )

    next_q = q_idx + 1
    session["q_idx"] = next_q

    if next_q < len(QUESTIONS):
        # Показываем результат, затем следующий вопрос в том же сообщении
        score_line = f"🎯 Счёт: {session['score']}/{next_q}"
        prefix = f"{result_line}\n\n{score_line}\n{'─' * 28}"
        time.sleep(0.3)
        show_question(session, next_q, prefix=prefix)
    else:
        # Финал
        score = session["score"]
        total = len(QUESTIONS)
        if score == total:
            emoji, comment = "🏆", "Отлично! Ты настоящий Python-мастер!"
        elif score >= 3:
            emoji, comment = "👍", "Хороший результат! Есть куда расти."
        else:
            emoji, comment = "📚", "Стоит повторить основы Python. Не сдавайся!"

        edit_message(
            session["mid"],
            f"{result_line}\n\n"
            f"{emoji} Тест завершён!\n\n"
            f"Результат: {score} / {total}\n\n"
            f"{comment}",
            buttons=start_button(),
        )
        del sessions[user_id]


def handle_message(update: dict):
    msg = update.get("message", {})
    body = msg.get("body", {}).get("text", "").strip()
    chat_id = msg.get("recipient", {}).get("chat_id")
    user_id = msg.get("sender", {}).get("user_id")

    if not chat_id or not user_id:
        return

    if body.startswith("/start"):
        handle_start(chat_id, user_id)
    elif user_id not in sessions:
        send_message(
            chat_id,
            "👋 Привет! Я бот для проверки знаний Python.\n\nНажми кнопку чтобы начать тест:",
            buttons=start_button(),
        )


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    print("Quiz bot started. Waiting for messages...")
    marker = None
    while True:
        data = get_updates(marker)
        new_marker = data.get("marker")
        if new_marker:
            marker = new_marker

        for upd in data.get("updates", []):
            upd_type = upd.get("update_type")
            try:
                if upd_type == "message_created":
                    handle_message(upd)
                elif upd_type == "message_callback":
                    handle_callback(upd)
            except Exception as e:
                print(f"[handler error] {e}")

        if not data.get("updates"):
            time.sleep(0.5)


if __name__ == "__main__":
    main()
