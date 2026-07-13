"""
Миграция: очищает exams.db и заполняет продакшн-данными из exams1.db.
Запускать на сервере: python migrate_prod.py
"""
import sqlite3, hashlib, json, os

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# --- данные из exams1.db ---
EXAM_TYPES = [
  {
    "id": 3009,
    "name": "А1",
    "duration": 60,
    "emoji": "🔬"
  },
  {
    "id": 3010,
    "name": "Б21",
    "duration": 60,
    "emoji": "📋"
  },
  {
    "id": 3011,
    "name": "Б26",
    "duration": 60,
    "emoji": "📊"
  },
  {
    "id": 3012,
    "name": "ОТ",
    "duration": 36,
    "emoji": "🦺"
  },
  {
    "id": 3013,
    "name": "ОТБ",
    "duration": 36,
    "emoji": "🛡️"
  },
  {
    "id": 3014,
    "name": "СИЗ",
    "duration": 36,
    "emoji": "🥽"
  },
  {
    "id": 3015,
    "name": "ПП",
    "duration": 36,
    "emoji": "🚒"
  },
  {
    "id": 3016,
    "name": "ЭБ",
    "duration": 12,
    "emoji": "💡"
  },
  {
    "id": 3017,
    "name": "ПТМ",
    "duration": 6,
    "emoji": "🔥"
  }
]

