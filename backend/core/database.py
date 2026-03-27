import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from backend.core.offline_manager import OfflineManager

# Load environment variables
if getattr(sys, 'frozen', False):
    base_path = Path(sys.executable).parent
    if (base_path / "_internal").exists():
        base_path = base_path / "_internal"
else:
    base_path = Path(__file__).resolve().parent.parent.parent

load_dotenv(base_path / ".env")

# Initialize Offline Manager
# This ensures we always have a connection to the Local MongoDB.
# The OfflineManager also handles background syncing to the Cloud if configured.
offline_manager = OfflineManager()

# EXPLICITLY use the Local Database for all application operations.
# This ensures the application works 100% offline without waiting for network timeouts.
db = offline_manager.local_db

# Collections - Core
users_col = db["users"]
menu_col = db["menu_items"]
inventory_col = db["inventory"]
stock_logs_col = db["stock_logs"]
shifts_col = db["shifts"]
counters_col = db["counters"]
audit_logs_col = db["audit_logs"]
expenses_col = db["expenses"]
orders_col = db["orders"]
sales_col = db["sales"]
sync_queue_col = db["sync_queue"]

# Collections - Phase 1 (Core Business)
customers_col = db["customers"]
order_holds_col = db["order_holds"]
refunds_col = db["refunds"]
modifiers_col = db["modifiers"]

# Collections - Phase 2 (Inventory Management)
recipes_col = db["recipes"]
suppliers_col = db["suppliers"]
purchase_orders_col = db["purchase_orders"]
grn_col = db["grn"]
supplier_ledger_col = db["supplier_ledger"]
wastage_col = db["wastage"]

# Collections - Phase 3 (Growth Features)
online_orders_col = db["online_orders"]
delivery_col = db["deliveries"]
riders_col = db["riders"]
reservations_col = db["reservations"]
loyalty_col = db["loyalty"]
loyalty_transactions_col = db["loyalty_transactions"]

# Collections - Phase 4 (Analytics)
daily_analytics_col = db["daily_analytics"]
item_analytics_col = db["item_analytics"]

# ── Indexes — ensure fast queries ────────────────────────────────────────────
def _ensure_indexes():
    """Create indexes for frequently queried fields. Safe to call on every startup."""
    try:
        # Orders — most queried collection
        orders_col.create_index([("created_at", -1)])
        orders_col.create_index([("status", 1)])
        orders_col.create_index([("order_type", 1)])
        orders_col.create_index([("invoice_no", 1)], unique=True)
        orders_col.create_index([("delivery_status", 1)], sparse=True)

        # Inventory
        inventory_col.create_index([("item_name", 1)])
        inventory_col.create_index([("category", 1)])
        inventory_col.create_index([("qty", 1)])

        # Stock logs
        stock_logs_col.create_index([("item_name", 1)])
        stock_logs_col.create_index([("timestamp", -1)])

        # Users
        users_col.create_index([("username", 1)], unique=True)
        users_col.create_index([("role", 1)])

        # Menu items
        menu_col.create_index([("name", 1)])
        menu_col.create_index([("category", 1)])
        menu_col.create_index([("available", 1)])

        # Shifts
        shifts_col.create_index([("opened_at", -1)])
        shifts_col.create_index([("status", 1)])

        # Wastage
        wastage_col.create_index([("recorded_at", -1)])
        wastage_col.create_index([("item_name", 1)])

        # Audit logs
        audit_logs_col.create_index([("timestamp", -1)])
        audit_logs_col.create_index([("user", 1)])

        # Customers
        customers_col.create_index([("phone", 1)], sparse=True)

    except Exception as _idx_err:
        print(f"[DB] Index setup warning: {_idx_err}")

_ensure_indexes()
