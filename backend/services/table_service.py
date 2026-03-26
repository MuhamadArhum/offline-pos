import re
from backend.core.database import db, orders_col

tables_col = db["tables"]

def _table_sort_key(table):
    """Sort T1, T2, T10 numerically instead of lexicographically."""
    no = table.get("table_no", "")
    m = re.search(r'\d+', no)
    return (int(m.group()) if m else 0, no)

def init_tables():
    try:
        if tables_col.count_documents({}) == 0:
            for i in range(1, 11):
                tables_col.insert_one({
                    "table_no": f"T{i}",
                    "status": "Free"
                })
    except Exception as e:
        print(f"[ERROR] init_tables: {e}")

def get_free_tables():
    try:
        return [t["table_no"] for t in tables_col.find({"status": "Free"})]
    except Exception as e:
        print(f"[ERROR] get_free_tables: {e}")
        return []

def get_all_tables():
    try:
        tables = list(tables_col.find())
        tables.sort(key=_table_sort_key)
        return tables
    except Exception as e:
        print(f"[ERROR] get_all_tables: {e}")
        return []

def set_table_status(table_no, status):
    try:
        tables_col.update_one(
            {"table_no": table_no},
            {"$set": {"status": status}}
        )
    except Exception as e:
        print(f"[ERROR] set_table_status: {e}")

def add_table(table_no):
    try:
        if tables_col.find_one({"table_no": table_no}):
            return False, "Table already exists"
        tables_col.insert_one({
            "table_no": table_no,
            "status": "Free"
        })
        return True, "Table added successfully"
    except Exception as e:
        print(f"[ERROR] add_table: {e}")
        return False, str(e)

def delete_table(table_no):
    try:
        if not tables_col.find_one({"table_no": table_no}):
            return False, "Table not found"
        running = orders_col.find_one({"table_no": table_no, "status": {"$in": ["Running", "Kitchen"]}})
        if running:
            return False, f"Table {table_no} has a running order. Complete it first."
        tables_col.delete_one({"table_no": table_no})
        return True, "Table deleted successfully"
    except Exception as e:
        print(f"[ERROR] delete_table: {e}")
        return False, str(e)
