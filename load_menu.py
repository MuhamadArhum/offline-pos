"""
Excel se Menu DB mein load karne ka script.
Usage: .venv/Scripts/python load_menu.py
       .venv/Scripts/python load_menu.py --clear
"""

import sys
import os
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.core.database import menu_col
from backend.core.menu_cache import MenuCache

EXCEL_FILE = "Combined Menu Rates Updated (FC & Restaurant) 19.03.2026.xlsx"


def load_menu_from_excel(clear_existing=False):
    print("\n" + "="*55)
    print("   MENU EXCEL IMPORT TOOL")
    print("="*55 + "\n")

    # -- 1. Excel file read karo ---------------------------------
    if not os.path.exists(EXCEL_FILE):
        print(f"[ERROR] File nahi mili: {EXCEL_FILE}")
        sys.exit(1)

    df = pd.read_excel(EXCEL_FILE, sheet_name=0, header=None)
    df = df.iloc[2:].copy()
    df.columns = ['_', 'HeadCode', 'HeadName', 'ItemCode', 'ItemName', 'RateFull', 'Half']
    df = df.dropna(subset=['ItemName', 'RateFull'])
    df = df[df['ItemName'].astype(str).str.strip() != '']

    df['HeadCode'] = df['HeadCode'].fillna(0).astype(int).astype(str)
    df['ItemCode'] = df['ItemCode'].fillna(0).astype(int).astype(str)
    df['RateFull'] = pd.to_numeric(df['RateFull'], errors='coerce').fillna(0)
    df['Half']     = pd.to_numeric(df['Half'],     errors='coerce').fillna(0)
    df['HeadName'] = df['HeadName'].astype(str).str.strip()
    df['ItemName'] = df['ItemName'].astype(str).str.strip()

    # Composite code: HeadCode-ItemCode, duplicates pe row index suffix
    df['CompositeCode'] = df['HeadCode'] + '-' + df['ItemCode']
    seen_codes = {}
    composite_codes = []
    for idx, code in enumerate(df['CompositeCode']):
        if code in seen_codes:
            seen_codes[code] += 1
            composite_codes.append(f"{code}-{seen_codes[code]}")
        else:
            seen_codes[code] = 0
            composite_codes.append(code)
    df['CompositeCode'] = composite_codes

    print(f"Excel mein mila:")
    print(f"  Total items : {len(df)}")
    print(f"  Categories  : {', '.join(df['HeadName'].unique())}\n")

    # -- 2. Existing data handle karo ----------------------------
    existing_count = menu_col.count_documents({})

    if clear_existing and existing_count > 0:
        confirm = input(f"  [!] DB mein pehle se {existing_count} items hain. Delete karein? (yes/no): ").strip().lower()
        if confirm == 'yes':
            menu_col.delete_many({})
            print(f"  Purane {existing_count} items delete ho gaye.\n")
        else:
            print("  Delete cancel — sirf naye items add honge (duplicates skip).\n")
            clear_existing = False

    # -- 3. Items insert karo ------------------------------------
    inserted = 0
    skipped  = 0
    errors   = 0

    for _, row in df.iterrows():
        name      = row['ItemName']
        price     = float(row['RateFull'])
        category  = row['HeadName']
        code      = row['CompositeCode']
        half_price = float(row['Half']) if row['Half'] > 0 else None

        # Duplicate check (same name + category)
        if not clear_existing:
            exists = menu_col.find_one({"name": name, "category": category})
            if exists:
                skipped += 1
                continue

        doc = {
            "name":        name,
            "price":       price,
            "category":    category,
            "code":        code,
            "available":   True,
            "is_combo":    False,
            "combo_items": [],
            "has_half":    bool(half_price),
        }
        if half_price:
            doc["half_price"] = half_price

        try:
            menu_col.insert_one(doc)
            inserted += 1
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
            errors += 1

    # -- 4. Categories collection sync karo ---------------------
    from backend.core.database import db
    categories_col = db["categories"]

    # Excel ke categories ke liye color/section mapping
    CAT_META = {
        "Chinese":     {"color": "#3B82F6", "section": "kitchen"},
        "Desi":        {"color": "#F97316", "section": "kitchen"},
        "BBQ":         {"color": "#EF4444", "section": "kitchen"},
        "Continental": {"color": "#10B981", "section": "kitchen"},
        "Banquet":     {"color": "#8B5CF6", "section": "kitchen"},
        "Fast Food":   {"color": "#F59E0B", "section": "kitchen"},
        "Tandoor":     {"color": "#92400E", "section": "kitchen"},
        "Extras":      {"color": "#6B7280", "section": "kitchen"},
        "Bar":         {"color": "#0EA5E9", "section": "bar"},
        "Deals":       {"color": "#059669", "section": "kitchen"},
    }

    cat_inserted = 0
    cat_skipped  = 0
    menu_categories = df['HeadName'].unique()

    for cat_name in menu_categories:
        if categories_col.find_one({"name": cat_name}):
            cat_skipped += 1
            continue
        meta = CAT_META.get(cat_name, {"color": "#3498db", "section": "kitchen"})
        categories_col.insert_one({
            "name":         cat_name,
            "description":  f"{cat_name} items",
            "color":        meta["color"],
            "section":      meta["section"],
            "printer_role": f"kot-{meta['section']}",
            "created_at":   __import__('datetime').datetime.now(),
            "is_active":    True,
        })
        cat_inserted += 1

    print(f"\nCategories: {cat_inserted} inserted, {cat_skipped} already existed")

    # -- 5. Cache invalidate karo --------------------------------
    MenuCache().invalidate()

    # -- 5. Summary ----------------------------------------------
    print("-"*55)
    print(f"  Inserted  : {inserted}")
    print(f"  Skipped   : {skipped}  (duplicates)")
    print(f"  Errors    : {errors}")
    print(f"  Total DB  : {menu_col.count_documents({})}")
    print("-"*55)

    print("\nCategory wise breakdown:")
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort":  {"_id": 1}}
    ]
    for doc in menu_col.aggregate(pipeline):
        print(f"  {doc['_id']:<20} {doc['count']} items")

    print("\n  Done! Menu DB mein load ho gaya.\n")


if __name__ == "__main__":
    clear = "--clear" in sys.argv
    load_menu_from_excel(clear_existing=clear)
