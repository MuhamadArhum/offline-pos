from backend.core.database import db
from datetime import datetime
from pymongo.errors import OperationFailure
from backend.core.logger import get_logger

logger = get_logger("InventoryService")

inventory_col = db["inventory"]
stock_logs_col = db["stock_logs"]

# Cache: once we detect transactions are not supported, skip future attempts
_transactions_supported = True

def log_stock_movement(item_name, change, reason, user="System", session=None):
    """Log stock movement history"""
    try:
        item = inventory_col.find_one({"item_name": item_name}, session=session)
        current_qty = item.get('qty', 0) if item else 0
        cost_per_unit = item.get('cost_per_unit', 0) if item else 0

        previous_qty = current_qty - change

        log = {
            "item_name": item_name,
            "change": change,
            "previous_qty": previous_qty,
            "new_qty": current_qty,
            "cost_per_unit": cost_per_unit,
            "reason": reason,
            "user": user,
            "timestamp": datetime.now()
        }
        stock_logs_col.insert_one(log, session=session)
    except Exception as e:
        logger.error(f"[ERROR] log_stock_movement: {e}")

def get_batches(item_name):
    """Get all batches for an item"""
    try:
        item = inventory_col.find_one({"item_name": item_name})
        if not item: return []
        return item.get("batches", [])
    except Exception as e:
        logger.error(f"[ERROR] get_batches: {e}")
        return []

def remove_batch(item_name, batch_idx, user="Admin"):
    """Remove a specific batch by index"""
    try:
        item = inventory_col.find_one({"item_name": item_name})
        if not item: return False

        batches = item.get("batches", [])
        if batch_idx < 0 or batch_idx >= len(batches):
            return False

        batch = batches.pop(batch_idx)
        qty_removed = batch.get("qty", 0)

        inventory_col.update_one(
            {"item_name": item_name},
            {
                "$set": {"batches": batches},
                "$inc": {"qty": -qty_removed}
            }
        )

        log_stock_movement(item_name, -qty_removed, f"Batch Removed: {batch.get('batch_no', 'Unknown')}", user)
        return True
    except Exception as e:
        logger.error(f"[ERROR] remove_batch: {e}")
        return False

def reconcile_stock(item_name, physical_qty, user="Admin"):
    """
    Adjust stock to match physical count.
    Records variance.
    """
    try:
        item = inventory_col.find_one({"item_name": item_name})
        if not item: return False

        current_qty = item.get("qty", 0)
        variance = physical_qty - current_qty

        if variance == 0:
            return True  # No change

        if variance < 0:
            # Stock Missing - Deduct using FIFO
            deduct_stock(item_name, abs(variance), "Stock Take Variance", user)
        else:
            # Stock Surplus - Add new 'Adjustment' batch
            batch_no = f"ADJ-{datetime.now().strftime('%Y%m%d')}"
            add_stock(item_name, variance, batch_no=batch_no, user=user)

        return True
    except Exception as e:
        logger.error(f"[ERROR] reconcile_stock: {e}")
        return False

def add_stock(item_name, qty, threshold=5, cost_per_unit=0, unit="pcs", user="Admin", supplier_id=None, batch_no=None, expiry_date=None, purchase_unit=None, conversion_factor=1, category="General"):
    """Add or update stock for an item with Batch & Unit support"""
    try:
        actual_qty = qty
        if purchase_unit and conversion_factor > 1:
            actual_qty = qty * conversion_factor

        update_data = {
            "$inc": {"qty": actual_qty},
            "$setOnInsert": {"threshold": threshold, "unit": unit}
        }

        set_fields = {}
        if cost_per_unit > 0:
            set_fields["cost_per_unit"] = cost_per_unit
        if supplier_id:
            set_fields["supplier_id"] = supplier_id
        if purchase_unit:
            set_fields["purchase_unit"] = purchase_unit
            set_fields["conversion_factor"] = conversion_factor
        if category:
            set_fields["category"] = category

        if set_fields:
            update_data["$set"] = set_fields

        if batch_no:
            batch = {
                "batch_no": batch_no,
                "qty": actual_qty,
                "expiry_date": expiry_date,
                "created_at": datetime.now()
            }
            update_data["$push"] = {"batches": batch}

        inventory_col.update_one(
            {"item_name": item_name},
            update_data,
            upsert=True
        )

        log_stock_movement(item_name, actual_qty, "Purchase/Restock", user)
    except Exception as e:
        logger.error(f"[ERROR] add_stock: {e}")

