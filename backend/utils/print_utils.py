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
    try:
        if os.path.exists(PRINT_LOG_FILE) and os.path.getsize(PRINT_LOG_FILE) > _MAX_LOG_BYTES:
            bak = PRINT_LOG_FILE.replace(".txt", ".bak.txt")
            if os.path.exists(bak):
                os.remove(bak)
            os.rename(PRINT_LOG_FILE, bak)
    except Exception:
        pass

def log_print_job(print_type, order_data, status="success", error_msg=""):
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


# ══════════════════════════════════════════════════════════════════════════════
#  REDESIGNED: THERMAL INVOICE — 80mm Professional
# ══════════════════════════════════════════════════════════════════════════════

def generate_thermal_invoice_html(order_data, restaurant_info=None, print_design=None):
    """
    Professional 80mm thermal invoice.
    Clean, high-contrast layout optimised for thermal paper.
    Font sizes, spacing and borders all tuned for 80mm roll.
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

    # ── Logo ──────────────────────────────────────────────────────────────────
    logo_html = ""
    if show_logo and restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
        logo_path = resolve_resource_path(restaurant_info["logo_path"])
        if os.path.exists(logo_path):
            logo_uri = Path(logo_path).as_uri()
            logo_html = f'<div class="logo-wrap"><img src="{logo_uri}" class="logo-img"></div>'

    # ── Items rows ────────────────────────────────────────────────────────────
    items_html = ""
    for item in order_data.get('items', []):
        note      = item.get('note', '')
        note_html = f'<div class="item-note">&#8627; {note}</div>' if note else ''
        total     = item['qty'] * item['price']
        items_html += f"""
        <tr class="item-row">
            <td class="col-item">{item['name']}{note_html}</td>
            <td class="col-qty">{item['qty']}</td>
            <td class="col-rate">{item['price']:.0f}</td>
            <td class="col-amt">{total:.0f}</td>
        </tr>"""

    # ── Meta ──────────────────────────────────────────────────────────────────
    invoice_no  = order_data.get('invoice_no', 'N/A')
    token_no    = order_data.get('token_no', '—')
    date_val    = order_data.get('completed_at') or order_data.get('created_at') or datetime.now()
    date_str    = date_val if isinstance(date_val, str) else date_val.strftime('%d-%m-%Y  %I:%M %p')
    table_no    = order_data.get('table_no', 'Takeaway')
    customer    = order_data.get('customer_name', 'Guest')
    waiter      = order_data.get('waiter', '')
    order_type  = order_data.get('order_type', 'Dine In')
    pay_method  = order_data.get('payment_method', '')
    pay_status  = order_data.get('payment_status', '')

    subtotal    = order_data.get('subtotal', 0)
    discount    = order_data.get('discount', 0)
    service_chg = order_data.get('service_charge', 0)
    tax         = order_data.get('tax', 0)
    grand_total = order_data.get('grand_total', 0)

    # ── Optional blocks ───────────────────────────────────────────────────────
    pay_badge_html = ""
    if pay_status == 'UNPAID':
        pay_badge_html = '<div class="badge-unpaid">&#10007; UNPAID &#10007;</div>'
    elif pay_status == 'PAID':
        pay_badge_html = '<div class="badge-paid">&#10003; PAID &#10003;</div>'

    bill_copy_html   = f'<div class="copy-badge">{bill_copy} COPY</div>' if bill_copy else ""
    order_type_html  = f'<div class="order-type">{order_type.upper()}</div>'
    header_extra_html = f'<div class="extra-line">{header_extra}</div>' if header_extra else ""
    footer_extra_html = f'<div class="extra-line">{footer_extra}</div>' if footer_extra else ""

    token_html = f"""
    <div class="token-box">
        <span class="token-label">TOKEN</span>
        <span class="token-num">#{token_no}</span>
    </div>""" if show_token else ""

    customer_row = f'<tr><td class="ml">Customer</td><td class="mv">{customer}</td></tr>' if show_customer else ""
    waiter_row   = f'<tr><td class="ml">Waiter</td><td class="mv">{waiter}</td></tr>' if (show_waiter and waiter) else ""

    discount_row = f"""
    <tr>
        <td class="tl red">Discount</td>
        <td class="tv red">- Rs.{discount:.0f}</td>
    </tr>""" if (discount and show_discount) else ""

    service_row = f"""
    <tr>
        <td class="tl">Service Charge</td>
        <td class="tv">Rs.{service_chg:.0f}</td>
    </tr>""" if (service_chg and show_service) else ""

    tax_row = f"""
    <tr>
        <td class="tl">Tax / GST</td>
        <td class="tv">Rs.{tax:.0f}</td>
    </tr>""" if (tax and show_tax) else ""

    pay_method_row = f"""
    <table class="totals-tbl" style="margin-top:4px;">
        <tr>
            <td class="tl bold">Payment</td>
            <td class="tv bold">{pay_method}</td>
        </tr>
    </table>""" if (pay_method and pay_method not in ('Pending', '')) else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
/* ── Reset ──────────────────────────────── */
* {{ margin:0; padding:0; box-sizing:border-box; }}

/* ── Root ───────────────────────────────── */
body {{
    font-family: 'Courier New', Courier, monospace;
    font-size: {fs}px;
    line-height: 1.45;
    color: #000;
    background: #fff;
    width: 76mm;
    margin: 0 auto;
    padding: 6px 4px 16px 4px;
}}

/* ── Dividers ───────────────────────────── */
.hr-solid {{ border:none; border-top: 2px solid #000; margin: 6px 0; }}
.hr-dash  {{ border:none; border-top: 1px dashed #555; margin: 5px 0; }}
.hr-thin  {{ border:none; border-top: 1px solid #ccc; margin: 4px 0; }}

/* ── Logo ───────────────────────────────── */
.logo-wrap {{ text-align:center; margin-bottom:6px; }}
.logo-img  {{ width:72px; height:auto; }}

/* ── Restaurant Header ──────────────────── */
.shop-name {{
    font-size: {fs + 8}px;
    font-weight: 900;
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 4px 0 2px;
}}
.shop-addr {{
    font-size: {fs - 1}px;
    text-align: center;
    color: #333;
    line-height: 1.5;
}}
.shop-phone {{
    font-size: {fs}px;
    font-weight: 700;
    text-align: center;
    margin-top: 1px;
}}

/* ── Invoice Strip ──────────────────────── */
.inv-strip {{
    background: #000;
    color: #fff;
    text-align: center;
    font-size: {fs - 1}px;
    font-weight: 900;
    letter-spacing: 4px;
    padding: 4px 0;
    margin: 8px 0 5px;
    text-transform: uppercase;
}}

/* ── Badges ─────────────────────────────── */
.badge-unpaid {{
    text-align: center;
    font-size: {fs + 3}px;
    font-weight: 900;
    letter-spacing: 3px;
    color: #b91c1c;
    border: 2.5px solid #b91c1c;
    padding: 4px 0;
    margin: 5px 0;
}}
.badge-paid {{
    text-align: center;
    font-size: {fs + 3}px;
    font-weight: 900;
    letter-spacing: 3px;
    color: #166534;
    border: 2.5px solid #166534;
    padding: 4px 0;
    margin: 5px 0;
}}
.copy-badge {{
    display: inline-block;
    border: 1.5px solid #000;
    font-size: {fs - 1}px;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 2px 10px;
    text-transform: uppercase;
    margin: 2px auto;
    text-align: center;
}}
.order-type {{
    display: inline-block;
    background: #000;
    color: #fff;
    font-size: {fs - 1}px;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 2px 10px;
    text-transform: uppercase;
    margin: 2px auto;
    text-align: center;
}}
.badge-center {{ text-align:center; margin: 3px 0; }}
.extra-line {{
    font-size: {fs - 1}px;
    text-align: center;
    color: #555;
    margin: 2px 0;
}}

/* ── Meta Table ─────────────────────────── */
.meta-tbl {{ width:100%; border-collapse:collapse; margin: 4px 0 5px; }}
.meta-tbl td {{ font-size:{fs - 1}px; padding:1.5px 0; vertical-align:top; }}
.ml {{
    color:#555;
    text-transform: uppercase;
    font-size: {fs - 2}px;
    letter-spacing: 0.5px;
    width: 36%;
}}
.mv {{ font-weight:700; }}

/* ── Token Box ──────────────────────────── */
.token-box {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 2px solid #000;
    padding: 4px 8px;
    margin: 6px 0 4px;
}}
.token-label {{
    font-size: {fs - 2}px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #555;
}}
.token-num {{
    font-size: {fs + 8}px;
    font-weight: 900;
    letter-spacing: 1px;
}}

/* ── Items Table ────────────────────────── */
.items-tbl {{ width:100%; border-collapse:collapse; }}
.items-tbl thead tr {{ border-bottom: 2px solid #000; }}
.items-tbl thead th {{
    font-size: {fs - 2}px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 4px 2px 5px;
}}
.items-tbl thead th.h-item {{ text-align:left;  width:46%; }}
.items-tbl thead th.h-qty  {{ text-align:center; width:10%; }}
.items-tbl thead th.h-rate {{ text-align:right;  width:20%; }}
.items-tbl thead th.h-amt  {{ text-align:right;  width:24%; }}

.item-row {{ border-bottom:1px dashed #ccc; }}
.item-row:last-child {{ border-bottom:none; }}
.items-tbl tbody td {{ font-size:{fs}px; padding:4px 2px; vertical-align:top; }}
.col-item {{ text-align:left;   font-weight:600; }}
.col-qty  {{ text-align:center; }}
.col-rate {{ text-align:right;  color:#444; }}
.col-amt  {{ text-align:right;  font-weight:800; }}
.item-note {{
    font-size: {fs - 2}px;
    color: #666;
    font-style: italic;
    padding-left: 4px;
    line-height: 1.3;
    margin-top: 1px;
}}

/* ── Totals ─────────────────────────────── */
.totals-tbl {{ width:100%; border-collapse:collapse; }}
.tl {{
    font-size: {fs - 1}px;
    color: #444;
    padding: 2px 0;
    width: 58%;
}}
.tv {{
    font-size: {fs - 1}px;
    text-align:right;
    padding: 2px 0;
    font-weight: 600;
}}
.red  {{ color:#b91c1c; }}
.bold {{ font-weight:800; }}

/* ── Grand Total ────────────────────────── */
.grand-box {{
    background: #000;
    color: #fff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 10px;
    margin: 7px 0 5px;
}}
.grand-lbl {{
    font-size: {fs + 1}px;
    font-weight: 900;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
.grand-val {{
    font-size: {fs + 8}px;
    font-weight: 900;
    letter-spacing: 0.5px;
}}

/* ── Footer ─────────────────────────────── */
.footer-thank {{
    font-size: {fs + 1}px;
    font-weight: 800;
    text-align: center;
    margin: 6px 0 2px;
    letter-spacing: 0.5px;
}}
.footer-powered {{
    font-size: {fs - 2}px;
    text-align: center;
    color: #888;
    margin-top: 3px;
}}
.inv-ref {{
    font-size: {fs - 3}px;
    text-align: center;
    color: #bbb;
    letter-spacing: 2px;
    margin-top: 2px;
}}
</style>
</head>
<body>

<!-- ═══ LOGO ═══════════════════════════════ -->
{logo_html}

<!-- ═══ RESTAURANT HEADER ═════════════════ -->
<div class="shop-name">{restaurant_info['name']}</div>
<div class="shop-addr">{restaurant_info.get('address','')}</div>
<div class="shop-phone">&#128222; {restaurant_info.get('phone','')}</div>

<!-- ═══ INVOICE STRIP ═════════════════════ -->
<div class="inv-strip">&#9472;&#9472;&#9472;&#9472;  INVOICE  &#9472;&#9472;&#9472;&#9472;</div>

{header_extra_html}

<!-- ═══ BADGES ════════════════════════════ -->
<div class="badge-center">{bill_copy_html}</div>
<div class="badge-center">{order_type_html}</div>
{pay_badge_html}

<!-- ═══ ORDER META ════════════════════════ -->
<table class="meta-tbl">
    <tr><td class="ml">Invoice&nbsp;#</td><td class="mv">{invoice_no}</td></tr>
    <tr><td class="ml">Date</td><td class="mv">{date_str}</td></tr>
    <tr><td class="ml">Table</td><td class="mv">{table_no}</td></tr>
    {customer_row}
    {waiter_row}
</table>

<!-- ═══ TOKEN ═════════════════════════════ -->
{token_html}

<hr class="hr-solid">

<!-- ═══ ITEMS TABLE ═══════════════════════ -->
<table class="items-tbl">
    <thead>
        <tr>
            <th class="h-item">Item</th>
            <th class="h-qty">Qty</th>
            <th class="h-rate">Rate</th>
            <th class="h-amt">Amt</th>
        </tr>
    </thead>
    <tbody>{items_html}</tbody>
</table>

<hr class="hr-dash">

<!-- ═══ TOTALS ════════════════════════════ -->
<table class="totals-tbl">
    <tr>
        <td class="tl">Subtotal</td>
        <td class="tv">Rs.{subtotal:.0f}</td>
    </tr>
    {discount_row}
    {service_row}
    {tax_row}
</table>

<!-- ═══ GRAND TOTAL ═══════════════════════ -->
<div class="grand-box">
    <div class="grand-lbl">Total</div>
    <div class="grand-val">Rs.{grand_total:.0f}</div>
</div>

{pay_method_row}

<hr class="hr-dash">

<!-- ═══ FOOTER ════════════════════════════ -->
<div class="footer-thank">{restaurant_info.get('footer', '&#9733;  Thank You — Visit Again!  &#9733;')}</div>
{footer_extra_html}
<div class="footer-powered">Powered by Abyte POS &bull; {datetime.now().strftime('%d-%m-%Y')}</div>
<div class="inv-ref">Ref: {invoice_no}</div>
<br><br>

</body>
</html>"""
    return html


