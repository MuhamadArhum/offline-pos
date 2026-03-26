from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo
from PyQt6.QtGui import QTextDocument, QPageSize, QPageLayout
from PyQt6.QtCore import QMarginsF, QSizeF, QSize
from datetime import datetime
import json
import os
from pathlib import Path

from backend.core.config import load_config as load_printer_config, resolve_resource_path
from backend.services.category_service import get_category_by_name

# ─── Print Design Settings ─────────────────────────────────────────────────────

_DEFAULT_BILL_DESIGN = {
    "paper_size": "80mm", "font_size": 11,
    "show_logo": True, "show_token": True, "show_customer": True,
    "show_waiter": True, "show_tax": True, "show_service_charge": True,
    "show_discount": True, "bill_copy": "ORIGINAL",
    "header_extra": "", "footer_extra": "",
}

_DEFAULT_KOT_DESIGN = {
    "font_size": 14, "kot_title": "KITCHEN ORDER TICKET",
    "show_table": True, "show_token": True, "show_order_type": True,
    "show_waiter": True, "show_notes": True, "show_category_headers": True,
}

def load_print_design():
    """Load print_design settings from config with defaults."""
    config = load_printer_config()
    pd = config.get("print_design", {})
    bill = {**_DEFAULT_BILL_DESIGN, **pd.get("bill", {})}
    kot  = {**_DEFAULT_KOT_DESIGN,  **pd.get("kot",  {})}
    return {
        "bill": bill,
        "kot":  kot,
        "preview_before_print": pd.get("preview_before_print", False),
    }

# Print Log File Path
PRINT_LOG_FILE = "logs/print_log.txt"

# Print timeout in seconds
PRINT_TIMEOUT = 5

# Background print queue
_print_queue = []
_queue_thread = None
_queue_lock = None

# PDF printer names to skip (case-insensitive)
_PDF_PRINTER_KEYWORDS = ["pdf", "xps", "fax", "onenote", "microsoft print"]

def _get_real_printer_name(preferred_name=None):
    """
    Return a real (non-PDF) printer name.
    preferred_name: printer name from config (use as-is if given).
    If no preferred_name, pick first non-PDF system printer.
    Returns None if no real printer found.
    """
    if preferred_name:
        return preferred_name
    available = QPrinterInfo.availablePrinters()
    for info in available:
        name_lower = info.printerName().lower()
        if not any(kw in name_lower for kw in _PDF_PRINTER_KEYWORDS):
            return info.printerName()
    return None

_MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB

def _rotate_log_if_needed():
    """Rotate print log when it exceeds 5 MB."""
    try:
        if os.path.exists(PRINT_LOG_FILE) and os.path.getsize(PRINT_LOG_FILE) > _MAX_LOG_BYTES:
            bak = PRINT_LOG_FILE.replace(".txt", ".bak.txt")
            if os.path.exists(bak):
                os.remove(bak)
            os.rename(PRINT_LOG_FILE, bak)
    except Exception:
        pass

