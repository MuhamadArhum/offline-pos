from typing import List, Dict, Any, Optional
from datetime import datetime
from bson.objectid import ObjectId
from app.core.database import db
from app.core.logger import logger

# We now use 'users' collection for riders
users_col = db["users"]
orders_col = db["orders"]

def get_riders(active_only: bool = False) -> List[Dict[str, Any]]:
    try:
        query = {"role": "Rider"}
        if active_only:
            query["active"] = True
            
        riders = list(users_col.find(query).sort("username", 1))
        
        # Normalize fields for UI compatibility
        for r in riders:
            r['name'] = r.get('username')
            r['status'] = 'Active' if r.get('active') else 'Inactive'
            
        return riders
    except Exception as e:
        logger.error(f"Error fetching riders from users: {e}")
        return []

def assign_rider_to_order(order_id: str, rider_id: str, rider_name: str) -> bool:
    try:
        orders_col.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "rider_id": rider_id,
                "rider_name": rider_name,
                "delivery_status": "Assigned",
                "assigned_at": datetime.now()
            }}
        )
        return True
    except Exception as e:
        logger.error(f"Error assigning rider to order {order_id}: {e}")
        return False

def update_delivery_status(order_id: str, status: str) -> bool:
    """
    Status options: 'Assigned', 'Out for Delivery', 'Delivered', 'Cancelled'
    """
    try:
        update_data = {
            "delivery_status": status,
            "updated_at": datetime.now()
        }
        
        if status == "Delivered":
            update_data["status"] = "Completed"
            update_data["completed_at"] = datetime.now()
            
            # Increment rider stats
            order = orders_col.find_one({"_id": ObjectId(order_id)})
            if order and order.get("rider_id"):
                try:
                    users_col.update_one(
                        {"_id": ObjectId(order["rider_id"])},
                        {"$inc": {"total_deliveries": 1}}
                    )
                except Exception as rider_err:
                    logger.warning(f"Could not update rider stats for rider_id={order['rider_id']}: {rider_err}")

        orders_col.update_one({"_id": ObjectId(order_id)}, {"$set": update_data})
        return True
    except Exception as e:
        logger.error(f"Error updating delivery status for order {order_id}: {e}")
        return False

def get_delivery_orders(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        query = {"order_type": "Delivery"}
        
        if status_filter:
            if status_filter == "Pending":
                query["$or"] = [
                    {"delivery_status": "Pending"},
                    {"delivery_status": {"$exists": False}},
                    {"delivery_status": None}
                ]
                query["status"] = {"$nin": ["Completed", "Void", "Refunded"]}
                
            elif status_filter == "Active":
                 query["delivery_status"] = {"$in": ["Assigned", "Out for Delivery"]}
                 
            elif status_filter == "History":
                 query["delivery_status"] = {"$in": ["Delivered", "Cancelled", "Returned"]}
                 
        return list(orders_col.find(query).sort("created_at", -1))
    except Exception as e:
        logger.error(f"Error fetching delivery orders: {e}")
        return []
