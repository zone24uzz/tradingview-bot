import json
import os

DB_FILE = "db.json"

user_data_store = {}
admins = {}

def load_db():
    global user_data_store, admins
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_data_store.update(data.get("users", {}))
                admins.update(data.get("admins", {}))
        except Exception as e:
            print(f"Error loading DB: {e}")

def save_db():
    data = {
        "users": user_data_store,
        "admins": admins
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

load_db()