def log_print_job(print_type, order_data, status="success", error_msg=""):
    """
    Log print job to file.
    print_type: 'receipt' or 'kot'
    order_data: dict with order information
    status: 'success' or 'failed'
    error_msg: error message if failed
    """
    try:
        os.makedirs("logs", exist_ok=True)
        _rotate_log_if_needed()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        invoice_no = order_data.get("invoice_no", "N/A")
        table_no = order_data.get("table_no", "N/A")
        grand_total = order_data.get("grand_total", 0)

        log_entry = f"[{timestamp}] {print_type.upper()} - Invoice: {invoice_no} | Table: {table_no} | Total: Rs {grand_total:,.2f} | Status: {status}"
        if error_msg:
            log_entry += f" | Error: {error_msg}"
        log_entry += "\n"

        with open(PRINT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error logging print job: {e}")

def get_restaurant_info(config=None):
    if not config:
        config = load_printer_config()
    
    info = config.get("restaurant_info", {})
    return {
        "name": info.get("name", "RESTAURANT NAME"),
        "address": info.get("address", "123 Food Street, City"),
        "phone": info.get("phone", "0300-1234567"),
        "footer": info.get("footer", "*** THANK YOU VISIT AGAIN ***"),
        "logo_path": info.get("logo_path", config.get("logo_path", "app/resources/POS.png")),
        "print_logo": info.get("print_logo", config.get("print_logo", True))
    }

def get_printers_by_role(role):
    config = load_printer_config()
    printers = config.get("printers", [])
    matching_printers = []
    if printers:
        for p in printers:
            if role in p.get("roles", []):
                matching_printers.append(p)
    if not matching_printers:
        if role == "receipt":
            p = config.get("receipt_printer")
            if p: matching_printers.append(p)
            elif "printer" in config: matching_printers.append(config["printer"])
        elif role == "kot":
            p = config.get("kot_printer")
            if p:
                if p.get("use_same"):
                    rp = config.get("receipt_printer")
                    if rp: matching_printers.append(rp)
                else:
                    matching_printers.append(p)
    return matching_printers

def generate_receipt_html(order_data, restaurant_info=None):
    if not restaurant_info:
        restaurant_info = get_restaurant_info()
    
    logo_html = ""
    if restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
        logo_path = resolve_resource_path(restaurant_info["logo_path"])
        if os.path.exists(logo_path):
            logo_uri = Path(logo_path).as_uri()
            logo_html = f'<div class="center"><img src="{logo_uri}" width="100"></div>'

    items_html = ""
    for item in order_data.get('items', []):
        note = item.get('note', '')
        note_html = f'<br><i style="font-size:10px;">({note})</i>' if note else ''
        items_html += f"""
        <tr>
            <td>{item['qty']}</td>
            <td>{item['name']}{note_html}</td>
            <td style="text-align: right;">{item['price']:.2f}</td>
            <td style="text-align: right;">{item['qty'] * item['price']:.2f}</td>
        </tr>
        """
    
    invoice_no = order_data.get('invoice_no', 'N/A')
    token_no = order_data.get('token_no', '')
    date_val = order_data.get('completed_at') or order_data.get('created_at') or datetime.now()
    date_str = date_val if isinstance(date_val, str) else date_val.strftime('%Y-%m-%d %H:%M:%S')
    order_type = order_data.get('order_type', 'Dine In')
    bill_type  = order_data.get('bill_type', '')
    bill_type_html = (
        f'<p class="center" style="font-size:13px; font-weight:bold; '
        f'border:1px solid #000; display:inline-block; padding:2px 10px;">'
        f'{bill_type.upper()} BILL</p>'
    ) if bill_type else ''

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Courier New', monospace; font-size: 12px; }}
            h2 {{ text-align: center; margin: 0; }}
            p {{ margin: 2px 0; }}
            .center {{ text-align: center; }}
            .right {{ text-align: right; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ border-bottom: 1px dashed #000; text-align: left; }}
            td {{ padding: 2px 0; }}
            .total-row {{ font-weight: bold; border-top: 1px dashed #000; }}
        </style>
    </head>
    <body>
        {logo_html}
        <h1>{restaurant_info['name']}</h1>
        <p class="center">{restaurant_info['address']}</p>
        <p class="center">Tel: {restaurant_info['phone']}</p>
        <br>
        <p class="center">{bill_type_html}</p>
        <p>Order #: {invoice_no}</p>
        <p style="font-size: 14px; font-weight: bold;">Token #: {token_no}</p>
        <p>Date: {date_str}</p>
        <p>Type: {order_type}</p>
        <p>Table: {order_data.get('table_no', 'Takeaway')}</p>
        <p>Customer: {order_data.get('customer_name', 'Guest')}</p>
        <table>
            <thead>
                <tr>
                    <th width="50%">Item</th>
                    <th width="10%">Qty</th>
                    <th width="20%" class="right">Price</th>
                    <th width="20%" class="right">Total</th>
                </tr>
            </thead>
            <tbody>{items_html}</tbody>
        </table>
        <br>
        <div class="right">
            <p>Subtotal: {order_data.get('subtotal', 0):.2f}</p>
            <p>Discount: -{order_data.get('discount', 0):.2f}</p>
            <p>Service Charge: {order_data.get('service_charge', 0):.2f}</p>
            <p>Tax: {order_data.get('tax', 0):.2f}</p>
            <p class="total-row" style="font-size: 14px;">TOTAL: {order_data.get('grand_total', 0):.2f}</p>
        </div>
        <br>
        <p class="center">{restaurant_info.get('footer', '*** THANK YOU VISIT AGAIN ***')}</p>
    </body>
    </html>
    """
    return html

def generate_kot_html(order_data, restaurant_info=None, print_design=None):
    if print_design is None:
        print_design = load_print_design().get("kot", _DEFAULT_KOT_DESIGN)

    kot_title   = print_design.get("kot_title", "KITCHEN ORDER TICKET")
    fs          = int(print_design.get("font_size", 14))
    show_table  = print_design.get("show_table", True)
    show_token  = print_design.get("show_token", True)
    show_type   = print_design.get("show_order_type", True)
    show_waiter = print_design.get("show_waiter", True)
    show_notes  = print_design.get("show_notes", True)
    show_cat_hdr= print_design.get("show_category_headers", True)

    date_val = order_data.get('updated_at') or order_data.get('created_at') or datetime.now()
    date_str = date_val if isinstance(date_val, str) else date_val.strftime('%d-%m-%Y  %I:%M %p')

    # Group items by category
    items = order_data.get('items', [])
    if show_cat_hdr:
        from collections import OrderedDict
        cat_map = OrderedDict()
        for item in items:
            cat = item.get('category', 'General') or 'General'
            cat_map.setdefault(cat, []).append(item)
    else:
        cat_map = {"": items}

    items_html = ""
    for cat_name, cat_items in cat_map.items():
        if show_cat_hdr and cat_name:
            items_html += f"""
            <tr>
                <td colspan="2" style="
                    background:#000; color:#fff;
                    font-size:{fs-2}px; font-weight:900;
                    letter-spacing:2px; padding:4px 6px;
                    text-transform:uppercase;">
                    &#9658; {cat_name.upper()}
                </td>
            </tr>"""
        for item in cat_items:
            note_html = ""
            if show_notes and item.get('note'):
                note_html = f'<tr><td colspan="2" style="font-size:{fs-4}px; color:#555; font-style:italic; padding:0 6px 4px 16px;">&#8627; {item["note"]}</td></tr>'
            items_html += f"""
            <tr>
                <td style="font-size:{fs}px; font-weight:900; padding:6px 4px;">
                    {item['name']}
                </td>
                <td style="font-size:{fs+4}px; font-weight:900; text-align:right;
                           padding:6px 4px; white-space:nowrap;">
                    x{item['qty']}
                </td>
            </tr>
            {note_html}"""

    table_html  = f'<p style="font-size:{fs+4}px; font-weight:900; margin:3px 0;">Table: {order_data.get("table_no", "Takeaway")}</p>' if show_table else ""
    token_html  = f'<div style="border:2px solid #000; padding:4px 8px; margin:6px 0; display:table; width:100%;"><span style="font-size:{fs-2}px; color:#555;">TOKEN</span><span style="font-size:{fs+6}px; font-weight:900; float:right;">#{order_data.get("token_no","—")}</span></div>' if show_token else ""
    type_val    = order_data.get('order_type', '')
    type_html   = f'<p style="font-size:{fs-2}px; font-weight:700; border:1px solid #000; display:inline-block; padding:1px 8px; margin:2px 0;">{type_val.upper()}</p>' if show_type and type_val else ""
    waiter_html = f'<p style="font-size:{fs-3}px; margin:2px 0;">Waiter: <b>{order_data.get("waiter","")}</b></p>' if show_waiter else ""

    html = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Courier New', Courier, monospace; font-size:{fs-2}px;
                color:#000; background:#fff; width:72mm; margin:0 auto; padding:4px 2px; }}
        .center {{ text-align:center; }}
        table {{ width:100%; border-collapse:collapse; }}
        hr.solid {{ border:none; border-top:2px solid #000; margin:5px 0; }}
        hr.dash  {{ border:none; border-top:1px dashed #000; margin:5px 0; }}
    </style>
    </head>
    <body>
        <div class="center" style="font-size:{fs+2}px; font-weight:900;
             letter-spacing:1px; border-bottom:3px double #000; padding-bottom:4px; margin-bottom:4px;">
            {kot_title}
        </div>
        <p style="font-size:{fs-3}px; margin:1px 0;">Order #: {order_data.get('invoice_no','New')}</p>
        <p style="font-size:{fs-3}px; margin:1px 0;">Date: {date_str}</p>
        {waiter_html}
        {type_html}
        <hr class="solid">
        {table_html}
        {token_html}
        <hr class="dash">
        <table>
            <thead>
                <tr>
                    <th style="font-size:{fs-3}px; text-align:left; padding:2px 4px; border-bottom:1px solid #000;">ITEM</th>
                    <th style="font-size:{fs-3}px; text-align:right; padding:2px 4px; border-bottom:1px solid #000;">QTY</th>
                </tr>
            </thead>
            <tbody>{items_html}</tbody>
        </table>
        <hr class="solid">
        <div class="center" style="font-size:{fs-2}px; font-weight:700; margin-top:4px;">
            *** KITCHEN COPY ***
        </div>
        <br>
    </body></html>
    """
    return html

def _generate_kot_html_legacy(order_data, restaurant_info=None):
    """Legacy: kept for backward compat reference only."""
    if not restaurant_info:
        restaurant_info = {"name": "KITCHEN ORDER TICKET", "address": "", "phone": ""}
    items_html = ""
    for item in order_data.get('items', []):
        items_html += f"""
        <tr>
            <td style="font-size: 14px; font-weight: bold;">{item['name']}</td>
            <td style="font-size: 14px; font-weight: bold;">{item['qty']}</td>
        </tr>
        """
    date_val = order_data.get('updated_at') or order_data.get('created_at') or datetime.now()
    date_str = date_val if isinstance(date_val, str) else date_val.strftime('%Y-%m-%d %H:%M:%S')

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Courier New', monospace; font-size: 12px; }}
            h2 {{ text-align: center; margin: 0; }}
            p {{ margin: 2px 0; }}
            .center {{ text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ border-bottom: 1px dashed #000; text-align: left; }}
            td {{ padding: 5px 0; }}
        </style>
    </head>
    <body>
        <h2>{restaurant_info.get('name', 'KITCHEN ORDER TICKET')}</h2>
        <br>
        <p style="font-size: 16px; font-weight: bold;">Table: {order_data.get('table_no', 'Takeaway')}</p>
        <p style="font-size: 14px; font-weight: bold;">Token #: {order_data.get('token_no', '')}</p>
        <p>Order #: {order_data.get('invoice_no', 'New')}</p>
        <p>Date: {date_str}</p>
        <p>Waiter: {order_data.get('waiter', 'Server')}</p>
        <table>
            <thead>
                <tr>
                    <th width="80%">Item</th>
                    <th width="20%">Qty</th>
                </tr>
            </thead>
            <tbody>{items_html}</tbody>
        </table>
        <br>
        <p class="center">*** KITCHEN COPY ***</p>
    </body>
    </html>
    """
    return html


# ─── THERMAL INVOICE GENERATOR (80mm Professional) ────────────────────────────

def generate_thermal_invoice_html(order_data, restaurant_info=None, print_design=None):
    """
    Generates a professional 80mm thermal printer invoice.
    Clean design optimized for 80mm (3 inch) thermal paper width.
    Supports logo, itemized table, totals, footer, and print_design settings.
    """
    if not restaurant_info:
        restaurant_info = get_restaurant_info()
    if print_design is None:
        print_design = load_print_design().get("bill", _DEFAULT_BILL_DESIGN)

    fs            = int(print_design.get("font_size", 11))
    show_logo     = print_design.get("show_logo", True)
    show_token    = print_design.get("show_token", True)
    show_customer = print_design.get("show_customer", True)
    show_waiter   = print_design.get("show_waiter", True)
    show_tax      = print_design.get("show_tax", True)
    show_service  = print_design.get("show_service_charge", True)
    show_discount = print_design.get("show_discount", True)
    bill_copy     = print_design.get("bill_copy", "").strip()
    header_extra  = print_design.get("header_extra", "").strip()
    footer_extra  = print_design.get("footer_extra", "").strip()

    # Logo
    logo_html = ""
    if show_logo and restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
        logo_path = resolve_resource_path(restaurant_info["logo_path"])
        if os.path.exists(logo_path):
            logo_uri = Path(logo_path).as_uri()
            logo_html = f'<div style="text-align:center; margin-bottom:6px;"><img src="{logo_uri}" style="width:70px; height:auto;"></div>'

    # Items rows
    items_html = ""
    for item in order_data.get('items', []):
        note = item.get('note', '')
        note_html = f'<div style="font-size:{fs-2}px; color:#555; font-style:italic; padding-left:4px;">&#8627; {note}</div>' if note else ''
        line_total = item['qty'] * item['price']
        items_html += f"""
        <tr>
            <td style="padding:4px 2px; font-size:{fs}px; vertical-align:top;">
                {item['name']}{note_html}
            </td>
            <td style="padding:4px 2px; font-size:{fs}px; text-align:center; vertical-align:top; white-space:nowrap;">{item['qty']}</td>
            <td style="padding:4px 2px; font-size:{fs}px; text-align:right; vertical-align:top; white-space:nowrap;">{item['price']:.0f}</td>
            <td style="padding:4px 2px; font-size:{fs}px; text-align:right; vertical-align:top; white-space:nowrap; font-weight:600;">{line_total:.0f}</td>
        </tr>
        """

    # Meta info
    invoice_no = order_data.get('invoice_no', 'N/A')
    token_no   = order_data.get('token_no', '—')
    date_val   = order_data.get('completed_at') or order_data.get('created_at') or datetime.now()
    date_str   = date_val if isinstance(date_val, str) else date_val.strftime('%d-%m-%Y  %I:%M %p')
    table_no   = order_data.get('table_no', 'Takeaway')
    customer   = order_data.get('customer_name', 'Guest')
    waiter     = order_data.get('waiter', '')

    # Optional meta rows
    customer_row = f'<tr><td class="meta-label">Customer</td><td class="meta-value">{customer}</td></tr>' if show_customer else ""
    waiter_row_meta = f'<tr><td class="meta-label">Waiter</td><td class="meta-value">{waiter}</td></tr>' if show_waiter and waiter else ""
    token_section = f"""
        <div class="token-box">
            <div class="token-label">TOKEN NO.</div>
            <div class="token-value">#{token_no}</div>
        </div>""" if show_token else ""
    bill_copy_html = f'<div style="text-align:center; font-size:{fs}px; font-weight:800; letter-spacing:2px; border:1.5px solid #000; padding:2px 0; margin:4px 0;">{bill_copy} COPY</div>' if bill_copy else ""
    header_extra_html = f'<div style="text-align:center; font-size:{fs-1}px; margin:2px 0;">{header_extra}</div>' if header_extra else ""
    footer_extra_html = f'<div style="text-align:center; font-size:{fs-1}px; margin:2px 0;">{footer_extra}</div>' if footer_extra else ""

    # Totals
    subtotal     = order_data.get('subtotal', 0)
    discount     = order_data.get('discount', 0)
    service_chg  = order_data.get('service_charge', 0)
    tax          = order_data.get('tax', 0)
    grand_total  = order_data.get('grand_total', 0)

    discount_row = f"""
        <tr>
            <td colspan="2" style="font-size:{fs}px; color:#c00; padding:2px 0;">Discount</td>
            <td style="font-size:{fs}px; color:#c00; text-align:right; padding:2px 0;">- Rs.{discount:.0f}</td>
        </tr>
    """ if (discount and show_discount) else ""

    service_row = f"""
        <tr>
            <td colspan="2" style="font-size:{fs}px; padding:2px 0;">Service Charge</td>
            <td style="font-size:{fs}px; text-align:right; padding:2px 0;">Rs.{service_chg:.0f}</td>
        </tr>
    """ if (service_chg and show_service) else ""

    tax_row = f"""
        <tr>
            <td colspan="2" style="font-size:11px; padding:2px 0;">Tax / GST</td>
            <td style="font-size:11px; text-align:right; padding:2px 0;">Rs.{tax:.0f}</td>
        </tr>
    """ if (tax and show_tax) else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        /* 80mm thermal = approx 302px usable width */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Courier New', Courier, monospace;
            font-size: {fs}px;
            color: #000;
            background: #fff;
            width: 72mm;
            margin: 0 auto;
            padding: 4px 2px;
        }}
        .center  {{ text-align: center; }}
        .right   {{ text-align: right; }}
        .bold    {{ font-weight: bold; }}
        .divider-solid {{ border: none; border-top: 1px solid #000; margin: 5px 0; }}
        .divider-dash  {{ border: none; border-top: 1px dashed #000; margin: 5px 0; }}

        /* Header */
        .shop-name {{
            font-size: 15px;
            font-weight: 900;
            text-align: center;
            letter-spacing: 0.5px;
            margin: 4px 0 2px;
        }}
        .shop-info {{
            font-size: 10px;
            text-align: center;
            color: #333;
            line-height: 1.5;
        }}

        /* Invoice label badge */
        .invoice-label {{
            text-align: center;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2px;
            background: #000;
            color: #fff;
            padding: 2px 0;
            margin: 6px 0 5px;
        }}

        /* Order meta */
        .meta-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 4px;
        }}
        .meta-table td {{
            font-size: 10px;
            padding: 1px 0;
            vertical-align: top;
        }}
        .meta-label {{ color: #555; width: 40%; }}
        .meta-value {{ font-weight: 600; }}

        /* Token highlight box */
        .token-box {{
            border: 1.5px solid #000;
            padding: 3px 6px;
            margin: 5px 0;
            display: table;
            width: 100%;
        }}
        .token-label {{
            display: table-cell;
            font-size: 10px;
            color: #555;
            vertical-align: middle;
        }}
        .token-value {{
            display: table-cell;
            font-size: 16px;
            font-weight: 900;
            text-align: right;
            vertical-align: middle;
        }}

        /* Items table */
        .items-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .items-table thead th {{
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            padding: 3px 2px;
            border-bottom: 1px solid #000;
        }}
        .items-table thead th:first-child {{ text-align: left; }}
        .items-table thead th:nth-child(2) {{ text-align: center; }}
        .items-table thead th:nth-child(3),
        .items-table thead th:nth-child(4) {{ text-align: right; }}

        /* Totals */
        .totals-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 2px;
        }}
        .totals-table td {{ padding: 1px 0; }}

        /* Grand total row */
        .grand-row {{
            background: #000;
            color: #fff;
            padding: 5px 6px;
            margin: 5px 0;
            display: table;
            width: 100%;
        }}
        .grand-label {{
            display: table-cell;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 1px;
            vertical-align: middle;
        }}
        .grand-value {{
            display: table-cell;
            font-size: 16px;
            font-weight: 900;
            text-align: right;
            vertical-align: middle;
        }}

        /* Footer */
        .footer-msg {{
            font-size: 11px;
            font-weight: 700;
            text-align: center;
            margin: 6px 0 2px;
        }}
        .footer-sub {{
            font-size: 9px;
            text-align: center;
            color: #555;
        }}
        .barcode-placeholder {{
            text-align: center;
            font-size: 9px;
            color: #aaa;
            margin-top: 6px;
            letter-spacing: 3px;
        }}
    </style>
    </head>
    <body>

        <!-- Logo -->
        {logo_html}

        <!-- Shop Header -->
        <div class="shop-name">{restaurant_info['name']}</div>
        <div class="shop-info">
            {restaurant_info['address']}<br>
            Tel: {restaurant_info['phone']}
        </div>

        <!-- Invoice Badge -->
        <div class="invoice-label">&mdash;&mdash; INVOICE &mdash;&mdash;</div>

        {header_extra_html}
        {bill_copy_html}

        <!-- Order Meta -->
        <table class="meta-table">
            <tr>
                <td class="meta-label">Invoice #</td>
                <td class="meta-value">{invoice_no}</td>
            </tr>
            <tr>
                <td class="meta-label">Date</td>
                <td class="meta-value">{date_str}</td>
            </tr>
            <tr>
                <td class="meta-label">Table</td>
                <td class="meta-value">{table_no}</td>
            </tr>
            {customer_row}
            {waiter_row_meta}
        </table>

        <!-- Token Highlight -->
        {token_section}

        <hr class="divider-solid">

        <!-- Items Table -->
        <table class="items-table">
            <thead>
                <tr>
                    <th style="width:48%; text-align:left;">Item</th>
                    <th style="width:10%; text-align:center;">Qty</th>
                    <th style="width:18%; text-align:right;">Rate</th>
                    <th style="width:24%; text-align:right;">Amt</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <hr class="divider-dash">

        <!-- Totals -->
        <table class="totals-table">
            <tr>
                <td colspan="2" style="font-size:{fs}px; padding:2px 0;">Subtotal</td>
                <td style="font-size:{fs}px; text-align:right; padding:2px 0;">Rs.{subtotal:.0f}</td>
            </tr>
            {discount_row}
            {service_row}
            {tax_row}
        </table>

        <!-- Grand Total -->
        <div class="grand-row">
            <div class="grand-label">TOTAL</div>
            <div class="grand-value">Rs. {grand_total:.0f}</div>
        </div>

        <hr class="divider-dash">

        <!-- Footer -->
        <div class="footer-msg">{restaurant_info.get('footer', '*** THANK YOU! VISIT AGAIN ***')}</div>
        {footer_extra_html}
        <div class="footer-sub">Powered by Abyte POS &bull; {datetime.now().strftime('%d-%m-%Y')}</div>
        <div class="barcode-placeholder">||||| {invoice_no} |||||</div>

        <br><br>
    </body>
    </html>
    """
    return html


def print_thermal_invoice(order_data, parent=None):
    """
    Print a professional thermal invoice (80mm) to the receipt printer.
    Uses the same printer routing as print_receipt.
    """
    printers = get_printers_by_role("receipt")
    if not printers:
        return _print_thermal_usb(order_data, {})
    config = printers[0]
    ptype = config.get("type", "usb")
    if ptype == "network":
        # Network thermal uses the existing ESC/POS network path (receipt)
        return print_network(order_data, config, is_kot=False)
    else:
        return _print_thermal_usb(order_data, config)


def _print_thermal_usb(order_data, config, restaurant_info=None):
    """Internal: renders thermal invoice HTML and sends to USB/system printer."""
    try:
        preferred = config.get("usb_name") or config.get("usb_printer_name")
        printer_name = _get_real_printer_name(preferred)
        if not printer_name:
            return False, "Koi real printer nahi mila. PDF printers skip kiye gaye."

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(printer_name)

        # Set page to 80mm width thermal roll
        # 80mm wide, long page (we let content define height)
        custom_size = QPageSize(QSizeF(80, 297), QPageSize.Unit.Millimeter, "Thermal 80mm")
        printer.setPageSize(custom_size)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setPageMargins(QMarginsF(2, 2, 2, 2), QPageLayout.Unit.Millimeter)
        printer.setFullPage(False)

        document = QTextDocument()
        document.setHtml(generate_thermal_invoice_html(order_data, restaurant_info))
        document.print(printer)

        return True, "Thermal Invoice Printed Successfully"
    except Exception as e:
        print(f"Thermal USB Print Error: {e}")
        return False, str(e)


# ─── EXISTING FUNCTIONS (unchanged) ───────────────────────────────────────────

def print_receipt(order_data, parent=None):
    log_print_job("receipt", order_data, "attempting")
    
    printers = get_printers_by_role("receipt")
    
    config = {}
    if printers:
        config = printers[0]
    
    ptype = config.get("type", "usb") if config else "usb"
    
    if ptype == "http":
        success, msg = print_http(order_data, config, is_kot=False)
    elif not printers:
        success, msg = print_usb(order_data, {}, is_kot=False)
    else:
        config = printers[0]
        ptype = config.get("type", "usb")
        if ptype == "network":
            success, msg = print_network(order_data, config, is_kot=False)
        else:
            success, msg = print_usb(order_data, config, is_kot=False)
    
    if not success:
        if ptype != "usb":
            fb_success, fb_msg = print_usb(order_data, {}, is_kot=False)
            if fb_success:
                log_print_job("receipt", order_data, "success", f"fallback_usb: {fb_msg} | primary: {msg}")
                return True, fb_msg
        fb2_success, fb2_msg = _print_thermal_usb(order_data, {})
        if fb2_success:
            log_print_job("receipt", order_data, "success", f"fallback_thermal: {fb2_msg} | primary: {msg}")
            return True, fb2_msg
        log_print_job("receipt", order_data, "failed", msg)
        return False, msg
    
    log_print_job("receipt", order_data, "success")
    return success, msg

def print_kot(order_data, parent=None):
    log_print_job("kot", order_data, "attempting")
    
    items = order_data.get('items', [])
    if not items:
        return False, "No items to print"
    
    printers = get_printers_by_role("kot")
    if printers:
        config = printers[0]
        if config.get("type") == "http":
            success, msg = print_http(order_data, config, is_kot=True)
            if success:
                log_print_job("kot", order_data, "success")
                return True, msg
            fb_success, fb_msg = print_usb(order_data, {}, is_kot=True)
            if fb_success:
                log_print_job("kot", order_data, "success", f"fallback_usb: {fb_msg} | primary: {msg}")
                return True, fb_msg
            log_print_job("kot", order_data, "failed", msg)
            return False, msg
    
    category_groups = {}
    for item in items:
        category = item.get('category', 'General')
        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(item)
    results = []
    success_count = 0
    for category, category_items in category_groups.items():
        category_info = get_category_by_name(category)
        printer_role = category_info.get('printer_role', f"kot-{category.lower()}") if category_info else f"kot-{category.lower()}"
        category_order = order_data.copy()
        category_order['items'] = category_items
        printers = get_printers_by_role(printer_role)
        if not printers:
            printers = get_printers_by_role("kot")
        if not printers:
            results.append(f"No printer configured for {category} (tried {printer_role} and kot)")
            continue
        for config in printers:
            ptype = config.get("type", "usb")
            if ptype == "http":
                success, msg = print_http(category_order, config, is_kot=True)
            elif ptype == "network":
                success, msg = print_network(category_order, config, is_kot=True)
                if not success:
                    fb_success, fb_msg = print_usb(category_order, {}, is_kot=True)
                    if fb_success:
                        results.append(f"{category}: Fallback USB")
                        success = True
                        msg = fb_msg
            else:
                success, msg = print_usb(category_order, config, is_kot=True)
            results.append(f"{category}: {msg}")
            if success:
                success_count += 1
    if success_count > 0:
        log_print_job("kot", order_data, "success")
        return True, f"Printed to {success_count} section printers: {'; '.join(set(results))}"
    else:
        log_print_job("kot", order_data, "failed", '; '.join(set(results)))
        return False, f"Failed to print KOT: {'; '.join(set(results))}"

def print_test_page_v2(full_config, print_type="receipt"):
    try:
        dummy_order = {
            "invoice_no": "TEST-001",
            "table_no": "Test Table",
            "customer_name": "Test Customer",
            "items": [
                {"name": "Test Item 1", "qty": 1, "price": 100},
                {"name": "Test Item 2", "qty": 2, "price": 50}
            ],
            "subtotal": 200,
            "discount": 0,
            "service_charge": 0,
            "tax": 0,
            "grand_total": 200,
            "created_at": datetime.now()
        }
        config = full_config.get("printer_config", {})
        restaurant_info = full_config.get("restaurant_info")
        ptype = config.get("type", "usb")
        if ptype == "network":
            return print_network(dummy_order, config, is_kot=(print_type=="kot"), restaurant_info=restaurant_info)
        else:
            return print_usb(dummy_order, config, is_kot=(print_type=="kot"), restaurant_info=restaurant_info)
    except Exception as e:
        return False, str(e)

def print_usb(order_data, config, is_kot=False, restaurant_info=None):
    """Print to USB/system printer on the main Qt thread"""
    try:
        preferred = config.get("usb_name") or config.get("usb_printer_name")
        printer_name = _get_real_printer_name(preferred)
        if not printer_name:
            return False, "Koi real printer nahi mila. PDF printers skip kiye gaye."
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(printer_name)
        document = QTextDocument()
        if is_kot:
            document.setHtml(generate_kot_html(order_data, restaurant_info))
        else:
            document.setHtml(generate_receipt_html(order_data, restaurant_info))
        document.print(printer)
        return True, "Printed Successfully"
    except Exception as e:
        return False, str(e)

def print_network(order_data, config, is_kot=False, restaurant_info=None):
    """Print to network printer with timeout handling"""
    import threading
    
    result = [None, None]
    
    def _print():
        try:
            from escpos.printer import Network
            ip = config.get("ip") or config.get("network_ip")
            port = int(config.get("port") or config.get("network_port", 9100))
            if not ip:
                result[0] = False
                result[1] = "IP Address Missing"
                return
            
            p = Network(ip, port=port, timeout=PRINT_TIMEOUT)
            ri = restaurant_info if restaurant_info else get_restaurant_info()
            p.set(align='center')
            if not is_kot and ri.get("print_logo") and ri.get("logo_path"):
                try:
                    logo_path = ri["logo_path"]
                    if os.path.exists(logo_path):
                        p.image(logo_path)
                except Exception as e:
                    print(f"Logo print error: {e}")
            if is_kot:
                p.text(f"{ri.get('name', 'KITCHEN ORDER TICKET')}\n\n")
                p.text("KITCHEN COPY\n\n")
            else:
                p.text(f"{ri.get('name', 'RESTAURANT NAME')}\n")
                p.text(f"{ri.get('address', '')}\n")
                p.text(f"Tel: {ri.get('phone', '')}\n\n")
            p.set(align='left')
            p.text(f"Table: {order_data.get('table_no', 'Takeaway')}\n")
            p.text(f"Order: {order_data.get('invoice_no', 'New')}\n")
            p.text(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            p.text("-" * 42 + "\n")
            p.text("{:<5} {:<20} {:>10}\n".format("Qty", "Item", "Total" if not is_kot else ""))
            p.text("-" * 42 + "\n")
            for item in order_data.get('items', []):
                qty = str(item['qty'])
                name = item['name'][:20]
                if is_kot:
                    p.set(bold=True, double_height=True, double_width=True)
                    p.text(f"{qty} x {name}\n")
                    if item.get('note'):
                        p.set(bold=False, double_height=False, double_width=False)
                        p.text(f"   Note: {item['note']}\n")
                        p.set(bold=True, double_height=True, double_width=True)
                    p.set(bold=False, double_height=False, double_width=False)
                else:
                    total = f"{item['qty']*item['price']:.2f}"
                    p.text("{:<5} {:<20} {:>10}\n".format(qty, name, total))
                    if item.get('note'):
                        p.text(f"      ({item['note']})\n")
            p.text("-" * 42 + "\n")
            if not is_kot:
                p.set(align='right')
                p.text(f"Subtotal: {order_data.get('subtotal', 0):.2f}\n")
                if order_data.get('discount'):
                    p.text(f"Discount: -{order_data.get('discount', 0):.2f}\n")
                if order_data.get('service_charge'):
                    p.text(f"Service Chg: {order_data.get('service_charge', 0):.2f}\n")
                if order_data.get('tax'):
                    p.text(f"Tax: {order_data.get('tax', 0):.2f}\n")
                p.set(bold=True)
                p.text(f"TOTAL: {order_data.get('grand_total', 0):.2f}\n")
                p.set(bold=False)
                p.set(align='center')
                p.text(f"\n{ri.get('footer', 'Thank You!')}\n")
            p.cut()
            p.close()
            result[0] = True
            result[1] = "Printed Successfully"
        except ImportError:
            result[0] = False
            result[1] = "python-escpos not found"
        except Exception as e:
            result[0] = False
            result[1] = str(e)
    
    # Run print in background thread with timeout
    t = threading.Thread(target=_print, daemon=True)
    t.start()
    t.join(timeout=PRINT_TIMEOUT)
    
    if t.is_alive():
        return False, "Network printer timeout or not responding"
    
    if result[0] is None:
        return False, "Print state unknown"
    
    return result[0], result[1]


def print_http(order_data, config, is_kot=False):
    """
    Print using HTTP request to Printer Server.
    config should contain 'server_url' (e.g., 'http://localhost:9100')
    """
    import requests
    import json
    
    try:
        server_url = config.get("server_url", "http://localhost:9100")
        
        # Prepare order data with print type
        print_data = order_data.copy()
        print_data['print_type'] = 'kot' if is_kot else 'receipt'
        
        # Send POST request to print server
        response = requests.post(
            f"{server_url}/print",
            json=print_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                return True, f"Print job sent: {result.get('job_id', 'N/A')}"
            else:
                return False, result.get("message", "Unknown error")
        else:
            return False, f"Server returned status {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to print server at {server_url}. Make sure Printer Server is running."
    except requests.exceptions.Timeout:
        return False, "Print server timed out"
    except Exception as e:
        print(f"HTTP Print Error: {e}")
        return False, str(e)

def print_test_page(config):
    return print_test_page_v2({"printer_config": config})

def generate_report_html(report_data, restaurant_info=None):
    if not restaurant_info:
        restaurant_info = get_restaurant_info()
    logo_html = ""
    if restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
        logo_path = os.path.abspath(restaurant_info["logo_path"])
        if os.path.exists(logo_path):
            logo_uri = Path(logo_path).as_uri()
            logo_html = f'<div class="center"><img src="{logo_uri}" width="100"></div>'
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Courier New', monospace; font-size: 12px; }}
            h2 {{ text-align: center; margin: 0; }}
            p {{ margin: 2px 0; }}
            .center {{ text-align: center; }}
            .right {{ text-align: right; }}
            .bold {{ font-weight: bold; }}
            hr {{ border-top: 1px dashed #000; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ border-bottom: 1px dashed #000; text-align: left; }}
            td {{ padding: 2px 0; }}
        </style>
    </head>
    <body>
        {logo_html}
        <h2>{restaurant_info['name']}</h2>
        <p class="center">{restaurant_info['address']}</p>
        <p class="center">Tel: {restaurant_info['phone']}</p>
        <br>
        <h3 class="center">{report_data.get('title', 'REPORT')}</h3>
        <p>Date: {report_data.get('date', datetime.now().strftime('%Y-%m-%d'))}</p>
        <p>Generated: {datetime.now().strftime('%H:%M:%S')}</p>
        <hr>
        <pre>{report_data.get('content', '')}</pre>
        <hr>
        <p class="center">{restaurant_info.get('footer', '*** END OF REPORT ***')}</p>
    </body>
    </html>
    """
    return html

def print_report_v2(report_data):
    try:
        restaurant_info = get_restaurant_info()
        printers = get_printers_by_role("receipt")
        printer_config = printers[0] if printers else {}
        ptype = printer_config.get("type", "usb")
        if ptype == "network":
            from escpos.printer import Network
            ip = printer_config.get("ip")
            port = int(printer_config.get("port", 9100))
            if not ip: return False, "IP Missing"
            p = Network(ip, port=port)
            p.set(align='center')
            if restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
                if os.path.exists(restaurant_info["logo_path"]):
                    p.image(restaurant_info["logo_path"])
            p.text(f"{restaurant_info['name']}\n")
            p.text(f"{report_data.get('title', 'REPORT')}\n\n")
            p.set(align='left')
            p.text(report_data.get('content', ''))
            p.cut()
            p.close()
            return True, "Printed to Network Printer"
        else:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            p_name = printer_config.get("usb_name")
            if p_name: printer.setPrinterName(p_name)
            doc = QTextDocument()
            doc.setHtml(generate_report_html(report_data, restaurant_info))
            doc.print(printer)
            return True, "Printed to System Printer"
    except Exception as e:
        print(f"Print Report Error: {e}")
        return False, str(e)

def print_dummy_receipt(report_text):
    print("Printing Report:\n", report_text)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    if not QPrinterInfo.availablePrinters():
        print("No printers available.")
        return
    doc = QTextDocument()
    doc.setPlainText(report_text)
    doc.print(printer)


# ─── INVOICE GENERATOR (A4 PDF - Design Only Changed) ─────────────────────────

def generate_pdf_invoice(order_data, restaurant_info=None):
    """
    Generates a professional A4 PDF invoice.
    Clean modern design with sidebar accent, full item table, and totals.
    Logic (paths, printer setup, data extraction) is unchanged.
    """
    try:
        # 1. Get restaurant info
        if not restaurant_info:
            restaurant_info = get_restaurant_info()

        # 2. Logo
        logo_html = ""
        if restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
            logo_path = resolve_resource_path(restaurant_info["logo_path"])
            if os.path.exists(logo_path):
                logo_uri = Path(logo_path).as_uri()
                logo_html = f'<img src="{logo_uri}" style="height:70px; width:auto; object-fit:contain;">'

        # 3. Items rows
        items_html = ""
        for i, item in enumerate(order_data.get('items', [])):
            note        = item.get('note', '')
            note_html   = f'<div style="font-size:11px; color:#888; margin-top:3px; font-style:italic;">Note: {note}</div>' if note else ''
            row_bg      = "#FAFBFF" if i % 2 == 0 else "#FFFFFF"
            line_total  = item['qty'] * item['price']
            items_html += f"""
            <tr style="background:{row_bg};">
                <td style="padding:12px 16px; font-size:13px; color:#1E2235; border-bottom:1px solid #EAECF4;">
                    {item['name']}{note_html}
                </td>
                <td style="padding:12px 16px; font-size:13px; color:#6B7280; text-align:center; border-bottom:1px solid #EAECF4;">{item['qty']}</td>
                <td style="padding:12px 16px; font-size:13px; color:#6B7280; text-align:right; border-bottom:1px solid #EAECF4;">Rs. {item['price']:.2f}</td>
                <td style="padding:12px 16px; font-size:13px; font-weight:600; color:#1E2235; text-align:right; border-bottom:1px solid #EAECF4;">Rs. {line_total:.2f}</td>
            </tr>
            """

        # 4. Prepare meta
        invoice_no = order_data.get('invoice_no', 'N/A')
        token_no   = order_data.get('token_no', '—')
        date_val   = order_data.get('completed_at') or order_data.get('created_at') or datetime.now()
        date_str   = date_val if isinstance(date_val, str) else date_val.strftime('%d %B %Y  •  %I:%M %p')

        def money_row(label, value, color="#4B5563", prefix="−" if False else ""):
            return f"""
            <tr>
                <td style="padding:7px 0; font-size:13px; color:#6B7280;">{label}</td>
                <td style="padding:7px 0; font-size:13px; color:{color}; text-align:right; font-weight:500;">
                    Rs. {value:.2f}
                </td>
            </tr>
            """

        subtotal_row  = money_row("Subtotal", order_data.get('subtotal', 0))
        discount_val  = order_data.get('discount', 0)
        service_val   = order_data.get('service_charge', 0)
        tax_val       = order_data.get('tax', 0)

        discount_row = f"""
            <tr>
                <td style="padding:7px 0; font-size:13px; color:#EF4444;">Discount</td>
                <td style="padding:7px 0; font-size:13px; color:#EF4444; text-align:right; font-weight:500;">
                    − Rs. {discount_val:.2f}
                </td>
            </tr>
        """ if discount_val else ""

        service_row = money_row("Service Charge", service_val) if service_val else ""
        tax_row     = money_row("Tax (GST)", tax_val) if tax_val else ""

        # 5. HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 0; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: Arial, Helvetica, sans-serif;
                font-size: 13px;
                color: #1E2235;
                background: #ffffff;
            }}
            .page {{
                width: 210mm;
                min-height: 297mm;
                display: flex;
                flex-direction: row;
            }}
            .sidebar {{
                width: 8px;
                background: linear-gradient(180deg, #4F46E5 0%, #7C3AED 100%);
                flex-shrink: 0;
            }}
            .main {{
                flex: 1;
                padding: 32px 36px 36px 36px;
            }}
            .header {{
                display: table;
                width: 100%;
                margin-bottom: 32px;
                padding-bottom: 24px;
                border-bottom: 2px solid #EAECF4;
            }}
            .header-left  {{ display: table-cell; vertical-align: top; width: 55%; }}
            .header-right {{ display: table-cell; vertical-align: top; text-align: right; }}
            .restaurant-name {{
                font-size: 22px;
                font-weight: 800;
                color: #1E2235;
                letter-spacing: -0.5px;
                margin-bottom: 4px;
            }}
            .restaurant-sub {{
                font-size: 12px;
                color: #9CA3AF;
                line-height: 1.6;
            }}
            .invoice-badge {{
                display: inline-block;
                background: #4F46E5;
                color: white;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 4px 14px;
                border-radius: 20px;
                text-transform: uppercase;
                margin-bottom: 10px;
            }}
            .invoice-number {{
                font-size: 26px;
                font-weight: 800;
                color: #1E2235;
                letter-spacing: -0.5px;
            }}
            .invoice-date {{
                font-size: 12px;
                color: #9CA3AF;
                margin-top: 4px;
            }}
            .info-grid {{
                display: table;
                width: 100%;
                margin-bottom: 28px;
                border: 1.5px solid #EAECF4;
                border-radius: 10px;
                overflow: hidden;
            }}
            .info-cell {{
                display: table-cell;
                padding: 14px 20px;
                border-right: 1.5px solid #EAECF4;
                width: 33%;
            }}
            .info-cell:last-child {{ border-right: none; }}
            .info-label {{
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                text-transform: uppercase;
                color: #9CA3AF;
                margin-bottom: 4px;
            }}
            .info-value {{
                font-size: 14px;
                font-weight: 700;
                color: #1E2235;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 24px;
                border: 1.5px solid #EAECF4;
                border-radius: 10px;
                overflow: hidden;
            }}
            .items-table thead tr {{ background: #1E2235; }}
            .items-table thead th {{
                padding: 13px 16px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                text-transform: uppercase;
                color: #A5B4FC;
                text-align: left;
            }}
            .items-table thead th:nth-child(2) {{ text-align: center; }}
            .items-table thead th:nth-child(3),
            .items-table thead th:nth-child(4) {{ text-align: right; }}
            .totals-wrapper {{ display: table; width: 100%; }}
            .totals-spacer {{ display: table-cell; width: 55%; }}
            .totals-box {{ display: table-cell; width: 45%; vertical-align: top; }}
            .totals-inner {{ border: 1.5px solid #EAECF4; border-radius: 10px; overflow: hidden; }}
            .totals-rows {{ padding: 16px 20px 0 20px; }}
            .totals-rows table {{ width: 100%; border-collapse: collapse; }}
            .grand-total-row {{
                background: #4F46E5;
                padding: 16px 20px;
                display: table;
                width: 100%;
                margin-top: 8px;
            }}
            .grand-label {{ display: table-cell; font-size: 13px; font-weight: 800; color: white; letter-spacing: 0.5px; text-transform: uppercase; }}
            .grand-value {{ display: table-cell; font-size: 18px; font-weight: 800; color: white; text-align: right; }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1.5px dashed #EAECF4;
                text-align: center;
            }}
            .footer-msg {{ font-size: 14px; font-weight: 700; color: #4F46E5; margin-bottom: 6px; }}
            .footer-sub {{ font-size: 11px; color: #C4C9D8; }}
        </style>
        </head>
        <body>
        <div class="page">
            <div class="sidebar"></div>
            <div class="main">
                <div class="header">
                    <div class="header-left">
                        {logo_html}
                        <div class="restaurant-name" style="margin-top: {'10px' if logo_html else '0'};">
                            {restaurant_info['name']}
                        </div>
                        <div class="restaurant-sub">
                            {restaurant_info['address']}<br>
                            Tel: {restaurant_info['phone']}
                        </div>
                    </div>
                    <div class="header-right">
                        <div class="invoice-badge">Invoice</div>
                        <div class="invoice-number">#{invoice_no}</div>
                        <div class="invoice-date">{date_str}</div>
                    </div>
                </div>
                <div class="info-grid">
                    <div class="info-cell">
                        <div class="info-label">Token No.</div>
                        <div class="info-value">{token_no}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Table</div>
                        <div class="info-value">{order_data.get('table_no', 'Takeaway')}</div>
                    </div>
                    <div class="info-cell">
                        <div class="info-label">Customer</div>
                        <div class="info-value">{order_data.get('customer_name', 'Guest')}</div>
                    </div>
                </div>
                <table class="items-table">
                    <thead>
                        <tr>
                            <th style="width:50%;">Description</th>
                            <th style="width:10%;">Qty</th>
                            <th style="width:20%;">Unit Price</th>
                            <th style="width:20%;">Total</th>
                        </tr>
                    </thead>
                    <tbody>{items_html}</tbody>
                </table>
                <div class="totals-wrapper">
                    <div class="totals-spacer"></div>
                    <div class="totals-box">
                        <div class="totals-inner">
                            <div class="totals-rows">
                                <table>
                                    {subtotal_row}
                                    {discount_row}
                                    {service_row}
                                    {tax_row}
                                </table>
                            </div>
                            <div class="grand-total-row">
                                <div class="grand-label">Grand Total</div>
                                <div class="grand-value">Rs. {order_data.get('grand_total', 0):.2f}</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="footer">
                    <div class="footer-msg">{restaurant_info.get('footer', 'Thank you for your visit!')}</div>
                    <div class="footer-sub">This is a computer-generated invoice — no signature required.</div>
                </div>
            </div>
        </div>
        </body>
        </html>
        """

        # 6. Output path
        invoice_dir = os.path.join(os.getcwd(), "invoices")
        os.makedirs(invoice_dir, exist_ok=True)
        filename  = f"Invoice_{order_data.get('invoice_no', 'Unknown')}.pdf"
        filename  = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-'))
        file_path = os.path.join(invoice_dir, filename)

        # 7. QPrinter setup
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(file_path)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setPageMargins(QMarginsF(8, 8, 8, 8), QPageLayout.Unit.Millimeter)

        doc = QTextDocument()
        doc.setHtml(html_content)
        doc.print(printer)

        return file_path

    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return None
