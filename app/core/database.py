import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from app.core.offline_manager import OfflineManager

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
