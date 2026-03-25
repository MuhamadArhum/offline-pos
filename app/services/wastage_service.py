"""
Wastage Tracking CRUD Operations
Records and analyzes kitchen wastage
"""
from app.core.database import wastage_col, inventory_col
from datetime import datetime, timedelta
from bson import ObjectId


class WastageReason:
    EXPIRED = "Expired"
    SPOILED = "Spoiled"
    OVERCOOKED = "Overcooked"
    DROPPED = "Dropped"
    WRONG_ORDER = "Wrong Order"
    CUSTOMER_RETURN = "Customer Return"
    PREPARATION = "Preparation Waste"
    DAMAGED = "Damaged"
    OTHER = "Other"

def get_wastage_reasons():
    """Get list of standard wastage reasons"""
    return [
        WastageReason.EXPIRED,
        WastageReason.SPOILED,
        WastageReason.OVERCOOKED,
        WastageReason.DROPPED,
        WastageReason.WRONG_ORDER,
        WastageReason.CUSTOMER_RETURN,
        WastageReason.PREPARATION,
        WastageReason.DAMAGED,
        WastageReason.OTHER
    ]


def record_wastage(item_name, quantity, unit, reason, user_id, notes="", cost_per_unit=0):
    """
    Record a wastage entry

    Args:
        item_name: Name of item wasted
        quantity: Quantity wasted
        unit: Unit of measurement
        reason: Reason for wastage
        user_id: User recording the wastage
        notes: Additional notes
        cost_per_unit: Cost per unit for value calculation
    """
    try:
        if cost_per_unit == 0:
            inv_item = inventory_col.find_one({"item_name": item_name})
            if inv_item:
                cost_per_unit = inv_item.get("cost_per_unit", 0)

        wastage = {
            "item_name": item_name,
            "quantity": quantity,
            "unit": unit,
            "reason": reason,
            "notes": notes,
            "cost_per_unit": cost_per_unit,
            "total_cost": quantity * cost_per_unit,
            "recorded_by": user_id,
            "recorded_at": datetime.now(),
            "shift_date": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        }

        result = wastage_col.insert_one(wastage)

        inventory_col.update_one(
            {"item_name": item_name},
            {"$inc": {"qty": -quantity}}
        )

        from app.services.inventory_service import log_stock_movement
        log_stock_movement(item_name, -quantity, f"Wastage: {reason}", str(user_id))

        return result.inserted_id
    except Exception as e:
        print(f"[ERROR] record_wastage: {e}")
        return None


def get_wastage_paginated(skip=0, limit=20):
    """Get all wastage records with pagination"""
    try:
        total = wastage_col.count_documents({})
        items = list(wastage_col.find().sort("recorded_at", -1).skip(skip).limit(limit))
        return items, total
    except Exception as e:
        print(f"[ERROR] get_wastage_paginated: {e}")
        return [], 0

def get_wastage_today():
    """Get today's wastage records"""
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return list(wastage_col.find(
            {"shift_date": today}
        ).sort("recorded_at", -1))
    except Exception as e:
        print(f"[ERROR] get_wastage_today: {e}")
        return []


def get_wastage_by_date_range(start_date, end_date):
    """Get wastage records for a date range"""
    try:
        return list(wastage_col.find({
            "recorded_at": {
                "$gte": start_date,
                "$lte": end_date
            }
        }).sort("recorded_at", -1))
    except Exception as e:
        print(f"[ERROR] get_wastage_by_date_range: {e}")
        return []


def get_wastage_summary(start_date=None, end_date=None):
    """
    Get wastage summary with totals by reason and item

    Returns dict with:
        - total_cost
        - by_reason: {reason: {count, cost}}
        - by_item: {item: {count, cost}}
    """
    try:
        query = {}
        if start_date and end_date:
            query["recorded_at"] = {"$gte": start_date, "$lte": end_date}

        wastage_records = list(wastage_col.find(query))

        summary = {
            "total_cost": 0,
            "total_items": 0,
            "by_reason": {},
            "by_item": {}
        }

        for r in wastage_records:
            summary["total_cost"] += r.get("total_cost", 0)
            summary["total_items"] += 1

            reason = r.get("reason", "Unknown")
            if reason not in summary["by_reason"]:
                summary["by_reason"][reason] = {"count": 0, "cost": 0}
            summary["by_reason"][reason]["count"] += 1
            summary["by_reason"][reason]["cost"] += r.get("total_cost", 0)

            item = r.get("item_name", "Unknown")
            if item not in summary["by_item"]:
                summary["by_item"][item] = {"count": 0, "cost": 0}
            summary["by_item"][item]["count"] += 1
            summary["by_item"][item]["cost"] += r.get("total_cost", 0)

        return summary
    except Exception as e:
        print(f"[ERROR] get_wastage_summary: {e}")
        return {"total_cost": 0, "total_items": 0, "by_reason": {}, "by_item": {}}


def get_weekly_wastage_trend():
    """Get wastage trend for the last 7 days"""
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)

        pipeline = [
            {"$match": {"recorded_at": {"$gte": week_ago}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$recorded_at"}},
                "total_cost": {"$sum": "$total_cost"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]

        return list(wastage_col.aggregate(pipeline))
    except Exception as e:
        print(f"[ERROR] get_weekly_wastage_trend: {e}")
        return []


def get_top_wasted_items(limit=10, days=30):
    """Get most wasted items"""
    try:
        start_date = datetime.now() - timedelta(days=days)

        pipeline = [
            {"$match": {"recorded_at": {"$gte": start_date}}},
            {"$group": {
                "_id": "$item_name",
                "total_quantity": {"$sum": "$quantity"},
                "total_cost": {"$sum": "$total_cost"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"total_cost": -1}},
            {"$limit": limit}
        ]

        return list(wastage_col.aggregate(pipeline))
    except Exception as e:
        print(f"[ERROR] get_top_wasted_items: {e}")
        return []


def delete_wastage_record(wastage_id, restore_inventory=True):
    """Delete a wastage record and optionally restore inventory"""
    try:
        if isinstance(wastage_id, str):
            wastage_id = ObjectId(wastage_id)

        wastage = wastage_col.find_one({"_id": wastage_id})
        if not wastage:
            return False

        if restore_inventory:
            inventory_col.update_one(
                {"item_name": wastage.get("item_name")},
                {"$inc": {"qty": wastage.get("quantity", 0)}}
            )

        wastage_col.delete_one({"_id": wastage_id})
        return True
    except Exception as e:
        print(f"[ERROR] delete_wastage_record: {e}")
        return False


def get_monthly_wastage_cost():
    """Get total wastage cost for current month"""
    try:
        today = datetime.now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = wastage_col.aggregate([
            {"$match": {"recorded_at": {"$gte": month_start}}},
            {"$group": {"_id": None, "total": {"$sum": "$total_cost"}}}
        ])

        total = list(result)
        return total[0]["total"] if total else 0
    except Exception as e:
        print(f"[ERROR] get_monthly_wastage_cost: {e}")
        return 0
