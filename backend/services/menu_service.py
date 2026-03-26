from backend.core.database import db
from backend.core.menu_cache import MenuCache

menu_col = db["menu_items"]

def add_item(name, price, category, code="", available=True, is_combo=False, combo_items=None):
    if combo_items is None:
        combo_items = []
    try:
        menu_col.insert_one({
            "name": name,
            "price": price,
            "category": category,
            "code": code,
            "available": available,
            "is_combo": is_combo,
            "combo_items": combo_items
        })
        MenuCache().invalidate()
        return True
    except Exception as e:
        print(f"[ERROR] add_item: {e}")
        return False

def get_items():
    try:
        return list(menu_col.find())
    except Exception as e:
        print(f"[ERROR] get_items: {e}")
        return []

# 🔴 YE FUNCTION ZAROORI HAI (Billing isko use karti hai)
def get_menu():
    """Get menu with caching for performance"""
    try:
        cache = MenuCache()
        return cache.get_menu()
    except Exception as e:
        print(f"[ERROR] get_menu: {e}")
        return []

def get_menu_paginated(query=None, skip=0, limit=20):
    """Get menu items with pagination (Bypasses cache for admin view)"""
    try:
        q = query or {}
        total = menu_col.count_documents(q)
        items = list(menu_col.find(q).skip(skip).limit(limit))
        return items, total
    except Exception as e:
        print(f"[ERROR] get_menu_paginated: {e}")
        return [], 0

def update_item(item_id, name, price, category, code, available, is_combo=False, combo_items=None):
    if combo_items is None:
        combo_items = []
    try:
        menu_col.update_one(
            {"_id": item_id},
            {"$set": {
                "name": name,
                "price": price,
                "category": category,
                "code": code,
                "available": available,
                "is_combo": is_combo,
                "combo_items": combo_items
            }}
        )
        MenuCache().invalidate()
        return True
    except Exception as e:
        print(f"[ERROR] update_item: {e}")
        return False

def delete_item(item_id):
    try:
        menu_col.delete_one({"_id": item_id})
        MenuCache().invalidate()
        return True
    except Exception as e:
        print(f"[ERROR] delete_item: {e}")
        return False

def get_items_by_category(category):
    """Get all menu items for a specific category"""
    try:
        return list(menu_col.find({"category": category}))
    except Exception as e:
        print(f"[ERROR] get_items_by_category: {e}")
        return []
