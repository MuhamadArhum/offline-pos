
from backend.core.database import db

settings_col = db["settings"]

def get_settings():
    s = settings_col.find_one()
    if not s:
        s = {
            "restaurant_name": "My Restaurant",
            "address": "",
            "phone": "",
            "tax": 0,
            "service": 0,
            "currency": "Rs"
        }
        settings_col.insert_one(s)
    return s

def save_settings(data):
    settings_col.delete_many({})
    settings_col.insert_one(data)