def restore_stock(item_name, qty, reason="Refund", user="System"):
    """Restore stock (e.g. for Refunds/Cancellations)"""
    try:
        inventory_col.update_one(
            {"item_name": item_name},
            {"$inc": {"qty": qty}}
        )
        log_stock_movement(item_name, qty, reason, user)
    except Exception as e:
        logger.error(f"[ERROR] restore_stock: {e}")

def deduct_stock(item_name, qty, reason="Sales", user="System"):
    """Deduct stock for an item using FIFO for batches with optional transaction support"""
    client = db.client
    
    def _perform_deduct(session=None):
        item = inventory_col.find_one({"item_name": item_name}, session=session)
        if not item:
            return
            
        # FIFO Logic: Deduct from oldest batches first
        remaining_to_deduct = qty
        batches = item.get("batches", [])
        
        # Sort batches by expiry (if exists) or created_at
        def sort_key(b):
            exp = b.get("expiry_date")
            if not exp:
                return datetime.max
            if isinstance(exp, str):
                try:
                    return datetime.strptime(exp, "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Invalid expiry_date format in batch: {exp}")
                    return datetime.max
            return exp
            
        batches.sort(key=sort_key)
        
        updated_batches = []
        
        for batch in batches:
            if remaining_to_deduct <= 0:
                updated_batches.append(batch)
                continue
                
            b_qty = batch.get("qty", 0)
            
            if b_qty > remaining_to_deduct:
                batch["qty"] = b_qty - remaining_to_deduct
                remaining_to_deduct = 0
                updated_batches.append(batch)
            else:
                remaining_to_deduct -= b_qty
                # Batch fully consumed, do not append to updated_batches
            
        # Update DB
        inventory_col.update_one(
            {"item_name": item_name},
            {
                "$inc": {"qty": -qty},
                "$set": {"batches": updated_batches}
            },
            session=session
        )
        log_stock_movement(item_name, -qty, reason, user, session=session)

    global _transactions_supported
    try:
        if _transactions_supported:
            # Attempt to use transaction
            with client.start_session() as session:
                with session.start_transaction():
                    _perform_deduct(session)
        else:
            _perform_deduct(None)
    except OperationFailure:
        # Standalone MongoDB - transactions not supported. Log once, then skip future attempts.
        if _transactions_supported:
            logger.warning("MongoDB transactions not supported (Standalone mode). Using atomic fallback.")
            _transactions_supported = False
        _perform_deduct(None)
    except Exception as e:
        logger.error(f"Error deducting stock for {item_name}: {e}")

def get_stock_history(item_name=None, limit=50, skip=0):
    """Get stock movement history with pagination"""
    try:
        query = {}
        if item_name:
            query["item_name"] = item_name

        total = stock_logs_col.count_documents(query)
        logs = list(stock_logs_col.find(query).sort("timestamp", -1).skip(skip).limit(limit))
        return logs, total
    except Exception as e:
        logger.error(f"[ERROR] get_stock_history: {e}")
        return [], 0

def get_inventory(query=None, skip=0, limit=0):
    """Get all inventory items. Always returns (list, total) tuple."""
    try:
        q = query or {}
        total = inventory_col.count_documents(q)
        cursor = inventory_col.find(q)

        if limit > 0:
            cursor = cursor.skip(skip).limit(limit)

        return list(cursor), total
    except Exception as e:
        logger.error(f"[ERROR] get_inventory: {e}")
        return [], 0

