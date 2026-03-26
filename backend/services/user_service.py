import bcrypt
from backend.core.database import users_col
from datetime import datetime, timedelta, timezone

MIN_PASSWORD_LEN = 8
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5

def _normalize_username(username: str) -> str:
    return str(username or "").strip()

def validate_password_strength(password: str) -> tuple[bool, str]:
    pwd = str(password or "")
    if len(pwd) < MIN_PASSWORD_LEN:
        return False, f"Password must be at least {MIN_PASSWORD_LEN} characters"
    return True, ""

def create_user(username, password, role, phone=None, vehicle_no=None):
    username = _normalize_username(username)
    ok, msg = validate_password_strength(password)
    if not username:
        raise ValueError("Username is required")
    if not ok:
        raise ValueError(msg)
    if users_col.find_one({"username": username}):
        raise ValueError("Username already exists")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user_doc = {
        "username": username,
        "password": hashed,
        "role": role,
        "active": True,
        "failed_attempts": 0,
        "locked_until": None
    }
    if phone: user_doc["phone"] = phone
    if vehicle_no: user_doc["vehicle_no"] = vehicle_no
    
    users_col.insert_one(user_doc)

def get_users(skip=0, limit=0):
    if limit > 0:
        total = users_col.count_documents({})
        users = list(users_col.find().skip(skip).limit(limit))
        return users, total
    return list(users_col.find())

def get_users_by_role(role):
    """
    Get all active users with a specific role.
    """
    return list(users_col.find({"role": role, "active": True}))

def toggle_user(user_id, status):
    users_col.update_one(
        {"_id": user_id},
        {"$set": {"active": status}}
    )

def record_failed_login(username: str):
    username = _normalize_username(username)
    if not username:
        return

    user = users_col.find_one({"username": username})
    if not user:
        return

    failed = int(user.get("failed_attempts", 0)) + 1
    update = {"failed_attempts": failed}

    if failed >= MAX_FAILED_ATTEMPTS:
        update["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)

    users_col.update_one({"_id": user["_id"]}, {"$set": update})

def clear_failed_logins(user_id):
    users_col.update_one(
        {"_id": user_id},
        {"$set": {"failed_attempts": 0, "locked_until": None}}
    )

def authenticate_user(username, password):
    username = _normalize_username(username)
    user = users_col.find_one({"username": username})
    
    if not user:
        return None
        
    # Check lockout
    locked_until = user.get("locked_until")
    if locked_until:
        if isinstance(locked_until, str):
            try:
                locked_until = datetime.fromisoformat(locked_until)
            except Exception:
                locked_until = None
        
        # Ensure timezone awareness for comparison
        if locked_until and locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
            
        if locked_until and locked_until > datetime.now(timezone.utc):
            return None # Locked
        
    if not user.get("active", True):
        return None # Inactive
        
    if bcrypt.checkpw(password.encode(), user['password']):
        clear_failed_logins(user['_id'])
        return user
    else:
        record_failed_login(username)
        return None
