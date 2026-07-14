"""Обновляет эмодзи ПП с 🚒 на 🚑 в существующей БД."""
import sqlite3, json, os

config_path = os.path.join(os.path.dirname(__file__), 'config.json')
db_path = 'exams.db'
if os.path.exists(config_path):
    with open(config_path, encoding='utf-8') as f:
        db_path = json.load(f).get('database', {}).get('path', 'exams.db')

conn = sqlite3.connect(db_path)
rows = conn.execute("UPDATE exam_types SET emoji = '🚑' WHERE name = 'ПП'")
conn.commit()
print(f"✅ Обновлено строк: {rows.rowcount}  (ПП → 🚑)")
conn.close()