USERS = [
  {
    "user_id": 2,
    "telegram_id": 1244411217,
    "full_name": "Коваленко Александр Викторович",
    "login": "КАВ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 3,
    "telegram_id": 154046895,
    "full_name": "Гуляев Иван Павлович",
    "login": "ГИП",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "admin",
    "email": null
  },
  {
    "user_id": 4,
    "telegram_id": 246064916,
    "full_name": "Сабитов Ринат Шамильевич",
    "login": "СРШ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 5,
    "telegram_id": 507672585,
    "full_name": "Морозов Сергей Владимирович",
    "login": "МСВ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 6,
    "telegram_id": 954737973,
    "full_name": "Саитов Рамиль Морадамович",
    "login": "СРМ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 7,
    "telegram_id": 1814842541,
    "full_name": "Кушнирчук Евгений Викторович",
    "login": "КЕВ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 8,
    "telegram_id": 5873560218,
    "full_name": "Корепанов Сергей Александрович",
    "login": "КСА",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 9,
    "telegram_id": 5041927182,
    "full_name": "Ротарь Константин Сергеевич",
    "login": "РКС",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 10,
    "telegram_id": 235505230,
    "full_name": "Зырянов Евгений Викторович",
    "login": "ЗЕВ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 11,
    "telegram_id": 440524673,
    "full_name": "Жаров Борис Леонидович",
    "login": "ЖБЛ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 12,
    "telegram_id": 40524128,
    "full_name": "Борисов Сергей Викторович",
    "login": "БСВ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 13,
    "telegram_id": 1038868995,
    "full_name": "Дмитриев Игорь Геннадьевич",
    "login": "ДИГ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 14,
    "telegram_id": 454766053,
    "full_name": "Элис Иван Викторович",
    "login": "ЭИВ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 15,
    "telegram_id": 457266205,
    "full_name": "Архипов Марат Владимирович",
    "login": "АМВ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  },
  {
    "user_id": 123456,
    "telegram_id": 361625169,
    "full_name": "Ханмурзаев Айнутдин Зиявдинович",
    "login": "ХАЗ",
    "password_hash": "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
    "role": "employee",
    "email": null
  }
]

EXAMS = [
  {
    "id": 8,
    "user_id": 15,
    "name": "ПТМ",
    "date": "04.12.2025",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 9,
    "user_id": 15,
    "name": "А1",
    "date": "07.03.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 10,
    "user_id": 15,
    "name": "Б21",
    "date": "07.03.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 11,
    "user_id": 15,
    "name": "ОТ",
    "date": "12.08.2024",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 12,
    "user_id": 15,
    "name": "ПП",
    "date": "08.12.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 13,
    "user_id": 15,
    "name": "СИЗ",
    "date": "08.12.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 15,
    "user_id": 15,
    "name": "ЭБ",
    "date": "15.01.2026",
    "duration": "12",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 16,
    "user_id": 12,
    "name": "А1",
    "date": "10.11.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 17,
    "user_id": 12,
    "name": "Б21",
    "date": "10.11.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 18,
    "user_id": 12,
    "name": "ОТБ",
    "date": "29.09.2025",
    "duration": "36",
    "notification_sent": 1,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 19,
    "user_id": 12,
    "name": "ПП",
    "date": "26.09.2025",
    "duration": "36",
    "notification_sent": 1,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 20,
    "user_id": 12,
    "name": "СИЗ",
    "date": "06.10.2025",
    "duration": "36",
    "notification_sent": 1,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 21,
    "user_id": 12,
    "name": "ПТМ",
    "date": "09.12.2025",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 22,
    "user_id": 3,
    "name": "А1",
    "date": "16.02.2024",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 23,
    "user_id": 3,
    "name": "Б21",
    "date": "16.02.2024",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 24,
    "user_id": 3,
    "name": "ПТМ",
    "date": "10.03.2026",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 25,
    "user_id": 3,
    "name": "ОТБ",
    "date": "22.09.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 26,
    "user_id": 3,
    "name": "ПП",
    "date": "22.09.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 27,
    "user_id": 3,
    "name": "СИЗ",
    "date": "22.09.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 28,
    "user_id": 3,
    "name": "ЭБ",
    "date": "23.03.2026",
    "duration": "12",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 30,
    "user_id": 13,
    "name": "ОТ",
    "date": "11.08.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 31,
    "user_id": 13,
    "name": "ОТБ",
    "date": "11.08.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 32,
    "user_id": 13,
    "name": "ПП",
    "date": "11.08.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 33,
    "user_id": 13,
    "name": "СИЗ",
    "date": "11.08.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 34,
    "user_id": 13,
    "name": "А1",
    "date": "11.11.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 35,
    "user_id": 13,
    "name": "Б21",
    "date": "11.11.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 43,
    "user_id": 11,
    "name": "ОТБ",
    "date": "08.09.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 44,
    "user_id": 11,
    "name": "ПП",
    "date": "08.09.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 45,
    "user_id": 11,
    "name": "СИЗ",
    "date": "08.09.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 47,
    "user_id": 11,
    "name": "А1",
    "date": "18.09.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 48,
    "user_id": 11,
    "name": "Б21",
    "date": "18.09.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 49,
    "user_id": 11,
    "name": "ПТМ",
    "date": "19.12.2025",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 50,
    "user_id": 10,
    "name": "ОТБ",
    "date": "07.07.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 51,
    "user_id": 10,
    "name": "ПП",
    "date": "07.07.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 52,
    "user_id": 10,
    "name": "СИЗ",
    "date": "07.07.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 53,
    "user_id": 10,
    "name": "ПТМ",
    "date": "19.12.2025",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 54,
    "user_id": 10,
    "name": "ОТ",
    "date": "27.10.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 55,
    "user_id": 10,
    "name": "А1",
    "date": "28.06.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 56,
    "user_id": 10,
    "name": "Б21",
    "date": "28.06.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 57,
    "user_id": 2,
    "name": "А1",
    "date": "05.10.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 58,
    "user_id": 2,
    "name": "ОТБ",
    "date": "21.11.2025",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 59,
    "user_id": 2,
    "name": "ПП",
    "date": "05.12.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 60,
    "user_id": 2,
    "name": "СИЗ",
    "date": "17.11.2025",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 61,
    "user_id": 2,
    "name": "Б21",
    "date": "19.10.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 62,
    "user_id": 2,
    "name": "ЭБ",
    "date": "17.11.2025",
    "duration": "12",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 63,
    "user_id": 2,
    "name": "ПТМ",
    "date": "23.12.2025",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 65,
    "user_id": 8,
    "name": "ОТ",
    "date": "17.10.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 66,
    "user_id": 8,
    "name": "А1",
    "date": "19.12.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 67,
    "user_id": 8,
    "name": "Б21",
    "date": "19.12.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 68,
    "user_id": 8,
    "name": "ОТБ",
    "date": "20.01.2024",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 69,
    "user_id": 8,
    "name": "ПП",
    "date": "11.12.2025",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 70,
    "user_id": 7,
    "name": "ЭБ",
    "date": "06.05.2026",
    "duration": "12",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 72,
    "user_id": 7,
    "name": "ПТМ",
    "date": "17.04.2026",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 73,
    "user_id": 7,
    "name": "Б26",
    "date": "16.02.2024",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 74,
    "user_id": 7,
    "name": "СИЗ",
    "date": "16.02.2024",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 75,
    "user_id": 7,
    "name": "ПП",
    "date": "22.01.2026",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 76,
    "user_id": 7,
    "name": "А1",
    "date": "22.02.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 77,
    "user_id": 7,
    "name": "Б21",
    "date": "22.02.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 78,
    "user_id": 7,
    "name": "ОТ",
    "date": "27.10.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 79,
    "user_id": 7,
    "name": "ОТБ",
    "date": "30.03.2024",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 80,
    "user_id": 5,
    "name": "А1",
    "date": "08.12.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 81,
    "user_id": 5,
    "name": "Б21",
    "date": "08.12.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 82,
    "user_id": 5,
    "name": "Б26",
    "date": "08.12.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 83,
    "user_id": 5,
    "name": "ОТБ",
    "date": "15.12.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 84,
    "user_id": 5,
    "name": "ПП",
    "date": "15.12.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 85,
    "user_id": 5,
    "name": "СИЗ",
    "date": "15.12.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 86,
    "user_id": 5,
    "name": "ПТМ",
    "date": "17.04.2026",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 87,
    "user_id": 5,
    "name": "ЭБ",
    "date": "27.01.2026",
    "duration": "12",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 88,
    "user_id": 9,
    "name": "ПТМ",
    "date": "27.04.2026",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 89,
    "user_id": 9,
    "name": "А1",
    "date": "20.03.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 90,
    "user_id": 9,
    "name": "Б21",
    "date": "20.03.2023",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 91,
    "user_id": 9,
    "name": "ОТБ",
    "date": "27.04.2026",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 92,
    "user_id": 9,
    "name": "ПП",
    "date": "27.04.2026",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 93,
    "user_id": 9,
    "name": "СИЗ",
    "date": "27.04.2026",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 94,
    "user_id": 4,
    "name": "ПТМ",
    "date": "23.03.2026",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 95,
    "user_id": 4,
    "name": "ОТБ",
    "date": "03.11.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 96,
    "user_id": 4,
    "name": "ПП",
    "date": "03.11.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 97,
    "user_id": 4,
    "name": "СИЗ",
    "date": "03.11.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 98,
    "user_id": 4,
    "name": "А1",
    "date": "16.02.2024",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 99,
    "user_id": 4,
    "name": "Б21",
    "date": "16.02.2024",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 100,
    "user_id": 4,
    "name": "ЭБ",
    "date": "23.03.2026",
    "duration": "12",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 101,
    "user_id": 14,
    "name": "ОТ",
    "date": "27.10.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 102,
    "user_id": 14,
    "name": "ОТБ",
    "date": "27.10.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 103,
    "user_id": 14,
    "name": "ПП",
    "date": "27.10.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 104,
    "user_id": 14,
    "name": "СИЗ",
    "date": "27.10.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 105,
    "user_id": 14,
    "name": "А1",
    "date": "28.09.2021",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 106,
    "user_id": 14,
    "name": "Б21",
    "date": "28.09.2021",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 107,
    "user_id": 6,
    "name": "А1",
    "date": "07.09.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 108,
    "user_id": 6,
    "name": "Б21",
    "date": "07.09.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 109,
    "user_id": 6,
    "name": "Б26",
    "date": "07.09.2022",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 110,
    "user_id": 6,
    "name": "ОТБ",
    "date": "21.11.2025",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 111,
    "user_id": 6,
    "name": "ПП",
    "date": "13.08.2025",
    "duration": "36",
    "notification_sent": 1,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 112,
    "user_id": 6,
    "name": "СИЗ",
    "date": "16.07.2025",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 113,
    "user_id": 10,
    "name": "ЭБ",
    "date": "27.01.2026",
    "duration": "12",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 114,
    "user_id": 12,
    "name": "ЭБ",
    "date": "28.01.2026",
    "duration": "12",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 115,
    "user_id": 13,
    "name": "ЭБ",
    "date": "27.01.2026",
    "duration": "12",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 116,
    "user_id": 6,
    "name": "ЭБ",
    "date": "17.11.2025",
    "duration": "12",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 117,
    "user_id": 6,
    "name": "ПТМ",
    "date": "22.04.2026",
    "duration": "6",
    "notification_sent": 1,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 118,
    "user_id": 9,
    "name": "ЭБ",
    "date": "03.07.2025",
    "duration": "12",
    "notification_sent": 1,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 119,
    "user_id": 11,
    "name": "ЭБ",
    "date": "09.09.2025",
    "duration": "12",
    "notification_sent": 1,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 120,
    "user_id": 123456,
    "name": "А1",
    "date": "20.06.2025",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 121,
    "user_id": 123456,
    "name": "Б21",
    "date": "20.06.2025",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 122,
    "user_id": 123456,
    "name": "Б26",
    "date": "20.06.2025",
    "duration": "60",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 123,
    "user_id": 123456,
    "name": "ПП",
    "date": "17.06.2025",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 124,
    "user_id": 123456,
    "name": "ПТМ",
    "date": "16.12.2025",
    "duration": "6",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 1,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 1
  },
  {
    "id": 125,
    "user_id": 123456,
    "name": "ЭБ",
    "date": "16.06.2025",
    "duration": "12",
    "notification_sent": 0,
    "month_notification_sent": 1,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 126,
    "user_id": 123456,
    "name": "ОТБ",
    "date": "17.06.2025",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 127,
    "user_id": 123456,
    "name": "СИЗ",
    "date": "16.06.2025",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  },
  {
    "id": 128,
    "user_id": 15,
    "name": "ОТБ",
    "date": "08.12.2023",
    "duration": "36",
    "notification_sent": 0,
    "month_notification_sent": 0,
    "week_notification_sent": 0,
    "exam_day_notification_sent": 0,
    "end_day_notification_sent": 0
  }
]

STATUSES = [
  {
    "id": 14,
    "user_id": 8,
    "status": "🏖️ Отпуск",
    "start_date": "09.01.2025",
    "end_date": "17.01.2025"
  },
  {
    "id": 16,
    "user_id": 4,
    "status": "🤒 Больничный",
    "start_date": "14.01.2025",
    "end_date": "17.01.2025"
  },
  {
    "id": 26,
    "user_id": 14,
    "status": "✈️ Командировка",
    "start_date": "20.01.2025",
    "end_date": "24.01.2025"
  },
  {
    "id": 40,
    "user_id": 7,
    "status": "✈️ Командировка",
    "start_date": "17.02.2025",
    "end_date": "21.02.2025"
  },
  {
    "id": 41,
    "user_id": 11,
    "status": "✈️ Командировка",
    "start_date": "03.02.2025",
    "end_date": "18.02.2025"
  },
  {
    "id": 42,
    "user_id": 5,
    "status": "✈️ Командировка",
    "start_date": "10.02.2025",
    "end_date": "25.02.2025"
  },
  {
    "id": 43,
    "user_id": 12,
    "status": "✈️ Командировка",
    "start_date": "18.02.2025",
    "end_date": "04.03.2025"
  },
  {
    "id": 45,
    "user_id": 9,
    "status": "✈️ Командировка",
    "start_date": "26.02.2025",
    "end_date": "07.03.2025"
  },
  {
    "id": 46,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "15.03.2025",
    "end_date": "25.03.2025"
  },
  {
    "id": 47,
    "user_id": 10,
    "status": "🏖️ Отпуск",
    "start_date": "24.03.2025",
    "end_date": "28.03.2025"
  },
  {
    "id": 51,
    "user_id": 11,
    "status": "🏖️ Отпуск",
    "start_date": "20.02.2025",
    "end_date": "21.02.2025"
  },
  {
    "id": 54,
    "user_id": 11,
    "status": "✈️ Командировка",
    "start_date": "16.03.2025",
    "end_date": "22.03.2025"
  },
  {
    "id": 55,
    "user_id": 5,
    "status": "🏖️ Отпуск",
    "start_date": "03.03.2025",
    "end_date": "07.03.2025"
  },
  {
    "id": 57,
    "user_id": 6,
    "status": "✈️ Командировка",
    "start_date": "09.02.2024",
    "end_date": "28.02.2025"
  },
  {
    "id": 58,
    "user_id": 6,
    "status": "🏖️ Отпуск",
    "start_date": "17.03.2025",
    "end_date": "21.03.2025"
  },
  {
    "id": 60,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "28.03.2025",
    "end_date": "28.03.2025"
  },
  {
    "id": 61,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "11.04.2025",
    "end_date": "11.04.2025"
  },
  {
    "id": 62,
    "user_id": 15,
    "status": "🏖️ Отпуск",
    "start_date": "03.03.2025",
    "end_date": "03.03.2025"
  },
  {
    "id": 63,
    "user_id": 15,
    "status": "🏖️ Отпуск",
    "start_date": "03.03.2025",
    "end_date": "10.03.2025"
  },
  {
    "id": 66,
    "user_id": 6,
    "status": "🏖️ Отпуск",
    "start_date": "29.08.2025",
    "end_date": "29.08.2025"
  },
  {
    "id": 67,
    "user_id": 6,
    "status": "🏖️ Отпуск",
    "start_date": "31.10.2025",
    "end_date": "31.10.2025"
  },
  {
    "id": 68,
    "user_id": 7,
    "status": "🏖️ Отпуск",
    "start_date": "17.03.2025",
    "end_date": "21.03.2025"
  },
  {
    "id": 69,
    "user_id": 10,
    "status": "🤒 Больничный",
    "start_date": "18.03.2025",
    "end_date": "21.03.2025"
  },
  {
    "id": 70,
    "user_id": 13,
    "status": "🏖️ Отпуск",
    "start_date": "17.04.2025",
    "end_date": "30.04.2025"
  },
  {
    "id": 75,
    "user_id": 11,
    "status": "🏖️ Отпуск",
    "start_date": "09.04.2025",
    "end_date": "15.04.2025"
  },
  {
    "id": 76,
    "user_id": 11,
    "status": "✈️ Командировка",
    "start_date": "16.04.2025",
    "end_date": "30.04.2025"
  },
  {
    "id": 77,
    "user_id": 10,
    "status": "✈️ Командировка",
    "start_date": "23.04.2025",
    "end_date": "27.04.2025"
  },
  {
    "id": 78,
    "user_id": 10,
    "status": "🏖️ Отпуск",
    "start_date": "28.04.2025",
    "end_date": "30.04.2025"
  },
  {
    "id": 79,
    "user_id": 3,
    "status": "🏖️ Отпуск",
    "start_date": "14.04.2025",
    "end_date": "18.04.2025"
  },
  {
    "id": 80,
    "user_id": 12,
    "status": "✈️ Командировка",
    "start_date": "12.05.2025",
    "end_date": "25.05.2025"
  },
  {
    "id": 83,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "26.05.2025",
    "end_date": "08.06.2025"
  },
  {
    "id": 84,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "28.04.2025",
    "end_date": "30.04.2025"
  },
  {
    "id": 85,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "05.05.2025",
    "end_date": "09.04.2025"
  },
  {
    "id": 86,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "28.04.2025",
    "end_date": "11.05.2025"
  },
  {
    "id": 87,
    "user_id": 5,
    "status": "🏖️ Отпуск",
    "start_date": "05.05.2025",
    "end_date": "07.05.2025"
  },
  {
    "id": 89,
    "user_id": 3,
    "status": "🤒 Больничный",
    "start_date": "06.05.2025",
    "end_date": "13.05.2025"
  },
  {
    "id": 90,
    "user_id": 6,
    "status": "✈️ Командировка",
    "start_date": "19.05.2025",
    "end_date": "31.05.2025"
  },
  {
    "id": 92,
    "user_id": 9,
    "status": "✈️ Командировка",
    "start_date": "25.05.2025",
    "end_date": "31.05.2025"
  },
  {
    "id": 93,
    "user_id": 10,
    "status": "🏖️ Отпуск",
    "start_date": "09.06.2025",
    "end_date": "11.06.2025"
  },
  {
    "id": 95,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "09.06.2025",
    "end_date": "11.06.2025"
  },
  {
    "id": 97,
    "user_id": 3,
    "status": "🏖️ Отпуск",
    "start_date": "09.06.2025",
    "end_date": "11.06.2025"
  },
  {
    "id": 98,
    "user_id": 7,
    "status": "🏖️ Отпуск",
    "start_date": "16.06.2025",
    "end_date": "27.06.2025"
  },
  {
    "id": 99,
    "user_id": 6,
    "status": "✈️ Командировка",
    "start_date": "12.06.2025",
    "end_date": "25.06.2025"
  },
  {
    "id": 102,
    "user_id": 9,
    "status": "✈️ Командировка",
    "start_date": "23.06.2025",
    "end_date": "02.07.2025"
  },
  {
    "id": 103,
    "user_id": 3,
    "status": "🏖️ Отпуск",
    "start_date": "23.06.2025",
    "end_date": "23.06.2025"
  },
  {
    "id": 104,
    "user_id": 4,
    "status": "🏖️ Отпуск",
    "start_date": "30.06.2025",
    "end_date": "13.07.2025"
  },
  {
    "id": 105,
    "user_id": 3,
    "status": "🏖️ Отпуск",
    "start_date": "30.06.2025",
    "end_date": "11.07.2025"
  },
  {
    "id": 106,
    "user_id": 10,
    "status": "🏖️ Отпуск",
    "start_date": "07.07.2025",
    "end_date": "25.07.2025"
  },
  {
    "id": 107,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "10.07.2025",
    "end_date": "11.07.2025"
  },
  {
    "id": 108,
    "user_id": 5,
    "status": "✈️ Командировка",
    "start_date": "07.07.2025",
    "end_date": "23.07.2025"
  },
  {
    "id": 109,
    "user_id": 6,
    "status": "✈️ Командировка",
    "start_date": "22.07.2025",
    "end_date": "02.08.2025"
  },
  {
    "id": 110,
    "user_id": 6,
    "status": "🏖️ Отпуск",
    "start_date": "14.07.2025",
    "end_date": "21.07.2025"
  },
  {
    "id": 111,
    "user_id": 6,
    "status": "🏖️ Отпуск",
    "start_date": "14.08.2025",
    "end_date": "29.08.2025"
  },
  {
    "id": 112,
    "user_id": 11,
    "status": "✈️ Командировка",
    "start_date": "14.07.2025",
    "end_date": "27.07.2025"
  },
  {
    "id": 113,
    "user_id": 11,
    "status": "🏖️ Отпуск",
    "start_date": "28.07.2025",
    "end_date": "12.08.2025"
  },
  {
    "id": 115,
    "user_id": 13,
    "status": "🏖️ Отпуск",
    "start_date": "14.07.2025",
    "end_date": "27.07.2025"
  },
  {
    "id": 116,
    "user_id": 5,
    "status": "🤒 Больничный",
    "start_date": "29.07.2025",
    "end_date": "05.08.2025"
  },
  {
    "id": 117,
    "user_id": 5,
    "status": "🏖️ Отпуск",
    "start_date": "04.08.2025",
    "end_date": "18.08.2025"
  },
  {
    "id": 118,
    "user_id": 15,
    "status": "🏖️ Отпуск",
    "start_date": "04.08.2025",
    "end_date": "24.08.2025"
  },
  {
    "id": 119,
    "user_id": 12,
    "status": "✈️ Командировка",
    "start_date": "12.08.2025",
    "end_date": "26.08.2025"
  },
  {
    "id": 120,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "11.08.2025",
    "end_date": "24.08.2025"
  },
  {
    "id": 121,
    "user_id": 10,
    "status": "🏖️ Отпуск",
    "start_date": "01.09.2025",
    "end_date": "01.09.2025"
  },
  {
    "id": 122,
    "user_id": 10,
    "status": "🏖️ Отпуск",
    "start_date": "01.11.2025",
    "end_date": "01.11.2025"
  },
  {
    "id": 123,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "28.08.2025",
    "end_date": "29.08.2025"
  },
  {
    "id": 124,
    "user_id": 5,
    "status": "✈️ Командировка",
    "start_date": "29.08.2025",
    "end_date": "08.09.2025"
  },
  {
    "id": 125,
    "user_id": 4,
    "status": "🏖️ Отпуск",
    "start_date": "01.09.2025",
    "end_date": "12.09.2025"
  },
  {
    "id": 127,
    "user_id": 11,
    "status": "🏖️ Отпуск",
    "start_date": "01.09.2025",
    "end_date": "01.09.2025"
  },
  {
    "id": 128,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "08.09.2025",
    "end_date": "21.09.2025"
  },
  {
    "id": 130,
    "user_id": 7,
    "status": "🏖️ Отпуск",
    "start_date": "08.09.2025",
    "end_date": "15.09.2025"
  },
  {
    "id": 131,
    "user_id": 5,
    "status": "✈️ Командировка",
    "start_date": "15.09.2025",
    "end_date": "26.09.2025"
  },
  {
    "id": 132,
    "user_id": 9,
    "status": "✈️ Командировка",
    "start_date": "17.09.2025",
    "end_date": "26.09.2025"
  },
  {
    "id": 133,
    "user_id": 7,
    "status": "🤒 Больничный",
    "start_date": "17.09.2025",
    "end_date": "23.09.2025"
  },
  {
    "id": 134,
    "user_id": 123456,
    "status": "✈️ Командировка",
    "start_date": "19.09.2025",
    "end_date": "01.10.2025"
  },
  {
    "id": 135,
    "user_id": 3,
    "status": "🤒 Больничный",
    "start_date": "20.09.2025",
    "end_date": "06.10.2025"
  },
  {
    "id": 137,
    "user_id": 11,
    "status": "🤒 Больничный",
    "start_date": "22.09.2025",
    "end_date": "22.09.2025"
  },
  {
    "id": 138,
    "user_id": 15,
    "status": "✈️ Командировка",
    "start_date": "22.09.2025",
    "end_date": "26.09.2025"
  },
  {
    "id": 139,
    "user_id": 7,
    "status": "✈️ Командировка",
    "start_date": "06.10.2025",
    "end_date": "08.10.2025"
  },
  {
    "id": 140,
    "user_id": 6,
    "status": "✈️ Командировка",
    "start_date": "05.10.2025",
    "end_date": "08.10.2025"
  },
  {
    "id": 141,
    "user_id": 5,
    "status": "🏖️ Отпуск",
    "start_date": "06.10.2025",
    "end_date": "14.10.2025"
  },
  {
    "id": 142,
    "user_id": 12,
    "status": "✈️ Командировка",
    "start_date": "10.10.2025",
    "end_date": "23.10.2025"
  },
  {
    "id": 143,
    "user_id": 10,
    "status": "✈️ Командировка",
    "start_date": "12.10.2025",
    "end_date": "19.10.2025"
  },
  {
    "id": 144,
    "user_id": 6,
    "status": "🤒 Больничный",
    "start_date": "14.10.2025",
    "end_date": "22.10.2025"
  },
  {
    "id": 146,
    "user_id": 5,
    "status": "✈️ Командировка",
    "start_date": "20.10.2025",
    "end_date": "31.10.2025"
  },
  {
    "id": 149,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "05.11.2025",
    "end_date": "06.11.2025"
  },
  {
    "id": 150,
    "user_id": 9,
    "status": "✈️ Командировка",
    "start_date": "13.11.2025",
    "end_date": "21.11.2025"
  },
  {
    "id": 152,
    "user_id": 4,
    "status": "🏖️ Отпуск",
    "start_date": "17.11.2025",
    "end_date": "18.11.2025"
  },
  {
    "id": 153,
    "user_id": 7,
    "status": "✈️ Командировка",
    "start_date": "17.11.2025",
    "end_date": "21.11.2025"
  },
  {
    "id": 154,
    "user_id": 11,
    "status": "🏖️ Отпуск",
    "start_date": "25.11.2025",
    "end_date": "03.12.2025"
  },
  {
    "id": 155,
    "user_id": 6,
    "status": "✈️ Командировка",
    "start_date": "23.11.2025",
    "end_date": "27.11.2025"
  },
  {
    "id": 158,
    "user_id": 7,
    "status": "🏖️ Отпуск",
    "start_date": "01.12.2025",
    "end_date": "04.12.2025"
  },
  {
    "id": 159,
    "user_id": 13,
    "status": "✈️ Командировка",
    "start_date": "07.12.2025",
    "end_date": "12.12.2025"
  },
  {
    "id": 160,
    "user_id": 5,
    "status": "✈️ Командировка",
    "start_date": "08.12.2025",
    "end_date": "25.12.2025"
  },
  {
    "id": 161,
    "user_id": 6,
    "status": "✈️ Командировка",
    "start_date": "14.12.2025",
    "end_date": "23.12.2025"
  },
  {
    "id": 162,
    "user_id": 6,
    "status": "🏖️ Отпуск",
    "start_date": "24.12.2025",
    "end_date": "24.12.2025"
  },
  {
    "id": 163,
    "user_id": 6,
    "status": "🏖️ Отпуск",
    "start_date": "30.12.2025",
    "end_date": "30.12.2025"
  },
  {
    "id": 164,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "22.12.2025",
    "end_date": "22.12.2025"
  },
  {
    "id": 165,
    "user_id": 8,
    "status": "🏖️ Отпуск",
    "start_date": "29.12.2025",
    "end_date": "30.12.2025"
  },
  {
    "id": 166,
    "user_id": 9,
    "status": "🤒 Больничный",
    "start_date": "24.12.2025",
    "end_date": "12.01.2026"
  },
  {
    "id": 167,
    "user_id": 5,
    "status": "🏖️ Отпуск",
    "start_date": "29.12.2025",
    "end_date": "11.01.2026"
  },
  {
    "id": 168,
    "user_id": 11,
    "status": "✈️ Командировка",
    "start_date": "29.01.2026",
    "end_date": "11.02.2026"
  },
  {
    "id": 170,
    "user_id": 2,
    "status": "🏖️ Отпуск",
    "start_date": "13.02.2026",
    "end_date": "17.02.2026"
  },
  {
    "id": 171,
    "user_id": 11,
    "status": "✈️ Командировка",
    "start_date": "11.02.2026",
    "end_date": "13.02.2026"
  },
  {
    "id": 172,
    "user_id": 12,
    "status": "✈️ Командировка",
    "start_date": "11.02.2026",
    "end_date": "25.02.2026"
  },
  {
    "id": 173,
    "user_id": 11,
    "status": "🤒 Больничный",
    "start_date": "19.02.2026",
    "end_date": "02.03.2026"
  },
  {
    "id": 175,
    "user_id": 4,
    "status": "🤒 Больничный",
    "start_date": "02.03.2026",
    "end_date": "02.03.2026"
  },
  {
    "id": 176,
    "user_id": 2,
    "status": "🏖️ Отпуск",
    "start_date": "06.03.2026",
    "end_date": "15.03.2026"
  },
  {
    "id": 177,
    "user_id": 10,
    "status": "✈️ Командировка",
    "start_date": "02.03.2026",
    "end_date": "06.03.2026"
  },
  {
    "id": 178,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "06.03.2026",
    "end_date": "06.03.2026"
  },
  {
    "id": 179,
    "user_id": 12,
    "status": "🏖️ Отпуск",
    "start_date": "20.03.2026",
    "end_date": "20.03.2026"
  },
  {
    "id": 180,
    "user_id": 4,
    "status": "🏖️ Отпуск",
    "start_date": "09.03.2026",
    "end_date": "15.03.2026"
  },
  {
    "id": 181,
    "user_id": 11,
    "status": "🏖️ Отпуск",
    "start_date": "10.03.2026",
    "end_date": "10.03.2026"
  },
  {
    "id": 182,
    "user_id": 11,
    "status": "✈️ Командировка",
    "start_date": "11.03.2026",
    "end_date": "22.03.2026"
  },
  {
    "id": 183,
    "user_id": 9,
    "status": "✈️ Командировка",
    "start_date": "11.03.2026",
    "end_date": "13.03.2026"
  },
  {
    "id": 184,
    "user_id": 5,
    "status": "🏖️ Отпуск",
    "start_date": "10.03.2026",
    "end_date": "13.03.2026"
  },
  {
    "id": 185,
    "user_id": 15,
    "status": "🏖️ Отпуск",
    "start_date": "29.03.2026",
    "end_date": "16.03.2026"
  },
  {
    "id": 186,
    "user_id": 15,
    "status": "🏖️ Отпуск",
    "start_date": "16.03.2026",
    "end_date": "23.03.2026"
  },
  {
    "id": 187,
    "user_id": 15,
    "status": "🏖️ Отпуск",
    "start_date": "16.03.2026",
    "end_date": "16.03.2026"
  },
  {
    "id": 188,
    "user_id": 15,
    "status": "🏖️ Отпуск",
    "start_date": "16.03.2026",
    "end_date": "29.03.2026"
  },
  {
    "id": 189,
    "user_id": 15,
    "status": "🏖️ Отпуск",
    "start_date": "16.03.2026",
    "end_date": "29.03.2026"
  },
  {
    "id": 190,
    "user_id": 123456,
    "status": "🏖️ Отпуск",
    "start_date": "16.03.2026",
    "end_date": "31.03.2026"
  },
  {
    "id": 191,
    "user_id": 10,
    "status": "🏖️ Отпуск",
    "start_date": "23.03.2026",
    "end_date": "27.03.2026"
  },
  {
    "id": 192,
    "user_id": 7,
    "status": "🏖️ Отпуск",
    "start_date": "01.04.2026",
    "end_date": "12.04.2026"
  },
  {
    "id": 193,
    "user_id": 7,
    "status": "🏖️ Отпуск",
    "start_date": "01.04.2026",
    "end_date": "12.04.2026"
  },
  {
    "id": 194,
    "user_id": 11,
    "status": "🏖️ Отпуск",
    "start_date": "13.04.2026",
    "end_date": "13.04.2026"
  },
  {
    "id": 195,
    "user_id": 11,
    "status": "🏖️ Отпуск",
    "start_date": "14.04.2026",
    "end_date": "19.04.2026"
  },
  {
    "id": 196,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "15.04.2026"
  },
  {
    "id": 197,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "15.04.2026"
  },
  {
    "id": 198,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "07.04.2026"
  },
  {
    "id": 199,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "08.04.2026"
  },
  {
    "id": 200,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "09.04.2026"
  },
  {
    "id": 201,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "10.04.2026"
  },
  {
    "id": 202,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "11.04.2026"
  },
  {
    "id": 203,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "10.04.2026"
  },
  {
    "id": 204,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "09.04.2026"
  },
  {
    "id": 205,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "08.04.2026"
  },
  {
    "id": 206,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "10.04.2026"
  },
  {
    "id": 207,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "09.04.2026"
  },
  {
    "id": 208,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "15.04.2026"
  },
  {
    "id": 209,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "06.04.2026"
  },
  {
    "id": 210,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "07.04.2026"
  },
  {
    "id": 211,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "08.04.2026"
  },
  {
    "id": 212,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "09.04.2026"
  },
  {
    "id": 213,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "07.04.2026"
  },
  {
    "id": 214,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "10.04.2026"
  },
  {
    "id": 215,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "08.04.2026"
  },
  {
    "id": 216,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "09.04.2026"
  },
  {
    "id": 217,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "11.04.2026"
  },
  {
    "id": 218,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "11.04.2026"
  },
  {
    "id": 219,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "07.04.2026"
  },
  {
    "id": 220,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "07.04.2026"
  },
  {
    "id": 221,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "11.04.2026"
  },
  {
    "id": 222,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "07.04.2026"
  },
  {
    "id": 223,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "06.04.2026"
  },
  {
    "id": 224,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "15.04.2026"
  },
  {
    "id": 225,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "11.04.2026"
  },
  {
    "id": 226,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "15.04.2026"
  },
  {
    "id": 227,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "15.04.2026"
  },
  {
    "id": 228,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "06.04.2026"
  },
  {
    "id": 229,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "14.04.2026"
  },
  {
    "id": 230,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "14.04.2026"
  },
  {
    "id": 231,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "06.04.2026"
  },
  {
    "id": 232,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "06.04.2026"
  },
  {
    "id": 233,
    "user_id": 9,
    "status": "🏖️ Отпуск",
    "start_date": "06.04.2026",
    "end_date": "15.04.2026"
  }
]


def get_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, encoding='utf-8') as f:
            return json.load(f)
    return {"database": {"path": "exams.db"}}

