"""
Recipe Management CRUD Operations
Links menu items to ingredients for automatic inventory deduction
"""
from backend.core.database import recipes_col, menu_col, inventory_col
from datetime import datetime
from bson import ObjectId


def add_recipe(menu_item_id, ingredients):
    """
    Add a recipe for a menu item

    Args:
        menu_item_id: ID of menu item
        ingredients: List of dicts [{item_name, quantity, unit}]

    Example:
        add_recipe("burger_id", [
            {"item_name": "Beef Patty", "quantity": 1, "unit": "pcs"},
            {"item_name": "Burger Bun", "quantity": 1, "unit": "pcs"},
            {"item_name": "Cheese Slice", "quantity": 1, "unit": "pcs"},
        ])
    """
    try:
        if isinstance(menu_item_id, str):
            menu_item_id = ObjectId(menu_item_id)

        menu_item = menu_col.find_one({"_id": menu_item_id})
        if not menu_item:
            raise ValueError("Menu item not found")

        recipe = {
            "menu_item_id": menu_item_id,
            "menu_item_name": menu_item.get("name"),
            "ingredients": ingredients,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "is_active": True
        }

        existing = recipes_col.find_one({"menu_item_id": menu_item_id})
        if existing:
            recipes_col.update_one(
                {"_id": existing["_id"]},
                {"$set": {"ingredients": ingredients, "updated_at": datetime.now()}}
            )
            return existing["_id"]

        result = recipes_col.insert_one(recipe)
        return result.inserted_id
    except Exception as e:
        print(f"[ERROR] add_recipe: {e}")
        return None


def get_recipe(menu_item_id):
    """Get recipe for a menu item"""
    try:
        if isinstance(menu_item_id, str):
            menu_item_id = ObjectId(menu_item_id)
        return recipes_col.find_one({"menu_item_id": menu_item_id, "is_active": True})
    except Exception as e:
        print(f"[ERROR] get_recipe: {e}")
        return None


def get_recipe_by_name(menu_item_name):
    """Get recipe by menu item name"""
    try:
        return recipes_col.find_one({"menu_item_name": menu_item_name, "is_active": True})
    except Exception as e:
        print(f"[ERROR] get_recipe_by_name: {e}")
        return None


def get_all_recipes():
    """Get all active recipes"""
    try:
        return list(recipes_col.find({"is_active": True}))
    except Exception as e:
        print(f"[ERROR] get_all_recipes: {e}")
        return []


def update_recipe(recipe_id, ingredients):
    """Update recipe ingredients"""
    try:
        if isinstance(recipe_id, str):
            recipe_id = ObjectId(recipe_id)

        recipes_col.update_one(
            {"_id": recipe_id},
            {
                "$set": {
                    "ingredients": ingredients,
                    "updated_at": datetime.now()
                }
            }
        )
        return True
    except Exception as e:
        print(f"[ERROR] update_recipe: {e}")
        return False


def delete_recipe(menu_item_id):
    """Soft delete a recipe"""
    try:
        if isinstance(menu_item_id, str):
            menu_item_id = ObjectId(menu_item_id)

        recipes_col.update_one(
            {"menu_item_id": menu_item_id},
            {"$set": {"is_active": False, "updated_at": datetime.now()}}
        )
        return True
    except Exception as e:
        print(f"[ERROR] delete_recipe: {e}")
        return False


def calculate_ingredients_for_order(cart):
    """
    Calculate total ingredients needed for an order

    Args:
        cart: Dict of {item_name: {qty, price}}

    Returns:
        Dict of {ingredient_name: total_quantity_needed}
    """
    total_ingredients = {}

    for item_name, data in cart.items():
        qty = data.get("qty", 1)
        recipe = get_recipe_by_name(item_name)

        if recipe:
            for ingredient in recipe.get("ingredients", []):
                ing_name = ingredient.get("item_name")
                ing_qty = ingredient.get("quantity", 0) * qty

                if ing_name in total_ingredients:
                    total_ingredients[ing_name] += ing_qty
                else:
                    total_ingredients[ing_name] = ing_qty

    return total_ingredients


def check_ingredient_availability(cart):
    """
    Check if all ingredients are available for an order

    Args:
        cart: Order cart dict

    Returns:
        tuple: (is_available: bool, missing_items: list)
    """
    try:
        needed = calculate_ingredients_for_order(cart)
        missing = []

        for ing_name, qty_needed in needed.items():
            stock = inventory_col.find_one({"item_name": ing_name})
            available = stock.get("qty", 0) if stock else 0

            if available < qty_needed:
                missing.append({
                    "item": ing_name,
                    "needed": qty_needed,
                    "available": available,
                    "shortage": qty_needed - available
                })

        return len(missing) == 0, missing
    except Exception as e:
        print(f"[ERROR] check_ingredient_availability: {e}")
        return True, []  # Fail open so sales aren't blocked on DB error


def deduct_recipe_ingredients(cart):
    """
    Deduct ingredients from inventory based on recipe

    Args:
        cart: Order cart dict

    Returns:
        List of deducted items with quantities
    """
    try:
        ingredients = calculate_ingredients_for_order(cart)
        deducted = []

        for ing_name, qty in ingredients.items():
            inventory_col.update_one(
                {"item_name": ing_name},
                {"$inc": {"qty": -qty}}
            )
            deducted.append({"item": ing_name, "quantity": qty})

        return deducted
    except Exception as e:
        print(f"[ERROR] deduct_recipe_ingredients: {e}")
        return []


def get_menu_items_without_recipe():
    """Get menu items that don't have recipes"""
    try:
        all_menu = list(menu_col.find({"available": True}))
        recipes_menu_ids = recipes_col.distinct("menu_item_id", {"is_active": True})

        without_recipe = []
        for item in all_menu:
            if item["_id"] not in recipes_menu_ids:
                without_recipe.append(item)

        return without_recipe
    except Exception as e:
        print(f"[ERROR] get_menu_items_without_recipe: {e}")
        return []


def get_recipe_cost(menu_item_id):
    """
    Calculate the ingredient cost for a menu item

    Args:
        menu_item_id: Menu item ID

    Returns:
        Total cost of ingredients
    """
    try:
        recipe = get_recipe(menu_item_id)
        if not recipe:
            return 0

        total_cost = 0
        for ingredient in recipe.get("ingredients", []):
            ing_name = ingredient.get("item_name")
            qty = ingredient.get("quantity", 0)

            stock = inventory_col.find_one({"item_name": ing_name})
            if stock:
                unit_cost = stock.get("cost_per_unit", 0)
                total_cost += unit_cost * qty

        return total_cost
    except Exception as e:
        print(f"[ERROR] get_recipe_cost: {e}")
        return 0


def get_profit_margin(menu_item_id):
    """Calculate profit margin for a menu item"""
    try:
        if isinstance(menu_item_id, str):
            menu_item_id = ObjectId(menu_item_id)

        menu_item = menu_col.find_one({"_id": menu_item_id})
        if not menu_item:
            return None

        selling_price = menu_item.get("price", 0)
        cost = get_recipe_cost(menu_item_id)

        if selling_price > 0:
            profit = selling_price - cost
            margin = (profit / selling_price) * 100
            return {
                "selling_price": selling_price,
                "cost": cost,
                "profit": profit,
                "margin_percent": margin
            }

        return None
    except Exception as e:
        print(f"[ERROR] get_profit_margin: {e}")
        return None
