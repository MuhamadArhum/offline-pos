
from app.core.database import db
from datetime import datetime
from bson import ObjectId

customers_col = db["customers"]

def get_customer_by_phone(phone):
    try:
        return customers_col.find_one({"phone": phone})
    except Exception as e:
        print(f"[ERROR] get_customer_by_phone: {e}")
        return None

def create_or_update_customer(phone, name, address=None):
    try:
        data = {
            "phone": phone,
            "name": name,
            "updated_at": datetime.now()
        }
        if address:
            data["address"] = address

        result = customers_col.find_one_and_update(
            {"phone": phone},
            {"$set": data, "$setOnInsert": {"points": 0, "created_at": datetime.now(), "order_history": []}},
            upsert=True,
            return_document=True
        )
        return result
    except Exception as e:
        print(f"[ERROR] create_or_update_customer: {e}")
        return None

def add_loyalty_points(customer_id, points):
    try:
        customers_col.update_one(
            {"_id": ObjectId(customer_id)},
            {"$inc": {"points": points}}
        )
    except Exception as e:
        print(f"[ERROR] add_loyalty_points: {e}")

def deduct_loyalty_points(customer_id, points):
    try:
        customers_col.update_one(
            {"_id": ObjectId(customer_id), "points": {"$gte": points}},
            {"$inc": {"points": -points}}
        )
    except Exception as e:
        print(f"[ERROR] deduct_loyalty_points: {e}")

def log_customer_order(customer_id, order_id, total):
    try:
        customers_col.update_one(
            {"_id": ObjectId(customer_id)},
            {
                "$push": {
                    "order_history": {
                        "order_id": order_id,
                        "date": datetime.now(),
                        "total": total
                    }
                },
                "$set": {"last_order_at": datetime.now()}
            }
        )
    except Exception as e:
        print(f"[ERROR] log_customer_order: {e}")