def get_inventory_item(item_name):
    """Get single inventory item by name"""
    try:
        return inventory_col.find_one({"item_name": item_name})
    except Exception as e:
        logger.error(f"[ERROR] get_inventory_item: {e}")
        return None

def delete_inventory_item(item_name):
    """Delete an inventory item by name"""
    try:
        result = inventory_col.delete_one({"item_name": item_name})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"[ERROR] delete_inventory_item: {e}")
        return False

def update_inventory_item(item_name, qty=None, threshold=None, cost_per_unit=None, unit=None, supplier_id=None, category=None):
    """Update inventory item details"""
    try:
        update_data = {}
        if qty is not None:
            update_data["qty"] = qty
        if threshold is not None:
            update_data["threshold"] = threshold
        if cost_per_unit is not None:
            update_data["cost_per_unit"] = cost_per_unit
        if unit is not None:
            update_data["unit"] = unit
        if supplier_id is not None:
            update_data["supplier_id"] = supplier_id
        if category is not None:
            update_data["category"] = category

        if update_data:
            inventory_col.update_one(
                {"item_name": item_name},
                {"$set": update_data}
            )
    except Exception as e:
        logger.error(f"[ERROR] update_inventory_item: {e}")

def process_sale_inventory(order_items):
    """
    Deduct inventory based on sold items (recipes or direct).
    Called when a sale is confirmed.
    """
    try:
        # Avoid circular import
        from backend.core.database import db
        recipes_col = db["recipes"]
        
        for item in order_items:
            # Handle both object and dict
            if isinstance(item, dict):
                item_name = item.get('name')
                qty_sold = float(item.get('qty', 0))
            else:
                item_name = item.name
                qty_sold = float(item.qty)

            # Check if recipe exists
            recipe = recipes_col.find_one({"name": item_name})

            if recipe:
                ingredients = recipe.get('ingredients', [])
                for ing in ingredients:
                    ing_name = ing.get('item_name')
                    ing_qty = float(ing.get('quantity', 0))
                    total_deduct = ing_qty * qty_sold
                    deduct_stock(ing_name, total_deduct, reason=f"Sale: {item_name}", user="System")
            else:
                # Direct deduction (if item exists in inventory)
                inv_item = inventory_col.find_one({"item_name": item_name})
                if inv_item:
                    deduct_stock(item_name, qty_sold, reason=f"Direct Sale: {item_name}", user="System")
    except Exception as e:
        logger.error(f"[ERROR] process_sale_inventory: {e}")

def low_stock_items():
    """Get items below threshold"""
    try:
        return list(
            inventory_col.find({
                "$expr": {"$lte": ["$qty", "$threshold"]}
            })
        )
    except Exception as e:
        logger.error(f"[ERROR] low_stock_items: {e}")
        return []

def get_inventory_value():
    """Get total inventory value"""
    try:
        items, _ = get_inventory()
        total = 0
        for item in items:
            qty = item.get("qty", 0)
            cost = item.get("cost_per_unit", 0)
            total += qty * cost
        return total
    except Exception as e:
        logger.error(f"[ERROR] get_inventory_value: {e}")
        return 0

def get_suppliers():
    """Get all suppliers"""
    try:
        return list(db.suppliers.find())
    except Exception as e:
        logger.error(f"[ERROR] get_suppliers: {e}")
        return []

def add_supplier(data):
    """Add new supplier"""
    try:
        db.suppliers.insert_one(data)
        return True
    except Exception as e:
        logger.error(f"[ERROR] add_supplier: {e}")
        return False

def delete_supplier(supplier_id):
    """Delete supplier by ID"""
    try:
        from bson.objectid import ObjectId
        db.suppliers.delete_one({"_id": ObjectId(supplier_id)})
        return True
    except Exception as e:
        logger.error(f"[ERROR] delete_supplier: {e}")
        return False
