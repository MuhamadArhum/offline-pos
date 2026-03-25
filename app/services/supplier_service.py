from app.core.database import db
from bson import ObjectId

supplier_col = db["suppliers"]

def get_suppliers():
    """Get all suppliers"""
    try:
        return list(supplier_col.find())
    except Exception as e:
        print(f"[ERROR] get_suppliers: {e}")
        return []

def get_supplier_by_id(supplier_id):
    """Get a single supplier by ID"""
    try:
        return supplier_col.find_one({"_id": ObjectId(supplier_id)})
    except Exception as e:
        print(f"[ERROR] get_supplier_by_id: {e}")
        return None

def add_supplier(supplier_data):
    """Add a new supplier"""
    try:
        supplier_col.insert_one(supplier_data)
        return True
    except Exception as e:
        print(f"[ERROR] add_supplier: {e}")
        return False

def update_supplier(supplier_id, updated_data):
    """Update a supplier"""
    try:
        supplier_col.update_one(
            {"_id": ObjectId(supplier_id)},
            {"$set": updated_data}
        )
        return True
    except Exception as e:
        print(f"[ERROR] update_supplier: {e}")
        return False

def delete_supplier(supplier_id):
    """Delete a supplier"""
    try:
        supplier_col.delete_one({"_id": ObjectId(supplier_id)})
        return True
    except Exception as e:
        print(f"[ERROR] delete_supplier: {e}")
        return False