# ══════════════════════════════════════════════════════════════════════════════
#  REDESIGNED: KOT — 80mm Kitchen Order Ticket
# ══════════════════════════════════════════════════════════════════════════════

def generate_kot_html(order_data, restaurant_info=None, print_design=None):
    """
    Premium KOT for 80mm thermal printer.
    Large item names, bold qty, category headers, token box — all kitchen-optimised.
    """
    if print_design is None:
        print_design = load_print_design().get("kot", _DEFAULT_KOT_DESIGN)

    kot_title   = print_design.get("kot_title", "KITCHEN ORDER TICKET")
    fs          = int(print_design.get("font_size", 14))
    show_table  = print_design.get("show_table", True)
    show_token  = print_design.get("show_token", True)
    show_type   = print_design.get("show_order_type", True)
    show_waiter = print_design.get("show_waiter", True)
    show_notes  = print_design.get("show_notes", True)
    show_cat    = print_design.get("show_category_headers", True)

    date_val = order_data.get('updated_at') or order_data.get('created_at') or datetime.now()
    date_str = date_val if isinstance(date_val, str) else date_val.strftime('%d-%m-%Y  %I:%M %p')

    # ── Group items by category ───────────────────────────────────────────────
    items = order_data.get('items', [])
    if show_cat:
        from collections import OrderedDict
        cat_map = OrderedDict()
        for item in items:
            cat = (item.get('category') or 'General').strip()
            cat_map.setdefault(cat, []).append(item)
    else:
        cat_map = {"": items}

    # ── Items HTML ────────────────────────────────────────────────────────────
    items_html = ""
    for cat_name, cat_items in cat_map.items():
        if show_cat and cat_name:
            items_html += f"""
        <tr class="cat-hdr">
            <td colspan="2">&#9658; {cat_name.upper()}</td>
        </tr>"""
        for item in cat_items:
            note_html = ""
            if show_notes and item.get('note'):
                note_html = f'<tr class="note-row"><td colspan="2">&#8627; {item["note"]}</td></tr>'
            items_html += f"""
        <tr class="item-row">
            <td class="i-name">{item['name']}</td>
            <td class="i-qty">x{item['qty']}</td>
        </tr>
        {note_html}"""

    # ── Optional meta blocks ──────────────────────────────────────────────────
    table_html  = f'<div class="table-num">Table: {order_data.get("table_no", "Takeaway")}</div>' if show_table else ""

    token_html  = f"""
    <div class="token-box">
        <span class="tok-lbl">TOKEN</span>
        <span class="tok-num">#{order_data.get("token_no","—")}</span>
    </div>""" if show_token else ""

    type_val   = order_data.get('order_type', '')
    type_html  = f'<div class="type-badge">{type_val.upper()}</div>' if (show_type and type_val) else ""

    waiter_html = f'<div class="waiter-line">Waiter: <b>{order_data.get("waiter","")}</b></div>' if show_waiter else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