def migrate():
    config = get_config()
    db_path = config['database']['path']
    print(f"\n📦 Подключение к БД: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # --- Очищаем существующие данные ---
    print("🗑️  Очистка таблиц...")
    c.execute("DELETE FROM exams")
    c.execute("DELETE FROM user_status")
    c.execute("DELETE FROM users")
    c.execute("DELETE FROM exam_types")
    c.execute("DELETE FROM sqlite_sequence WHERE name IN ('exams','user_status','users','exam_types')")

    # --- exam_types ---
    print(f"📋 Импорт {len(EXAM_TYPES)} типов экзаменов...")
    for t in EXAM_TYPES:
        c.execute(
            "INSERT OR REPLACE INTO exam_types (id, name, duration, emoji) VALUES (?,?,?,?)",
            (t['id'], t['name'], t['duration'], t['emoji'])
        )

    # --- users ---
    print(f"👥 Импорт {len(USERS)} пользователей...")
    for u in USERS:
        # Убедимся что колонки существуют (check_and_fix_database должна была их создать)
        cols = [row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()]
        needed = ['login', 'password_hash', 'role', 'email']
        for col in needed:
            if col not in cols:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
                print(f"  ➕ Добавлена колонка: {col}")

        c.execute("""
            INSERT OR REPLACE INTO users
                (user_id, telegram_id, full_name, login, password_hash, role, email)
            VALUES (?,?,?,?,?,?,?)
        """, (u['user_id'], u['telegram_id'], u['full_name'],
              u['login'], u['password_hash'], u['role'], u['email']))
        print(f"  ✅ {u['full_name']:35s} → {u['login']} ({u['role']})")

    # --- exams ---
    print(f"\n📝 Импорт {len(EXAMS)} записей экзаменов...")
    exam_cols = [row[1] for row in c.execute("PRAGMA table_info(exams)").fetchall()]
    for e in EXAMS:
        if 'last_notification_day' not in exam_cols:
            c.execute("ALTER TABLE exams ADD COLUMN last_notification_day INTEGER DEFAULT 0")
            exam_cols.append('last_notification_day')
        c.execute("""
            INSERT OR REPLACE INTO exams
                (id, user_id, name, date, duration,
                 notification_sent, month_notification_sent,
                 week_notification_sent, exam_day_notification_sent,
                 end_day_notification_sent, last_notification_day)
            VALUES (?,?,?,?,?,?,?,?,?,?,0)
        """, (e['id'], e['user_id'], e['name'], e['date'], e['duration'],
              e['notification_sent'], e['month_notification_sent'],
              e['week_notification_sent'], e['exam_day_notification_sent'],
              e['end_day_notification_sent']))

    # --- user_status ---
    print(f"\n🏷️  Импорт {len(STATUSES)} статусов...")
    for s in STATUSES:
        c.execute("""
            INSERT OR REPLACE INTO user_status (id, user_id, status, start_date, end_date)
            VALUES (?,?,?,?,?)
        """, (s['id'], s['user_id'], s['status'], s['start_date'], s['end_date']))

    conn.commit()
    conn.close()

    print("\n✅ Миграция завершена!")
    print("\n🔑 Логины и пароль для всех: 123456")
    for u in USERS:
        print(f"   {u['full_name']:35s} → {u['login']}")

if __name__ == "__main__":
    migrate()
