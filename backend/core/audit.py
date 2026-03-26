from backend.core.database import audit_logs_col
from datetime import datetime

def log_action(user_id, username, action, details=""):
    """
    Logs a system action.
    """
    log_entry = {
        "user_id": user_id,
        "username": username,
        "action": action,
        "details": details,
        "timestamp": datetime.now()
    }
    audit_logs_col.insert_one(log_entry)

def get_logs(skip=0, limit=50):
    total = audit_logs_col.count_documents({})
    logs = list(audit_logs_col.find().sort("timestamp", -1).skip(skip).limit(limit))
    return logs, total