/* ── Reset ──────────────────────────────── */
* {{ margin:0; padding:0; box-sizing:border-box; }}

/* ── Root ───────────────────────────────── */
body {{
    font-family: 'Courier New', Courier, monospace;
    font-size: {fs - 2}px;
    line-height: 1.4;
    color: #000;
    background: #fff;
    width: 76mm;
    margin: 0 auto;
    padding: 4px 4px 14px 4px;
}}

/* ── Dividers ───────────────────────────── */
.hr-solid {{ border:none; border-top:2.5px solid #000; margin:5px 0; }}
.hr-dash  {{ border:none; border-top:1px dashed #555; margin:5px 0; }}
.hr-double{{
    border:none;
    border-top: 3px double #000;
    margin: 6px 0 4px;
}}

/* ── KOT Title Header ───────────────────── */
.kot-header {{
    text-align: center;
    font-size: {fs + 3}px;
    font-weight: 900;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 4px 0 5px;
    border-bottom: 3px double #000;
    margin-bottom: 5px;
    line-height: 1.3;
}}

/* ── Meta Lines ─────────────────────────── */
.meta-line {{
    font-size: {fs - 3}px;
    margin: 1.5px 0;
    color: #222;
}}
.waiter-line {{
    font-size: {fs - 3}px;
    margin: 1.5px 0;
}}
.type-badge {{
    display: inline-block;
    border: 1.5px solid #000;
    font-size: {fs - 3}px;
    font-weight: 800;
    letter-spacing: 1.5px;
    padding: 2px 10px;
    text-transform: uppercase;
    margin: 3px 0;
}}

/* ── Table Number ───────────────────────── */
.table-num {{
    font-size: {fs + 4}px;
    font-weight: 900;
    margin: 4px 0 2px;
    letter-spacing: 0.5px;
}}

/* ── Token Box ──────────────────────────── */
.token-box {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 2.5px solid #000;
    padding: 5px 10px;
    margin: 5px 0 4px;
}}
.tok-lbl {{
    font-size: {fs - 3}px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #444;
}}
.tok-num {{
    font-size: {fs + 9}px;
    font-weight: 900;
    letter-spacing: 1px;
}}

/* ── Items Table ────────────────────────── */
.items-tbl {{ width:100%; border-collapse:collapse; }}

/* Category header row */
.cat-hdr td {{
    background: #000;
    color: #fff;
    font-size: {fs - 2}px;
    font-weight: 900;
    letter-spacing: 2px;
    padding: 4px 6px;
    text-transform: uppercase;
}}

/* Item row */
.item-row {{ border-bottom: 1px dashed #bbb; }}
.item-row:last-child {{ border-bottom:none; }}
.i-name {{
    font-size: {fs + 1}px;
    font-weight: 900;
    padding: 7px 4px 7px 2px;
    vertical-align: middle;
    width: 72%;
    line-height: 1.25;
}}
.i-qty  {{
    font-size: {fs + 5}px;
    font-weight: 900;
    text-align: right;
    padding: 7px 2px;
    vertical-align: middle;
    white-space: nowrap;
    width: 28%;
}}

/* Note row */
.note-row td {{
    font-size: {fs - 3}px;
    color: #555;
    font-style: italic;
    padding: 0 6px 5px 14px;
    line-height: 1.3;
}}

/* Column headers */
.col-hdr th {{
    font-size: {fs - 3}px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 3px 2px 4px;
    border-bottom: 2px solid #000;
}}
.col-hdr th.h-item {{ text-align:left; }}
.col-hdr th.h-qty  {{ text-align:right; }}

/* ── Footer ─────────────────────────────── */
.footer-lbl {{
    font-size: {fs - 2}px;
    font-weight: 700;
    text-align: center;
    letter-spacing: 2px;
    margin-top: 5px;
    text-transform: uppercase;
}}
</style>
</head>
<body>

<!-- ═══ KOT HEADER ═══════════════════════ -->
<div class="kot-header">{kot_title}</div>

<!-- ═══ META INFO ════════════════════════ -->
<div class="meta-line">Order #: <b>{order_data.get('invoice_no','New')}</b></div>
<div class="meta-line">Date: {date_str}</div>
{waiter_html}
{type_html}

<hr class="hr-solid">

<!-- ═══ TABLE + TOKEN ════════════════════ -->
{table_html}
{token_html}

<hr class="hr-dash">

<!-- ═══ ITEMS ════════════════════════════ -->
<table class="items-tbl">
    <thead>
        <tr class="col-hdr">
            <th class="h-item">Item</th>
            <th class="h-qty">Qty</th>
        </tr>
    </thead>
    <tbody>{items_html}</tbody>
</table>

<hr class="hr-solid">

<!-- ═══ FOOTER ═══════════════════════════ -->
<div class="footer-lbl">&#9658;&#9658;&#9658; Kitchen Copy &#9668;&#9668;&#9668;</div>

<br>
</body>
</html>"""
    return html


# ── Legacy KOT (backward compat only) ────────────────────────────────────────
def _generate_kot_html_legacy(order_data, restaurant_info=None):
    if not restaurant_info:
        restaurant_info = {"name": "KITCHEN ORDER TICKET", "address": "", "phone": ""}
    items_html = ""
    for item in order_data.get('items', []):
        items_html += f"""
        <tr>
            <td style="font-size: 14px; font-weight: bold;">{item['name']}</td>
            <td style="font-size: 14px; font-weight: bold;">{item['qty']}</td>
        </tr>"""
    date_val = order_data.get('updated_at') or order_data.get('created_at') or datetime.now()
    date_str = date_val if isinstance(date_val, str) else date_val.strftime('%Y-%m-%d %H:%M:%S')
    html = f"""
    <html><head><style>
        body {{ font-family: 'Courier New', monospace; font-size: 12px; }}
        h2 {{ text-align: center; margin: 0; }}
        p {{ margin: 2px 0; }}
        .center {{ text-align: center; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ border-bottom: 1px dashed #000; text-align: left; }}
        td {{ padding: 5px 0; }}
    </style></head>
    <body>
        <h2>{restaurant_info.get('name', 'KITCHEN ORDER TICKET')}</h2><br>
        <p style="font-size: 16px; font-weight: bold;">Table: {order_data.get('table_no', 'Takeaway')}</p>
        <p style="font-size: 14px; font-weight: bold;">Token #: {order_data.get('token_no', '')}</p>
        <p>Order #: {order_data.get('invoice_no', 'New')}</p>
        <p>Date: {date_str}</p>
        <p>Waiter: {order_data.get('waiter', 'Server')}</p>
        <table>
            <thead><tr><th width="80%">Item</th><th width="20%">Qty</th></tr></thead>
            <tbody>{items_html}</tbody>
        </table>
        <br><p class="center">*** KITCHEN COPY ***</p>
    </body></html>"""
    return html


# ══════════════════════════════════════════════════════════════════════════════
#  RECEIPT HTML (simple fallback — unchanged logic)
# ══════════════════════════════════════════════════════════════════════════════

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
            <td>{item['name']}{note_html}</td>
            <td>{item['qty']}</td>
            <td style="text-align: right;">{item['price']:.2f}</td>
            <td style="text-align: right;">{item['qty'] * item['price']:.2f}</td>
        </tr>"""

    invoice_no = order_data.get('invoice_no', 'N/A')
    token_no   = order_data.get('token_no', '')
    date_val   = order_data.get('completed_at') or order_data.get('created_at') or datetime.now()
    date_str   = date_val if isinstance(date_val, str) else date_val.strftime('%Y-%m-%d %H:%M:%S')
    order_type = order_data.get('order_type', 'Dine In')
    bill_type  = order_data.get('bill_type', '')
    bill_type_html = (
        f'<p class="center" style="font-size:13px; font-weight:bold; '
        f'border:1px solid #000; display:inline-block; padding:2px 10px;">'
        f'{bill_type.upper()} BILL</p>'
    ) if bill_type else ''

    payment_status = order_data.get('payment_status', '')
    if payment_status == 'UNPAID':
        pay_status_html = (
            '<p class="center" style="font-size:16px; font-weight:900; '
            'border:2px solid #c00; color:#c00; padding:4px 0; margin:6px 0; '
            'letter-spacing:2px;">&#10007; UNPAID &#10007;</p>'
        )
    elif payment_status == 'PAID':
        pay_status_html = (
            '<p class="center" style="font-size:16px; font-weight:900; '
            'border:2px solid #059669; color:#059669; padding:4px 0; margin:6px 0; '
            'letter-spacing:2px;">&#10003; PAID &#10003;</p>'
        )
    else:
        pay_status_html = ''

    html = f"""
    <html><head>
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
        {pay_status_html}
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
    </body></html>"""
    return html


# ══════════════════════════════════════════════════════════════════════════════
#  PRINT FUNCTIONS (logic unchanged)
# ══════════════════════════════════════════════════════════════════════════════

def print_thermal_invoice(order_data, parent=None):
    printers = get_printers_by_role("receipt")
    if not printers:
        return _print_thermal_usb(order_data, {})
    config = printers[0]
    ptype = config.get("type", "usb")
    if ptype == "network":
        return print_network(order_data, config, is_kot=False)
    else:
        return _print_thermal_usb(order_data, config)


def _print_thermal_usb(order_data, config, restaurant_info=None):
    try:
        preferred = config.get("usb_name") or config.get("usb_printer_name")
        printer_name = _get_real_printer_name(preferred)
        if not printer_name:
            return False, "Koi real printer nahi mila. PDF printers skip kiye gaye."
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(printer_name)
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


def print_receipt(order_data, parent=None):
    if not order_data.get('payment_status'):
        order_data = dict(order_data)
        order_data['payment_status'] = (
            'PAID' if order_data.get('status') == 'Completed' else 'UNPAID'
        )
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
            "invoice_no": "TEST-001", "table_no": "Test Table",
            "customer_name": "Test Customer",
            "items": [
                {"name": "Test Item 1", "qty": 1, "price": 100},
                {"name": "Test Item 2", "qty": 2, "price": 50}
            ],
            "subtotal": 200, "discount": 0, "service_charge": 0,
            "tax": 0, "grand_total": 200, "created_at": datetime.now()
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
    import threading
    result = [None, None]

    def _print():
        try:
            from escpos.printer import Network
            ip   = config.get("ip") or config.get("network_ip")
            port = int(config.get("port") or config.get("network_port", 9100))
            if not ip:
                result[0] = False; result[1] = "IP Address Missing"; return

            p  = Network(ip, port=port, timeout=PRINT_TIMEOUT)
            ri = restaurant_info if restaurant_info else get_restaurant_info()

            W = 42  # 80mm thermal: 42 chars normal, 21 chars double-width

            # helper: right-aligned label + value row
            def _row(label, value, w=W):
                v = str(value)
                pad = w - len(label) - len(v)
                return label + " " * max(pad, 1) + v + "\n"

            # ══════════════════════════════════════════════════════════
            #  KOT (Kitchen Order Ticket)
            # ══════════════════════════════════════════════════════════
            if is_kot:
                p.set(align='center', bold=True, double_height=True, double_width=True)
                p.text("KOT\n")
                p.set(bold=False, double_height=False, double_width=False)
                p.text(f"{ri.get('name','')}\n")
                p.text("-" * W + "\n")
                p.set(align='left')
                date_val = order_data.get('updated_at') or order_data.get('created_at') or datetime.now()
                date_str = date_val if isinstance(date_val, str) else date_val.strftime('%d-%m-%Y  %I:%M %p')
                p.text(f"Table  : {order_data.get('table_no','Takeaway')}\n")
                p.text(f"Type   : {order_data.get('order_type','Dine In')}\n")
                p.text(f"Time   : {date_str}\n")
                if order_data.get('waiter'):
                    p.text(f"Waiter : {order_data['waiter']}\n")
                if order_data.get('token_no'):
                    p.text(_row("Token  :", f"#{order_data['token_no']}"))
                p.text("=" * W + "\n")
                for item in order_data.get('items', []):
                    p.set(bold=True, double_height=True, double_width=True)
                    p.text(f"{item['qty']} x {item['name']}\n")
                    p.set(bold=False, double_height=False, double_width=False)
                    if item.get('note'):
                        p.text(f"   >> {item['note']}\n")
                p.text("=" * W + "\n")
                p.set(align='center')
                p.text("-- KITCHEN COPY --\n")
                p.cut()
                p.close()
                result[0] = True; result[1] = "KOT Printed"
                return

            # ══════════════════════════════════════════════════════════
            #  BILL / RECEIPT
            # ══════════════════════════════════════════════════════════

            # ── Logo ─────────────────────────────────────────────────
            p.set(align='center')
            if ri.get("print_logo") and ri.get("logo_path"):
                try:
                    if os.path.exists(ri["logo_path"]):
                        p.image(ri["logo_path"])
                except Exception:
                    pass

            # ── Restaurant Name (largest text) ────────────────────────
            p.set(align='center', bold=True, double_height=True, double_width=True)
            name_text = ri.get('name', 'RESTAURANT')[:20]
            p.text(f"{name_text}\n")
            p.set(bold=False, double_height=False, double_width=False)

            # ── Address & Phone ───────────────────────────────────────
            p.set(align='center')
            if ri.get('address'):
                p.text(f"{ri['address']}\n")
            if ri.get('phone'):
                p.text(f"Tel: {ri['phone']}\n")

            p.text("-" * W + "\n")
            p.set(align='center', bold=True)
            p.text("INVOICE\n")
            p.set(bold=False)
            p.text("-" * W + "\n")

            # ── PAID / UNPAID Badge ───────────────────────────────────
            pay_status = order_data.get('payment_status', '')
            if pay_status in ('PAID', 'UNPAID'):
                p.set(align='center', bold=True, double_height=True)
                if pay_status == 'UNPAID':
                    p.text("**** UNPAID ****\n")
                else:
                    p.text("****  PAID  ****\n")
                p.set(bold=False, double_height=False)
                p.text("-" * W + "\n")

            # ── Order Meta ────────────────────────────────────────────
            p.set(align='left')
            date_val = order_data.get('completed_at') or order_data.get('created_at') or datetime.now()
            date_str = date_val if isinstance(date_val, str) else date_val.strftime('%d-%m-%Y  %I:%M %p')

            inv  = order_data.get('invoice_no', 'N/A')
            tbl  = order_data.get('table_no', 'Takeaway')
            otype= order_data.get('order_type', 'Dine In')
            cust = order_data.get('customer_name', '')
            wait = order_data.get('waiter', '')
            tok  = order_data.get('token_no', '')

            p.text(f"Invoice : {inv}\n")
            p.text(f"Date    : {date_str}\n")
            p.text(f"Table   : {tbl}   |   {otype}\n")
            if cust and cust not in ('', 'Guest'):
                p.text(f"Customer: {cust}\n")
            if wait:
                p.text(f"Waiter  : {wait}\n")

            # ── Token Number (prominent) ──────────────────────────────
            if tok:
                p.text("-" * W + "\n")
                p.set(align='center', bold=True, double_height=True, double_width=True)
                p.text(f"# {tok} #\n")
                p.set(bold=False, double_height=False, double_width=False)
                p.set(align='left')
                p.text("TOKEN NO.\n")

            p.text("=" * W + "\n")

            # ── Items header ──────────────────────────────────────────
            p.set(bold=True)
            p.text(f"{'#':<3} {'Item':<27} {'Amt':>8}\n")
            p.set(bold=False)
            p.text("-" * W + "\n")

            # ── Items ─────────────────────────────────────────────────
            for idx, item in enumerate(order_data.get('items', []), 1):
                qty   = item['qty']
                name  = item['name']
                price = item['price']
                total = qty * price

                # First line: number, name (up to 20 chars), amount
                name_line1 = name[:20]
                p.text(f"{idx:<3} {name_line1:<20} x{qty:<3} {total:>7.0f}\n")

                # Continuation if name is long
                if len(name) > 20:
                    p.text(f"    {name[20:44]}\n")

                # Note
                if item.get('note'):
                    p.text(f"    >> {item['note']}\n")

            p.text("=" * W + "\n")

            # ── Totals ────────────────────────────────────────────────
            p.set(align='left')
            subtotal   = order_data.get('subtotal', 0)
            discount   = order_data.get('discount', 0)
            service    = order_data.get('service_charge', 0)
            tax        = order_data.get('tax', 0)
            grand      = order_data.get('grand_total', 0)
            pay_method = order_data.get('payment_method', '')

            p.text(_row("Subtotal :", f"Rs. {int(subtotal):,}"))
            if discount:
                p.text(_row("Discount :", f"-Rs.{int(discount):,}"))
            if service:
                p.text(_row("Service  :", f"Rs. {int(service):,}"))
            if tax:
                p.text(_row("Tax/GST  :", f"Rs. {int(tax):,}"))

            p.text("-" * W + "\n")

            # ── Grand Total (biggest) ──────────────────────────────────
            p.set(align='center', bold=True, double_height=True)
            p.text(f"TOTAL  Rs. {int(grand):,}\n")
            p.set(bold=False, double_height=False)

            if pay_method and pay_method not in ('Pending', ''):
                p.text("-" * W + "\n")
                p.set(align='left')
                p.text(_row("Payment  :", pay_method))

            # ── Footer ────────────────────────────────────────────────
            p.text("=" * W + "\n")
            p.set(align='center', bold=True)
            p.text(f"{ri.get('footer','*** Thank You! Visit Again ***')}\n")
            p.set(bold=False)
            p.text(f"Powered by Abyte POS\n")
            p.text("\n\n")
            p.cut()
            p.close()
            result[0] = True
            result[1] = "Printed Successfully"

        except ImportError:
            result[0] = False; result[1] = "python-escpos not found"
        except Exception as e:
            result[0] = False; result[1] = str(e)

    t = threading.Thread(target=_print, daemon=True)
    t.start()
    t.join(timeout=PRINT_TIMEOUT)
    if t.is_alive():
        return False, "Network printer timeout or not responding"
    if result[0] is None:
        return False, "Print state unknown"
    return result[0], result[1]


def print_http(order_data, config, is_kot=False):
    import requests
    try:
        server_url = config.get("server_url", "http://localhost:9100")
        print_data = order_data.copy()
        print_data['print_type'] = 'kot' if is_kot else 'receipt'
        response = requests.post(
            f"{server_url}/print", json=print_data,
            headers={"Content-Type": "application/json"}, timeout=30
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
        return False, f"Cannot connect to print server at {server_url}."
    except requests.exceptions.Timeout:
        return False, "Print server timed out"
    except Exception as e:
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
    <html><head>
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
    </body></html>"""
    return html


def print_report_v2(report_data):
    try:
        restaurant_info = get_restaurant_info()
        printers = get_printers_by_role("receipt")
        printer_config = printers[0] if printers else {}
        ptype = printer_config.get("type", "usb")
        if ptype == "network":
            from escpos.printer import Network
            ip   = printer_config.get("ip")
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
            p.cut(); p.close()
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


# ══════════════════════════════════════════════════════════════════════════════
#  A4 PDF INVOICE (unchanged logic, design preserved)
# ══════════════════════════════════════════════════════════════════════════════

def generate_pdf_invoice(order_data, restaurant_info=None):
    try:
        if not restaurant_info:
            restaurant_info = get_restaurant_info()

        logo_html = ""
        if restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
            logo_path = resolve_resource_path(restaurant_info["logo_path"])
            if os.path.exists(logo_path):
                logo_uri = Path(logo_path).as_uri()
                logo_html = f'<img src="{logo_uri}" style="height:70px; width:auto; object-fit:contain;">'

        items_html = ""
        for i, item in enumerate(order_data.get('items', [])):
            note       = item.get('note', '')
            note_html  = f'<div style="font-size:11px; color:#888; margin-top:3px; font-style:italic;">Note: {note}</div>' if note else ''
            row_bg     = "#FAFBFF" if i % 2 == 0 else "#FFFFFF"
            line_total = item['qty'] * item['price']
            items_html += f"""
            <tr style="background:{row_bg};">
                <td style="padding:12px 16px; font-size:13px; color:#1E2235; border-bottom:1px solid #EAECF4;">
                    {item['name']}{note_html}
                </td>
                <td style="padding:12px 16px; font-size:13px; color:#6B7280; text-align:center; border-bottom:1px solid #EAECF4;">{item['qty']}</td>
                <td style="padding:12px 16px; font-size:13px; color:#6B7280; text-align:right; border-bottom:1px solid #EAECF4;">Rs. {item['price']:.2f}</td>
                <td style="padding:12px 16px; font-size:13px; font-weight:600; color:#1E2235; text-align:right; border-bottom:1px solid #EAECF4;">Rs. {line_total:.2f}</td>
            </tr>"""

        invoice_no = order_data.get('invoice_no', 'N/A')
        token_no   = order_data.get('token_no', '—')
        date_val   = order_data.get('completed_at') or order_data.get('created_at') or datetime.now()
        date_str   = date_val if isinstance(date_val, str) else date_val.strftime('%d %B %Y  •  %I:%M %p')

        def money_row(label, value, color="#4B5563"):
            return f"""
            <tr>
                <td style="padding:7px 0; font-size:13px; color:#6B7280;">{label}</td>
                <td style="padding:7px 0; font-size:13px; color:{color}; text-align:right; font-weight:500;">Rs. {value:.2f}</td>
            </tr>"""

        subtotal_row = money_row("Subtotal", order_data.get('subtotal', 0))
        discount_val = order_data.get('discount', 0)
        service_val  = order_data.get('service_charge', 0)
        tax_val      = order_data.get('tax', 0)

        discount_row = f"""
            <tr>
                <td style="padding:7px 0; font-size:13px; color:#EF4444;">Discount</td>
                <td style="padding:7px 0; font-size:13px; color:#EF4444; text-align:right; font-weight:500;">− Rs. {discount_val:.2f}</td>
            </tr>""" if discount_val else ""
        service_row = money_row("Service Charge", service_val) if service_val else ""
        tax_row     = money_row("Tax (GST)", tax_val) if tax_val else ""

        html_content = f"""
        <!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 0; }}
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ font-family: Arial, Helvetica, sans-serif; font-size:13px; color:#1E2235; background:#fff; }}
            .page {{ width:210mm; min-height:297mm; display:flex; flex-direction:row; }}
            .sidebar {{ width:8px; background:linear-gradient(180deg,#4F46E5 0%,#7C3AED 100%); flex-shrink:0; }}
            .main {{ flex:1; padding:32px 36px 36px 36px; }}
            .header {{ display:table; width:100%; margin-bottom:32px; padding-bottom:24px; border-bottom:2px solid #EAECF4; }}
            .header-left  {{ display:table-cell; vertical-align:top; width:55%; }}
            .header-right {{ display:table-cell; vertical-align:top; text-align:right; }}
            .restaurant-name {{ font-size:22px; font-weight:800; color:#1E2235; letter-spacing:-0.5px; margin-bottom:4px; }}
            .restaurant-sub  {{ font-size:12px; color:#9CA3AF; line-height:1.6; }}
            .invoice-badge  {{ display:inline-block; background:#4F46E5; color:white; font-size:11px; font-weight:700; letter-spacing:2px; padding:4px 14px; border-radius:20px; text-transform:uppercase; margin-bottom:10px; }}
            .invoice-number {{ font-size:26px; font-weight:800; color:#1E2235; letter-spacing:-0.5px; }}
            .invoice-date   {{ font-size:12px; color:#9CA3AF; margin-top:4px; }}
            .info-grid {{ display:table; width:100%; margin-bottom:28px; border:1.5px solid #EAECF4; border-radius:10px; overflow:hidden; }}
            .info-cell {{ display:table-cell; padding:14px 20px; border-right:1.5px solid #EAECF4; width:33%; }}
            .info-cell:last-child {{ border-right:none; }}
            .info-label {{ font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#9CA3AF; margin-bottom:4px; }}
            .info-value {{ font-size:14px; font-weight:700; color:#1E2235; }}
            .items-table {{ width:100%; border-collapse:collapse; margin-bottom:24px; border:1.5px solid #EAECF4; border-radius:10px; overflow:hidden; }}
            .items-table thead tr {{ background:#1E2235; }}
            .items-table thead th {{ padding:13px 16px; font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#A5B4FC; text-align:left; }}
            .items-table thead th:nth-child(2) {{ text-align:center; }}
            .items-table thead th:nth-child(3), .items-table thead th:nth-child(4) {{ text-align:right; }}
            .totals-wrapper {{ display:table; width:100%; }}
            .totals-spacer  {{ display:table-cell; width:55%; }}
            .totals-box     {{ display:table-cell; width:45%; vertical-align:top; }}
            .totals-inner   {{ border:1.5px solid #EAECF4; border-radius:10px; overflow:hidden; }}
            .totals-rows    {{ padding:16px 20px 0 20px; }}
            .totals-rows table {{ width:100%; border-collapse:collapse; }}
            .grand-total-row {{ background:#4F46E5; padding:16px 20px; display:table; width:100%; margin-top:8px; }}
            .grand-label {{ display:table-cell; font-size:13px; font-weight:800; color:white; letter-spacing:0.5px; text-transform:uppercase; }}
            .grand-value {{ display:table-cell; font-size:18px; font-weight:800; color:white; text-align:right; }}
            .footer {{ margin-top:40px; padding-top:20px; border-top:1.5px dashed #EAECF4; text-align:center; }}
            .footer-msg {{ font-size:14px; font-weight:700; color:#4F46E5; margin-bottom:6px; }}
            .footer-sub {{ font-size:11px; color:#C4C9D8; }}
        </style></head>
        <body>
        <div class="page">
            <div class="sidebar"></div>
            <div class="main">
                <div class="header">
                    <div class="header-left">
                        {logo_html}
                        <div class="restaurant-name" style="margin-top:{'10px' if logo_html else '0'};">{restaurant_info['name']}</div>
                        <div class="restaurant-sub">{restaurant_info['address']}<br>Tel: {restaurant_info['phone']}</div>
                    </div>
                    <div class="header-right">
                        <div class="invoice-badge">Invoice</div>
                        <div class="invoice-number">#{invoice_no}</div>
                        <div class="invoice-date">{date_str}</div>
                    </div>
                </div>
                <div class="info-grid">
                    <div class="info-cell"><div class="info-label">Token No.</div><div class="info-value">{token_no}</div></div>
                    <div class="info-cell"><div class="info-label">Table</div><div class="info-value">{order_data.get('table_no','Takeaway')}</div></div>
                    <div class="info-cell"><div class="info-label">Customer</div><div class="info-value">{order_data.get('customer_name','Guest')}</div></div>
                </div>
                <table class="items-table">
                    <thead><tr>
                        <th style="width:50%;">Description</th>
                        <th style="width:10%;">Qty</th>
                        <th style="width:20%;">Unit Price</th>
                        <th style="width:20%;">Total</th>
                    </tr></thead>
                    <tbody>{items_html}</tbody>
                </table>
                <div class="totals-wrapper">
                    <div class="totals-spacer"></div>
                    <div class="totals-box">
                        <div class="totals-inner">
                            <div class="totals-rows">
                                <table>{subtotal_row}{discount_row}{service_row}{tax_row}</table>
                            </div>
                            <div class="grand-total-row">
                                <div class="grand-label">Grand Total</div>
                                <div class="grand-value">Rs. {order_data.get('grand_total',0):.2f}</div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="footer">
                    <div class="footer-msg">{restaurant_info.get('footer','Thank you for your visit!')}</div>
                    <div class="footer-sub">This is a computer-generated invoice — no signature required.</div>
                </div>
            </div>
        </div>
        </body></html>"""

        invoice_dir = os.path.join(os.getcwd(), "invoices")
        os.makedirs(invoice_dir, exist_ok=True)
        filename  = f"Invoice_{order_data.get('invoice_no', 'Unknown')}.pdf"
        filename  = "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_', '-'))
        file_path = os.path.join(invoice_dir, filename)

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