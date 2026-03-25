"""
Role-Based Access Control (RBAC) System
Defines permissions for each role in the POS system
"""

# Role definitions with their allowed modules & actions
ROLE_PERMISSIONS = {
    "admin": ["all"],  # Admin has access to everything
    "manager": [
        "billing", "menu", "inventory", "reports",
        "tables", "kitchen", "expenses", "shifts",
        "customers", "orders", "recipes", "suppliers", "wastage", "modifiers",
        "refund_order", "day_close", "change_price", "manage_pos", "audit_logs"
    ],
    "cashier": [
        "billing", "tables", "kitchen", "shifts", "customers", "orders"
    ],
    "kitchen_supervisor": [
        "kitchen", "order_history", "wastage"
    ],
    "waiter": [
        "tables", "menu"
    ],
    "rider": [
        "orders"
    ]
}

# Module/Action names mapping for UI Display
MODULE_NAMES = {
    # Modules
    "billing": "New Order (POS)",
    "tables": "Table Management",
    "kitchen": "Kitchen Display",
    "menu": "Menu Management",
    "inventory": "Inventory Control",
    "users": "User Management",
    "reports": "Sales Reports",
    "expenses": "Expense Management",
    "settings": "System Settings",
    "shifts": "Shift Management",
    "order_history": "Order History",
    
    # Phase 1 & 2 Modules
    "customers": "CRM (Customers)",
    "orders": "Order Tracking",
    "recipes": "Recipe Management",
    "suppliers": "Supplier Management",
    "wastage": "Wastage Recording",
    
    # Actions
    "refund_order": "Process Refunds",
    "day_close": "Perform Day Close (Z-Report)",
    "change_price": "Modify Item Prices",
    "manage_permissions": "Manage User Permissions",
    "audit_logs": "View Audit Logs",
    "manage_pos": "Manage Purchase Orders"
}

def has_permission(user, module):
    """
    Check if a user has permission to access a module or perform an action
    
    Args:
        user: User document from database
        module: Permission key (e.g., 'billing', 'refund_order')
    
    Returns:
        bool: True if user has access, False otherwise
    """
    if not user: return False
    
    role = str(user.get("role", "")).strip().lower()
    
    # Check custom permissions first (if set by admin)
    custom_perms = user.get("custom_permissions", [])
    if custom_perms and module in custom_perms:
        return True
    
    # Check role-based permissions
    allowed_modules = ROLE_PERMISSIONS.get(role, [])
    
    # Admin has access to everything
    if "all" in allowed_modules:
        return True
    
    return module in allowed_modules

def get_user_permissions(user):
    """
    Get list of all permissions a user has
    """
    role = str(user.get("role", "")).strip().lower()
    
    # Check custom permissions first
    custom_perms = user.get("custom_permissions", [])
    if custom_perms:
        return custom_perms
    
    # Get role-based permissions
    allowed_modules = ROLE_PERMISSIONS.get(role, [])
    
    # If admin, return all keys
    if "all" in allowed_modules:
        return list(MODULE_NAMES.keys())
    
    return allowed_modules

def get_all_roles():
    """Get list of all available roles"""
    return list(ROLE_PERMISSIONS.keys())

def get_role_display_name(role):
    """Get display name for a role"""
    return role.capitalize()
