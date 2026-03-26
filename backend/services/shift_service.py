from datetime import datetime, timedelta
from backend.core.database import shifts_col, orders_col, expenses_col
from bson.objectid import ObjectId

def get_shifts_by_date(date_obj):
    """
    Get all shifts for a specific date (start_time within that day).
    """
    start = datetime.combine(date_obj, datetime.min.time())
    end = datetime.combine(date_obj, datetime.max.time())
    
    shifts = list(shifts_col.find({
        "start_time": {"$gte": start, "$lte": end}
    }).sort("start_time", 1))
    
    return shifts

def get_shift_report(shift_id):
    """
    Alias for report_service.get_shift_report_data but lightweight?
    Actually, we should use report_service for full data.
    This might just return the shift document.
    """
    return shifts_col.find_one({"_id": ObjectId(shift_id)})

def start_shift(user, opening_cash=0.0):
    """
    Starts a new shift for the user.
    """
    # Check if user already has an active shift
    # Support both username (str) and user_id (ObjectId)
    query = {"status": "Active"}
    if isinstance(user, str):
        query["user"] = user
    else:
        # Assuming user is an object with _id or just user_id
        # For now, stick to what sales_page.py sends (username usually)
        # But if it sends user dict, we might need to adjust.
        # Based on sales_page.py: start_shift(user, ...) where user is from LoginWindow
        # LoginWindow returns user dict.
        # But wait, sales_page.py:1453 start_shift(user, ...)
        # Let's assume user is username string if checking "user" field in DB.
        # But if DB uses user_id, we need that.
        # shifts_crud.py used "user": user.
        query["user"] = user

    active_shift = shifts_col.find_one(query)
    
    if active_shift:
        return active_shift
        
    shift_data = {
        "user": user,
        "start_time": datetime.now(),
        "opening_cash": opening_cash,
        "status": "Active",
        "end_time": None,
        "closing_cash": 0.0,
        "total_sales": 0.0,
        "total_expenses": 0.0,
        "cash_difference": 0.0,
        # Fields for incremental tracking (compatibility)
        "total_cash_sales": 0.0,
        "total_card_sales": 0.0,
        "expected_cash": 0.0
    }
    
    result = shifts_col.insert_one(shift_data)
    shift_data["_id"] = result.inserted_id
    return shift_data

def open_shift(user_id, username, opening_balance):
    """
    Alias for start_shift to support auth/shifts.py consumers.
    """
    return start_shift(username, opening_balance)

def get_active_shift(user):
    """
    Get active shift for user (username or user_id).
    """
    query = {"status": "Active"}
    # Try to match either user field (username) or user_id field
    # But for now, since we write "user": username, we query "user": username
    if isinstance(user, dict):
        user = user.get('username')
    
    query["user"] = user
    return shifts_col.find_one(query)

def get_all_shifts():
    """
    Get all shifts sorted by start time descending.
    """
    return list(shifts_col.find().sort("start_time", -1))

def end_shift(shift_id, closing_cash):
    """
    Ends the shift, calculates totals, and updates status.
    """
    shift = shifts_col.find_one({"_id": ObjectId(shift_id)})
    if not shift:
        return None
        
    user = shift['user']
    start_time = shift['start_time']
    end_time = datetime.now()
    
    # Calculate Sales for this shift: filter by shift_id first, fallback to time+user range
    # Query both string and ObjectId representations to handle legacy data
    shift_id_obj = shift["_id"]
    sales = list(orders_col.find({
        "shift_id": {"$in": [str(shift_id_obj), shift_id_obj]},
        "status": "Completed"
    }))
    # Fallback: if no orders tagged with shift_id, use time+user range
    if not sales:
        sales_query = {
            "updated_at": {"$gte": start_time, "$lte": end_time},
            "status": "Completed"
        }
        # Try to narrow by user field if available
        if isinstance(user, str):
            sales_query["$or"] = [{"waiter": user}, {"user": user}]
        sales = list(orders_col.find(sales_query))
    
    total_sales = sum(o.get('grand_total', 0) for o in sales)
    
    # Calculate Cash Sales specifically
    cash_sales = 0
    card_sales = 0
    for s in sales:
        if s.get('payment_method') == 'Cash':
            cash_sales += s.get('grand_total', 0)
        else:
            card_sales += s.get('grand_total', 0)

    # Calculate Expenses — filter by shift_id if recorded, else by time + user
    expenses = list(expenses_col.find({
        "shift_id": {"$in": [str(shift_id_obj), shift_id_obj]}
    }))
    if not expenses:
        exp_query = {"timestamp": {"$gte": start_time, "$lte": end_time}}
        if isinstance(user, str):
            exp_query["$or"] = [{"user": user}, {"recorded_by": user}]
        expenses = list(expenses_col.find(exp_query))
    total_expenses = sum(e.get('amount', 0) for e in expenses)
    
    # Expected Cash = Opening Cash + Cash Sales - Expenses
    expected_cash = shift.get('opening_cash', 0) + cash_sales - total_expenses
    
    cash_difference = closing_cash - expected_cash
    
    update_data = {
        "end_time": end_time,
        "status": "Closed",
        "closing_cash": closing_cash,
        "total_sales": total_sales,
        "total_cash_sales": cash_sales,
        "total_card_sales": card_sales,
        "total_expenses": total_expenses,
        "expected_cash": expected_cash,
        "cash_difference": cash_difference
    }
    
    shifts_col.update_one({"_id": ObjectId(shift_id)}, {"$set": update_data})
    
    return cash_difference

def update_shift_totals(shift_id, cash_inc=0.0, card_inc=0.0, expense_inc=0.0):
    """
    Increment shift totals when a sale or expense is recorded.
    """
    if not shift_id:
        return

    inc_data = {}

    if cash_inc != 0:
        inc_data["total_cash_sales"] = cash_inc
    if card_inc != 0:
        inc_data["total_card_sales"] = card_inc
    if cash_inc != 0 or card_inc != 0:
        inc_data["total_sales"] = cash_inc + card_inc
    if expense_inc != 0:
        inc_data["total_expenses"] = expense_inc

    if inc_data:
        try:
            _sid = ObjectId(shift_id)
        except Exception:
            _sid = shift_id
        shifts_col.update_one(
            {"_id": _sid},
            {"$inc": inc_data}
        )
