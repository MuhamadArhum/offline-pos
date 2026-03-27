import bcrypt
from backend.core.database import users_col
from datetime import datetime, timedelta, timezone

MIN_PASSWORD_LEN = 6
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5


# ── Custom Exceptions ─────────────────────────────────────────────────────────
class AuthError(Exception):
    """Base authentication error"""
    pass

class AccountLockedError(AuthError):
    """Raised when account is temporarily locked due to failed attempts"""
    def __init__(self, locked_until: datetime):
        self.locked_until = locked_until
        remaining = max(0, int((locked_until - datetime.now(timezone.utc)).total_seconds() // 60) + 1)
        super().__init__(f"Account locked. Try again in {remaining} minute(s).")

class AccountInactiveError(AuthError):
    """Raised when account has been deactivated"""
    def __init__(self):
        super().__init__("This account has been deactivated. Contact your administrator.")

class InvalidCredentialsError(AuthError):
    """Raised when username or password is wrong"""
    def __init__(self):
        super().__init__("Incorrect username or password.")


# ── Helpers ───────────────────────────────────────────────────────────────────
def _normalize_username(username: str) -> str:
    return str(username or "").strip()


def validate_password_strength(password: str) -> tuple[bool, str]:
    pwd = str(password or "")
    if len(pwd) < MIN_PASSWORD_LEN:
        return False, f"Password must be at least {MIN_PASSWORD_LEN} characters"
    if pwd.isdigit():
        return False, "Password cannot be all numbers"
    return True, ""


# ── Core Functions ────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str):
    """
    Authenticate a user. Returns the user dict on success.
    Raises AccountLockedError, AccountInactiveError, or InvalidCredentialsError on failure.
    """
    username = _normalize_username(username)
    if not username or not password:
        raise InvalidCredentialsError()

    user = users_col.find_one({"username": username})

    if not user:
        raise InvalidCredentialsError()

    # Check lockout
    locked_until = user.get("locked_until")
    if locked_until:
        if isinstance(locked_until, str):
            try:
                locked_until = datetime.fromisoformat(locked_until)
            except Exception:
                locked_until = None

        if locked_until:
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > datetime.now(timezone.utc):
                raise AccountLockedError(locked_until)

    # Check active status
    if not user.get("active", True):
        raise AccountInactiveError()

    # Check password
    try:
        password_matches = bcrypt.checkpw(password.encode(), user["password"])
    except Exception:
        raise InvalidCredentialsError()

    if not password_matches:
        _record_failed_login_by_id(user["_id"], user.get("failed_attempts", 0))
        raise InvalidCredentialsError()

    # Success — clear failed attempts
    clear_failed_logins(user["_id"])
    return user


def create_user(username, password, role, phone=None, vehicle_no=None):
    username = _normalize_username(username)
    if not username:
        raise ValueError("Username is required")

    ok, msg = validate_password_strength(password)
    if not ok:
        raise ValueError(msg)

    if users_col.find_one({"username": username}):
        raise ValueError(f"Username '{username}' already exists")

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user_doc = {
        "username": username,
        "password": hashed,
        "role": role,
        "active": True,
        "failed_attempts": 0,
        "locked_until": None,
        "created_at": datetime.now(timezone.utc),
    }
    if phone:
        user_doc["phone"] = phone
    if vehicle_no:
        user_doc["vehicle_no"] = vehicle_no

    users_col.insert_one(user_doc)


def get_users(skip=0, limit=0):
    if limit > 0:
        total = users_col.count_documents({})
        users = list(users_col.find().skip(skip).limit(limit))
        return users, total
    return list(users_col.find())


def get_users_by_role(role):
    return list(users_col.find({"role": role, "active": True}))


def toggle_user(user_id, status):
    users_col.update_one(
        {"_id": user_id},
        {"$set": {"active": status}}
    )


def record_failed_login(username: str):
    """Public API kept for backward compatibility."""
    username = _normalize_username(username)
    if not username:
        return
    user = users_col.find_one({"username": username})
    if not user:
        return
    _record_failed_login_by_id(user["_id"], user.get("failed_attempts", 0))


def _record_failed_login_by_id(user_id, current_attempts: int):
    failed = int(current_attempts) + 1
    update = {"failed_attempts": failed}
    if failed >= MAX_FAILED_ATTEMPTS:
        update["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
    users_col.update_one({"_id": user_id}, {"$set": update})


def clear_failed_logins(user_id):
    users_col.update_one(
        {"_id": user_id},
        {"$set": {"failed_attempts": 0, "locked_until": None}}
    )
