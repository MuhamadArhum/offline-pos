import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from app.core.database import orders_col, inventory_col, expenses_col, wastage_col, recipes_col, audit_logs_col, shifts_col
from app.core.config import load_config, resolve_resource_path
from app.core.logger import get_logger
from bson.objectid import ObjectId

logger = get_logger("ReportService")

def get_shift_report_data(shift_id):
    """
    Get comprehensive report data for a specific shift.
    """
    if isinstance(shift_id, str):
        shift_id = ObjectId(shift_id)
        
    shift = shifts_col.find_one({"_id": shift_id})
    if not shift:
        return None
        
    start_time = shift.get('start_time')
    end_time = shift.get('end_time')
    
    # If shift is active, use current time as end time for report
    if not end_time:
        end_time = datetime.now()
        
    # Sales
    # Use shift_id if available in orders, otherwise fallback to time range
    # Query both ObjectId and string representations to handle any type stored
    sales_query = {"shift_id": {"$in": [shift_id, str(shift_id)]}, "status": "Completed"}
    sales = list(orders_col.find(sales_query))
    
    # If no sales found with shift_id but we have time range, try time range fallback
    # This helps with migration or if shift_id was missed
    if not sales and start_time:
         sales = list(orders_col.find({
            "updated_at": {"$gte": start_time, "$lte": end_time},
            "status": "Completed"
         }))
    
    total_sales = sum(o.get('grand_total', 0) for o in sales)
    cash_sales = sum(o.get('grand_total', 0) for o in sales if o.get('payment_method') == 'Cash')
    card_sales = sum(o.get('grand_total', 0) for o in sales if o.get('payment_method') != 'Cash')
    
    # Expenses
    # Use shift_id if available
    expenses = list(expenses_col.find({"shift_id": {"$in": [shift_id, str(shift_id)]}}))
    if not expenses and start_time:
        expenses = list(expenses_col.find({
            "timestamp": {"$gte": start_time, "$lte": end_time}
        }))
        
    total_expenses = sum(e.get('amount', 0) for e in expenses)
    
    # --- New: Shift Wise Item Sales ---
    item_sales = {}
    for sale in sales:
        for item in sale.get('items', []):
            name = item.get('name', 'Unknown')
            qty = item.get('qty', 0)
            total = item.get('price', 0) * qty
            
            if name in item_sales:
                item_sales[name]['qty'] += qty
                item_sales[name]['total'] += total
            else:
                item_sales[name] = {'qty': qty, 'total': total}
                
    # Convert to list and sort by qty
    top_items = sorted(
        [{'name': k, **v} for k, v in item_sales.items()],
        key=lambda x: x['qty'],
        reverse=True
    )
    
    return {
        "shift": shift,
        "sales": sales,
        "expenses": expenses,
        "total_sales": total_sales,
        "cash_sales": cash_sales,
        "card_sales": card_sales,
        "online_sales": total_sales - (cash_sales + card_sales), # Derived
        "total_expenses": total_expenses,
        "net_cash": (shift.get('opening_cash', 0) + cash_sales - total_expenses),
        "top_items": top_items # Added Item Report
    }

