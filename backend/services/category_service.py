from backend.core.database import db
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from bson.objectid import ObjectId

categories_col = db["categories"]

# Simple cache for category names
_category_cache = None
_category_cache_time = None
_cache_duration = timedelta(minutes=5)

def _get_cache_valid():
    """Check if cache is valid"""
    global _category_cache, _category_cache_time
    now = datetime.now()
    if _category_cache is not None and _category_cache_time is not None:
        if now - _category_cache_time < _cache_duration:
            return True
    return False

def invalidate_category_cache():
    """Clear category cache"""
    global _category_cache, _category_cache_time
    _category_cache = None
    _category_cache_time = None

def get_categories() -> List[Dict]:
    """Get all categories sorted by name"""
    try:
        return list(categories_col.find().sort("name", 1))
    except Exception as e:
        print(f"[ERROR] get_categories: {e}")
        return []

def get_category_names() -> List[str]:
    """Get all category names with caching"""
    global _category_cache, _category_cache_time

    if _get_cache_valid():
        return _category_cache

    try:
        categories = list(categories_col.find({}, {"name": 1}).sort("name", 1))
        _category_cache = [cat["name"] for cat in categories]
        _category_cache_time = datetime.now()
        return _category_cache
    except Exception as e:
        print(f"[ERROR] get_category_names: {e}")
        return []

def add_category(name: str, description: str = "", color: str = "#3498db",
                section: str = "kitchen", printer_role: str = "") -> bool:
    """Add a new category"""
    try:
        if categories_col.find_one({"name": name}):
            return False  # Category already exists

        if not printer_role:
            printer_role = f"kot-{section}"

        categories_col.insert_one({
            "name": name,
            "description": description,
            "color": color,
            "section": section,
            "printer_role": printer_role,
            "created_at": datetime.now(),
            "is_active": True
        })
        invalidate_category_cache()
        return True
    except Exception as e:
        print(f"[ERROR] add_category: {e}")
        return False

def update_category(category_id: str, name: str, description: str = "", color: str = "#3498db",
                   section: str = "kitchen", printer_role: str = "") -> bool:
    """Update an existing category"""
    try:
        existing = categories_col.find_one({"name": name})
        if existing and str(existing["_id"]) != category_id:
            return False

        if not printer_role:
            printer_role = f"kot-{section}"

        try:
            _id = ObjectId(category_id)
        except Exception:
            _id = category_id

        result = categories_col.update_one(
            {"_id": _id},
            {"$set": {
                "name": name,
                "description": description,
                "color": color,
                "section": section,
                "printer_role": printer_role
            }}
        )
        if result.modified_count > 0:
            invalidate_category_cache()
        return result.modified_count > 0
    except Exception as e:
        print(f"[ERROR] update_category: {e}")
        return False

def delete_category(category_id: str) -> bool:
    """Delete a category"""
    try:
        from backend.services.menu_service import menu_col
        try:
            _id = ObjectId(category_id)
        except Exception:
            _id = category_id

        product_count = menu_col.count_documents({"category": category_id})

        if product_count > 0:
            return False  # Cannot delete category with products

        result = categories_col.delete_one({"_id": _id})
        if result.deleted_count > 0:
            invalidate_category_cache()
        return result.deleted_count > 0
    except Exception as e:
        print(f"[ERROR] delete_category: {e}")
        return False

def get_category_by_id(category_id: str) -> Optional[Dict]:
    """Get a single category by ID"""
    try:
        try:
            _id = ObjectId(category_id)
        except Exception:
            _id = category_id
        return categories_col.find_one({"_id": _id})
    except Exception as e:
        print(f"[ERROR] get_category_by_id: {e}")
        return None

def get_category_by_name(name: str) -> Optional[Dict]:
    """Get a single category by name"""
    try:
        return categories_col.find_one({"name": name})
    except Exception as e:
        print(f"[ERROR] get_category_by_name: {e}")
        return None

def seed_default_categories():
    """Seed default categories if none exist"""
    try:
        if categories_col.count_documents({}) == 0:
            default_categories = [
                {"name": "Burger", "description": "Burgers and sandwiches", "section": "kitchen", "color": "#e74c3c"},
                {"name": "Pizza", "description": "Pizza items", "section": "pizza", "color": "#f39c12"},
                {"name": "Drink", "description": "Beverages and drinks", "section": "bar", "color": "#3498db"},
                {"name": "Dessert", "description": "Desserts and sweets", "section": "dessert", "color": "#9b59b6"},
                {"name": "Side", "description": "Side dishes and appetizers", "section": "kitchen", "color": "#27ae60"}
            ]

            for cat in default_categories:
                add_category(cat["name"], cat["description"], cat["color"], cat["section"])
    except Exception as e:
        print(f"[ERROR] seed_default_categories: {e}")