def generate_purchase_order(items, filename="purchase_order.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Add Logo if available
    config = load_config()
    logo_path = resolve_resource_path(config.get("logo_path"))
    if logo_path and os.path.exists(logo_path):
        try:
            # Scale logo
            im = Image(logo_path)
            # Aspect ratio check
            aspect = im.imageHeight / im.imageWidth
            target_w = 150
            target_h = target_w * aspect
            im.drawWidth = target_w
            im.drawHeight = target_h
            im.hAlign = 'CENTER'
            elements.append(im)
            elements.append(Spacer(1, 10))
        except Exception as e:
            print(f"Error adding logo to PDF: {e}")

    elements.append(Paragraph("Purchase Order / Low Stock Report", styles['Title']))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    data = [['Item Name', 'Current Qty', 'Threshold', 'Suggested Order']]
    
    for item in items:
        name = item.get('item_name', 'Unknown')
        qty = item.get('qty', 0)
        thresh = item.get('threshold', 5)
        suggested = max(0, (thresh * 2) - qty)
        data.append([name, str(qty), str(thresh), str(suggested)])
        
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    
    try:
        doc.build(elements)
        return True, filename
    except Exception as e:
        return False, str(e)

def sales_by_date(start_date, end_date):
    """
    Get completed sales between start_date and end_date.
    Returns a list of order documents.
    """
    # Assuming 'updated_at' is set when order is completed.
    # If not, we might need to query by 'created_at' and filter by status 'Completed'
    query = {
        "status": "Completed",
        "updated_at": { 
            "$gte": start_date,
            "$lt": end_date
        }
    }
    
    # Try to find orders
    try:
        orders = list(orders_col.find(query).sort("updated_at", -1))
    except Exception as e:
        print(f"Error querying sales: {e}")
        return []
    
    results = []
    for order in orders:
        # Normalize data for the report
        timestamp = order.get('updated_at', order.get('created_at', datetime.now()))
        
        # Handle invoice_no (fallback to _id)
        invoice_no = order.get('order_no')
        if not invoice_no:
            invoice_no = str(order.get('_id', ''))[-6:].upper()
            
        order_type = order.get('order_type', 'Dine-in')
        grand_total = order.get('grand_total', 0.0)
        payment_method = order.get('payment_method', 'Cash')
        
        # Create a display-friendly dict but keep original data
        display_order = {
            'timestamp': timestamp,
            'invoice_no': invoice_no,
            'order_type': order_type,
            'grand_total': grand_total,
            'payment_method': payment_method
        }
        display_order.update(order) # Merge original data
        results.append(display_order)
        
    return results

def get_item_sales_report(start_date, end_date):
    """
    Aggregate sales by item name.
    Returns list of dicts: {'name': str, 'qty': int, 'total': float, 'category': str}
    """
    pipeline = [
        {
            "$match": {
                "status": "Completed",
                "updated_at": {"$gte": start_date, "$lt": end_date}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.name",
                "qty": {"$sum": "$items.qty"},
                "total": {"$sum": "$items.total"},
                "category": {"$first": "$items.category"}
            }
        },
        {"$sort": {"qty": -1}}
    ]
    
    try:
        results = list(orders_col.aggregate(pipeline))
        return results
    except Exception as e:
        print(f"Error generating item report: {e}")
        return []

def get_category_sales_report(start_date, end_date):
    """
    Aggregate sales by category.
    Returns list of dicts: {'_id': str, 'total_qty': int, 'total_revenue': float}
    """
    pipeline = [
        {
            "$match": {
                "status": "Completed",
                "updated_at": {"$gte": start_date, "$lt": end_date}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.category",
                "total_qty": {"$sum": "$items.qty"},
                "total_revenue": {"$sum": "$items.total"}
            }
        },
        {"$sort": {"total_revenue": -1}}
    ]
    
    try:
        results = list(orders_col.aggregate(pipeline))
        return results
    except Exception as e:
        print(f"Error generating category report: {e}")
        return []

def get_low_stock_report():
    """
    Get items where quantity is below threshold.
    Returns list of dicts.
    """
    try:
        # threshold is string or int in DB? usually int, but let's handle cases
        # Using aggregation to compare qty vs threshold
        pipeline = [
            {
                "$project": {
                    "item_name": 1,
                    "qty": 1,
                    "threshold": 1,
                    "unit": 1,
                    "is_low": {"$lt": ["$qty", "$threshold"]}
                }
            },
            {
                "$match": {"is_low": True}
            }
        ]
        return list(inventory_col.aggregate(pipeline))
    except Exception as e:
        print(f"Error generating low stock report: {e}")
        return []

def get_hourly_sales_report(start_date, end_date):
    """
    Aggregate sales by hour of day.
    Returns list of dicts: {'_id': hour(int), 'total_revenue': float, 'count': int}
    """
    pipeline = [
        {
            "$match": {
                "status": "Completed",
                "updated_at": {"$gte": start_date, "$lt": end_date}
            }
        },
        {
            "$project": {
                "hour": {"$hour": "$updated_at"},
                "grand_total": 1
            }
        },
        {
            "$group": {
                "_id": "$hour",
                "total_revenue": {"$sum": "$grand_total"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    try:
        return list(orders_col.aggregate(pipeline))
    except Exception as e:
        print(f"Error generating hourly report: {e}")
        return []

def get_payment_method_report(start_date, end_date):
    """
    Aggregate sales by payment method.
    """
    pipeline = [
        {
            "$match": {
                "status": "Completed",
                "updated_at": {"$gte": start_date, "$lt": end_date}
            }
        },
        {
            "$group": {
                "_id": "$payment_method",
                "total_revenue": {"$sum": "$grand_total"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"total_revenue": -1}}
    ]
    try:
        return list(orders_col.aggregate(pipeline))
    except Exception as e:
        print(f"Error generating payment report: {e}")
        return []

def get_staff_performance_report(start_date, end_date):
    """
    Aggregate sales by user (waiter/cashier).
    """
    pipeline = [
        {
            "$match": {
                "status": "Completed",
                "updated_at": {"$gte": start_date, "$lt": end_date}
            }
        },
        {
            "$group": {
                "_id": "$waiter_name", # Assuming waiter_name or user field exists
                "total_revenue": {"$sum": "$grand_total"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"total_revenue": -1}}
    ]
    try:
        results = list(orders_col.aggregate(pipeline))
        # If all results have null _id, waiter_name field missing — retry with 'user' field
        all_null = results and all(r.get('_id') is None for r in results)
        if all_null:
            pipeline_user = [
                pipeline[0],
                {
                    "$group": {
                        "_id": "$user",
                        "total_revenue": {"$sum": "$grand_total"},
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"total_revenue": -1}}
            ]
            results = list(orders_col.aggregate(pipeline_user))
        return results
    except Exception as e:
        print(f"Error generating staff report: {e}")
        return []

def get_profit_loss_report(start_date, end_date):
    """
    Calculate Profit & Loss.
    Returns dict: {revenue, cogs, expenses, wastage, net_profit}
    """
    # 1. Total Revenue
    pipeline_rev = [
        {"$match": {"status": "Completed", "updated_at": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": None, "total": {"$sum": "$grand_total"}}}
    ]
    res_rev = list(orders_col.aggregate(pipeline_rev))
    revenue = res_rev[0]['total'] if res_rev else 0
    
    # 2. Expenses
    pipeline_exp = [
        {"$match": {"timestamp": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    res_exp = list(expenses_col.aggregate(pipeline_exp))
    expenses = res_exp[0]['total'] if res_exp else 0
    
    # 3. Wastage
    pipeline_waste = [
        {"$match": {"recorded_at": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_cost"}}}
    ]
    res_waste = list(wastage_col.aggregate(pipeline_waste))
    wastage = res_waste[0]['total'] if res_waste else 0
    
    # 4. COGS (Optimized with $lookup)
    pipeline_cogs = [
        {"$match": {"status": "Completed", "updated_at": {"$gte": start_date, "$lt": end_date}}},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.name", "qty": {"$sum": "$items.qty"}}},
        {
            "$lookup": {
                "from": "inventory",
                "localField": "_id",
                "foreignField": "item_name",
                "as": "inventory_data"
            }
        },
        {"$unwind": {"path": "$inventory_data", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "qty": 1,
                "cost": {"$ifNull": ["$inventory_data.cost_per_unit", 0]},
                "total_cost": {"$multiply": ["$qty", {"$ifNull": ["$inventory_data.cost_per_unit", 0]}]}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_cogs": {"$sum": "$total_cost"}
            }
        }
    ]
    
    try:
        res_cogs = list(orders_col.aggregate(pipeline_cogs))
        cogs = res_cogs[0]['total_cogs'] if res_cogs else 0
    except Exception as e:
        logger.error(f"Error calculating COGS: {e}")
        cogs = 0
        
    net_profit = revenue - cogs - expenses - wastage
    
    return {
        "revenue": revenue,
        "cogs": cogs,
        "expenses": expenses,
        "wastage": wastage,
        "net_profit": net_profit
    }

def get_sales_trend(start_date, end_date):
    """
    Daily sales trend for line chart.
    Returns list of dicts: {'_id': date_str, 'total_revenue': float}
    """
    pipeline = [
        {
            "$match": {
                "status": "Completed",
                "updated_at": {"$gte": start_date, "$lt": end_date}
            }
        },
        {
            "$project": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$updated_at"}},
                "grand_total": 1
            }
        },
        {
            "$group": {
                "_id": "$date",
                "total_revenue": {"$sum": "$grand_total"}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    try:
        return list(orders_col.aggregate(pipeline))
    except Exception as e:
        print(f"Error generating sales trend: {e}")
        return []

def get_stock_valuation():
    """
    Calculate total value of current inventory.
    Returns list of dicts: {'item_name', 'qty', 'cost_per_unit', 'total_value'}
    """
    try:
        items = list(inventory_col.find())
        valuation = []
        for item in items:
            qty = item.get('qty', 0)
            cost = item.get('cost_per_unit', 0)
            total_value = qty * cost
            valuation.append({
                "item_name": item.get('item_name'),
                "qty": qty,
                "cost_per_unit": cost,
                "total_value": total_value
            })
        return valuation
    except Exception as e:
        print(f"Error generating stock valuation: {e}")
        return []

def get_dead_stock(days=30):
    """
    Identify items not sold in the last X days.
    """
    start_date = datetime.now() - timedelta(days=days)
    try:
        # 1. Get all items sold in last X days
        sold_items = orders_col.distinct("items.name", {
            "status": "Completed",
            "updated_at": {"$gte": start_date}
        })
        
        # 2. Get all inventory items
        all_inventory = list(inventory_col.find())
        
        dead_stock = []
        for item in all_inventory:
            if item.get('item_name') not in sold_items:
                dead_stock.append({
                    "item_name": item.get('item_name'),
                    "last_sold": "No sales in period", # Simplified
                    "current_stock": item.get('qty', 0),
                    "value": item.get('qty', 0) * item.get('cost_per_unit', 0)
                })
        return dead_stock
    except Exception as e:
        print(f"Error generating dead stock: {e}")
        return []

def get_theoretical_usage(start_date, end_date):
    """
    Calculate theoretical ingredient usage based on recipes and sales.
    """
    try:
        # 1. Get all sold items with quantity
        pipeline = [
            {"$match": {"status": "Completed", "updated_at": {"$gte": start_date, "$lt": end_date}}},
            {"$unwind": "$items"},
            {"$group": {"_id": "$items.name", "total_qty": {"$sum": "$items.qty"}}}
        ]
        sold_items = list(orders_col.aggregate(pipeline))
        
        usage_report = {}
        
        for sold in sold_items:
            item_name = sold['_id']
            qty_sold = sold['total_qty']
            
            # Find recipe
            recipe = recipes_col.find_one({"menu_item_name": item_name, "is_active": True})
            if recipe:
                for ingredient in recipe.get('ingredients', []):
                    ing_name = ingredient.get('item_name')
                    ing_qty = ingredient.get('quantity', 0)
                    total_needed = ing_qty * qty_sold
                    
                    if ing_name in usage_report:
                        usage_report[ing_name] += total_needed
                    else:
                        usage_report[ing_name] = total_needed
                        
        # Format for table
        result = [{"ingredient": k, "theoretical_usage": v} for k, v in usage_report.items()]
        return result
    except Exception as e:
        print(f"Error generating theoretical usage: {e}")
        return []

def get_void_orders(start_date, end_date):
    """
    Get cancelled orders.
    """
    try:
        query = {
            "status": "Cancelled",
            "updated_at": {"$gte": start_date, "$lt": end_date}
        }
        return list(orders_col.find(query).sort("updated_at", -1))
    except Exception as e:
        print(f"Error generating void report: {e}")
        return []

def get_discount_report(start_date, end_date):
    """
    Get orders with discounts.
    """
    try:
        query = {
            "status": "Completed",
            "updated_at": {"$gte": start_date, "$lt": end_date},
            "$or": [
                {"discount": {"$gt": 0}},
                {"discount_amount": {"$gt": 0}}
            ]
        }
        return list(orders_col.find(query).sort("updated_at", -1))
    except Exception as e:
        print(f"Error generating discount report: {e}")
        return []

def get_audit_logs_report(start_date, end_date):
    """
    Get system audit logs.
    """
    try:
        query = {
            "timestamp": {"$gte": start_date, "$lt": end_date}
        }
        return list(audit_logs_col.find(query).sort("timestamp", -1))
    except Exception as e:
        print(f"Error generating audit report: {e}")
        return []

def today_sales():
    """
    Get sales for the current day.
    """
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return sales_by_date(start, end)

import csv

def export_to_csv(data, filename, headers=None):
    """
    Export list of dicts or list of lists to CSV.
    """
    try:
        if not data:
            return False, "No data to export"
            
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Determine headers
            if not headers:
                if isinstance(data[0], dict):
                    headers = list(data[0].keys())
                # If list of lists, no headers unless provided
            
            if headers:
                writer.writerow(headers)
                
            for row in data:
                if isinstance(row, dict):
                    writer.writerow([row.get(h, '') for h in headers])
                else:
                    writer.writerow(row)
                    
        return True, filename
    except Exception as e:
        return False, str(e)
