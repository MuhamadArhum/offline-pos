from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo
from PyQt6.QtGui import QTextDocument, QPageSize, QPageLayout
from PyQt6.QtCore import QMarginsF, QSizeF
from datetime import datetime
import os
from pathlib import Path

from backend.core.config import load_config as load_printer_config, resolve_resource_path
from backend.services.category_service import get_category_by_name

# ─── Print Design Defaults ──────────────────────────────────────────────────

_DEFAULT_BILL_DESIGN = {
    "paper_size": "80mm", "font_size": 9,
    "show_logo": True, "show_token": True, "show_customer": True,
    "show_waiter": True, "show_tax": True, "show_service_charge": True,
    "show_discount": True, "bill_copy": "ORIGINAL",
    "header_extra": "", "footer_extra": "",
}

_DEFAULT_KOT_DESIGN = {
    "font_size": 11, "kot_title": "KITCHEN ORDER TICKET",
    "show_table": True, "show_token": True, "show_order_type": True,
    "show_waiter": True, "show_notes": True, "show_category_headers": True,
}

def load_print_design():
    config = load_printer_config()
    pd   = config.get("print_design", {})
    bill = {**_DEFAULT_BILL_DESIGN, **pd.get("bill", {})}
    kot  = {**_DEFAULT_KOT_DESIGN,  **pd.get("kot",  {})}
    return {
        "bill": bill,
        "kot":  kot,
        "preview_before_print": pd.get("preview_before_print", False),
    }

# ─── Misc ───────────────────────────────────────────────────────────────────

PRINT_LOG_FILE        = "logs/print_log.txt"
PRINT_TIMEOUT         = 5
_print_queue          = []
_queue_thread         = None
_queue_lock           = None
_PDF_PRINTER_KEYWORDS = ["pdf", "xps", "fax", "onenote", "microsoft print"]
_MAX_LOG_BYTES        = 5 * 1024 * 1024  # 5 MB

def _get_real_printer_name(preferred_name=None):
    if preferred_name:
        return preferred_name
    for info in QPrinterInfo.availablePrinters():
        if not any(kw in info.printerName().lower() for kw in _PDF_PRINTER_KEYWORDS):
            return info.printerName()
    return None

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
        ts      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        inv     = order_data.get("invoice_no", "N/A")
        tbl     = order_data.get("table_no",   "N/A")
        total   = order_data.get("grand_total", 0)
        entry   = f"[{ts}] {print_type.upper()} - Invoice: {inv} | Table: {tbl} | Total: Rs {total:,.2f} | Status: {status}"
        if error_msg:
            entry += f" | Error: {error_msg}"
        with open(PRINT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception as e:
        print(f"Error logging print job: {e}")

def get_restaurant_info(config=None):
    if not config:
        config = load_printer_config()
    info = config.get("restaurant_info", {})
    return {
        "name":       info.get("name",       "RESTAURANT NAME"),
        "address":    info.get("address",    "123 Food Street, City"),
        "phone":      info.get("phone",      "0300-1234567"),
        "footer":     info.get("footer",     "*** THANK YOU VISIT AGAIN ***"),
        "logo_path":  info.get("logo_path",  config.get("logo_path", "app/resources/POS.png")),
        "print_logo": info.get("print_logo", config.get("print_logo", True)),
    }

def get_printers_by_role(role):
    config   = load_printer_config()
    printers = config.get("printers", [])
    result   = [p for p in printers if role in p.get("roles", [])]
    if not result:
        if role == "receipt":
            p = config.get("receipt_printer")
            if p:
                result.append(p)
            elif "printer" in config:
                result.append(config["printer"])
        elif role == "kot":
            p = config.get("kot_printer")
            if p:
                if p.get("use_same"):
                    rp = config.get("receipt_printer")
                    if rp:
                        result.append(rp)
                else:
                    result.append(p)
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  PROFESSIONAL THERMAL INVOICE — 80mm  (White / No Black Backgrounds)
# ══════════════════════════════════════════════════════════════════════════════

def generate_thermal_invoice_html(order_data, restaurant_info=None, print_design=None):
    """
    80mm thermal invoice — pure table-based layout (no flexbox).
    QTextDocument compatible.
    """
    if not restaurant_info:
        restaurant_info = get_restaurant_info()
    if print_design is None:
        print_design = load_print_design().get("bill", _DEFAULT_BILL_DESIGN)

    show_logo     = print_design.get("show_logo",           True)
    show_token    = print_design.get("show_token",          True)
    show_customer = print_design.get("show_customer",       True)
    show_waiter   = print_design.get("show_waiter",         True)
    show_tax      = print_design.get("show_tax",            True)
    show_service  = print_design.get("show_service_charge", True)
    show_discount = print_design.get("show_discount",       True)
    bill_copy     = print_design.get("bill_copy",           "").strip()
    header_extra  = print_design.get("header_extra",        "").strip()
    footer_extra  = print_design.get("footer_extra",        "").strip()

    # ── Order meta ────────────────────────────────────────────────────────────
    invoice_no  = order_data.get("invoice_no",     "N/A")
    token_no    = order_data.get("token_no",        "")
    date_val    = order_data.get("completed_at") or order_data.get("created_at") or datetime.now()
    if isinstance(date_val, str):
        date_str = date_val
        time_str = ""
    else:
        date_str = date_val.strftime("%d-%m-%Y")
        time_str = date_val.strftime("%I:%M %p")
    table_no    = order_data.get("table_no",       "Takeaway")
    customer    = order_data.get("customer_name",  "Guest")
    waiter      = order_data.get("waiter",         "")
    order_type  = order_data.get("order_type",     "Dine In")
    pay_method  = order_data.get("payment_method", "")
    pay_status  = order_data.get("payment_status", "")
    subtotal    = order_data.get("subtotal",        0)
    discount    = order_data.get("discount",        0)
    service_chg = order_data.get("service_charge",  0)
    tax         = order_data.get("tax",             0)
    grand_total = order_data.get("grand_total",     0)

    S = "font-family:'Courier New',Courier,monospace;"  # base font shortcut

    # ── Logo ─────────────────────────────────────────────────────────────────
    logo_html = ""
    if show_logo and restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
        lp = resolve_resource_path(restaurant_info["logo_path"])
        if os.path.exists(lp):
            logo_html = (
                f'<tr><td align="center" style="padding-bottom:4px;">'
                f'<img src="{Path(lp).as_uri()}" width="60"></td></tr>'
            )

    # ── Extra header/footer lines ─────────────────────────────────────────────
    header_extra_html = (
        f'<tr><td align="center" style="{S}font-size:8pt;color:#444;">{header_extra}</td></tr>'
    ) if header_extra else ""
    footer_extra_html = (
        f'<tr><td align="center" style="{S}font-size:8pt;color:#444;padding-top:2px;">{footer_extra}</td></tr>'
    ) if footer_extra else ""

    # ── Payment status badge ──────────────────────────────────────────────────
    pay_badge_html = ""
    if pay_status == "UNPAID":
        pay_badge_html = (
            f'<tr><td align="center" style="{S}font-size:9pt;font-weight:bold;'
            f'color:#cc0000;border:1px solid #cc0000;padding:3px 0;">'
            f'!! UNPAID !!</td></tr>'
        )
    elif pay_status == "PAID":
        pay_badge_html = (
            f'<tr><td align="center" style="{S}font-size:9pt;font-weight:bold;'
            f'color:#007700;border:1px solid #007700;padding:3px 0;">'
            f'** PAID **</td></tr>'
        )

    # ── Bill copy + order type row ────────────────────────────────────────────
    copy_label = bill_copy if bill_copy else "ORIGINAL"
    tags_html = (
        f'<tr><td align="center" style="{S}font-size:8pt;font-weight:bold;padding:3px 0;">'
        f'[ {copy_label} ]  &nbsp;  [ {order_type.upper()} ]</td></tr>'
    )

    # ── Token / Table reference box ───────────────────────────────────────────
    ref_box_html = ""
    if show_token and token_no:
        ref_box_html = f"""
<tr><td style="padding:3px 0;">
<table width="100%" cellspacing="0" cellpadding="0"
       style="border-collapse:collapse;border:1px solid #111;">
  <tr>
    <td width="40%" align="center" style="{S}border-right:1px solid #aaa;padding:4px 2px;">
      <div style="{S}font-size:7pt;color:#888;font-weight:bold;">TOKEN</div>
      <div style="{S}font-size:18pt;font-weight:bold;line-height:1.1;">#{token_no}</div>
    </td>
    <td width="30%" align="center" style="{S}border-right:1px solid #aaa;padding:4px 2px;">
      <div style="{S}font-size:7pt;color:#888;font-weight:bold;">TABLE</div>
      <div style="{S}font-size:13pt;font-weight:bold;">{table_no}</div>
    </td>
    <td width="30%" align="center" style="{S}padding:4px 2px;">
      <div style="{S}font-size:7pt;color:#888;font-weight:bold;">COPY</div>
      <div style="{S}font-size:9pt;font-weight:bold;">{copy_label}</div>
    </td>
  </tr>
</table>
</td></tr>"""

    # ── Customer / Waiter row ─────────────────────────────────────────────────
    cust_waiter_html = ""
    if show_customer or (show_waiter and waiter):
        left_cell = (
            f'<td width="50%" style="{S}font-size:8pt;font-weight:bold;padding:2px 0;">'
            f'<span style="font-size:7pt;color:#666;">Customer: </span>{customer}</td>'
        ) if show_customer else '<td width="50%"></td>'
        right_cell = (
            f'<td width="50%" align="right" style="{S}font-size:8pt;font-weight:bold;padding:2px 0;">'
            f'<span style="font-size:7pt;color:#666;">Waiter: </span>{waiter}</td>'
        ) if (show_waiter and waiter) else '<td width="50%"></td>'
        cust_waiter_html = f"""
<tr><td style="padding:2px 0 3px;">
<table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
  <tr>{left_cell}{right_cell}</tr>
</table>
</td></tr>"""

    # ── Items rows ────────────────────────────────────────────────────────────
    IROW = "border-bottom:1px solid #bbb;"   # item row separator (on td)

    items_rows = ""
    for item in order_data.get("items", []):
        note      = item.get("note", "")
        note_html = (
            f'<tr><td colspan="4" style="font-size:7pt;font-weight:normal;'
            f'color:#666;font-style:italic;padding:0 2px 3px 10px;">'
            f'&gt; {note}</td></tr>'
        ) if note else ""
        total = item["qty"] * item["price"]
        items_rows += f"""
  <tr>
    <td style="font-size:9pt;font-weight:bold;padding:3px 2px 3px 0;
               vertical-align:top;width:46%;{IROW}">{item['name']}</td>
    <td align="center" style="font-size:9pt;font-weight:bold;padding:3px 1px;
               vertical-align:top;width:10%;{IROW}">{item['qty']}</td>
    <td align="right" style="font-size:9pt;font-weight:bold;padding:3px 1px;
               vertical-align:top;width:22%;{IROW}">{item['price']:.0f}</td>
    <td align="right" style="font-size:9pt;font-weight:bold;padding:3px 0;
               vertical-align:top;width:22%;{IROW}">{total:.0f}</td>
  </tr>{note_html}"""

    # ── Totals rows ───────────────────────────────────────────────────────────
    TROW = "border-bottom:1px solid #ccc;"

    def tot_row(label, value, is_neg=False):
        val_str = f"- Rs.{value:,.0f}" if is_neg else f"Rs.{value:,.0f}"
        return (
            f'<tr>'
            f'<td style="font-size:9pt;color:#444;padding:3px 4px;{TROW}">{label}</td>'
            f'<td align="right" style="font-size:9pt;font-weight:bold;padding:3px 4px;{TROW}">{val_str}</td>'
            f'</tr>'
        )

    totals_rows  = tot_row("Sub Total", subtotal)
    if discount    and show_discount: totals_rows += tot_row("Discount",       discount,    is_neg=True)
    if service_chg and show_service:  totals_rows += tot_row("Service Charge", service_chg)
    if tax         and show_tax:      totals_rows += tot_row("Tax / GST",      tax)
    if pay_method and pay_method not in ("Pending", ""):
        totals_rows += (
            f'<tr>'
            f'<td style="font-size:9pt;color:#444;padding:3px 4px;{TROW}">Payment</td>'
            f'<td align="right" style="font-size:9pt;font-weight:bold;padding:3px 4px;{TROW}">{pay_method}</td>'
            f'</tr>'
        )

    rest_name   = restaurant_info.get('name', 'RESTAURANT').upper()
    rest_addr   = restaurant_info.get('address', '')
    rest_phone  = restaurant_info.get('phone', '')
    rest_footer = restaurant_info.get('footer', '*** THANK YOU - VISIT AGAIN ***')
    order_type_u = order_type.upper()
    copy_label_u = copy_label.upper()

    TH = f"border-top:2px solid #000;border-bottom:1px solid #000;"   # table header cell border
    SEP = f"border-top:1px solid #000;"                                # separator

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 9pt;
      font-weight: bold;
      color: #000;
      background: #fff;
  }}
  td, th {{ padding: 0; margin: 0; }}
</style>
</head>
<body>

<table width="100%" cellspacing="0" cellpadding="0" border="0">

  <!-- HEADER -->
  {logo_html}
  <tr><td align="center" style="font-size:13pt;font-weight:bold;padding:5px 4px 1px;">
    {rest_name}
  </td></tr>
  <tr><td align="center" style="font-size:8pt;font-weight:normal;padding:1px 4px;">
    {rest_addr}
  </td></tr>
  <tr><td align="center" style="font-size:9pt;font-weight:bold;padding:1px 4px 3px;">
    Tel: {rest_phone}
  </td></tr>
  {header_extra_html}
  <tr><td style="border-bottom:2px solid #000;font-size:1pt;">&nbsp;</td></tr>

  <!-- INVOICE TITLE -->
  <tr><td align="center" style="font-size:10pt;font-weight:bold;padding:4px 0 3px;">
    ----  INVOICE  ----
  </td></tr>

  <!-- META STRIP: Invoice / Date / Time / Type -->
  <tr><td style="padding:1px 0 1px;">
    <table width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <td width="28%" valign="top"
            style="font-size:7pt;padding:3px 2px;{TH}border-right:1px solid #aaa;">
          <b style="color:#555;">Invoice#</b><br/><b style="font-size:8pt;">{invoice_no}</b>
        </td>
        <td width="24%" valign="top"
            style="font-size:7pt;padding:3px 2px;{TH}border-right:1px solid #aaa;">
          <b style="color:#555;">Date</b><br/><b style="font-size:8pt;">{date_str}</b>
        </td>
        <td width="24%" valign="top"
            style="font-size:7pt;padding:3px 2px;{TH}border-right:1px solid #aaa;">
          <b style="color:#555;">Time</b><br/><b style="font-size:8pt;">{time_str}</b>
        </td>
        <td width="24%" valign="top"
            style="font-size:7pt;padding:3px 2px;{TH}">
          <b style="color:#555;">Type</b><br/><b style="font-size:8pt;">{order_type_u}</b>
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- PAY STATUS -->
  {pay_badge_html}

  <!-- COPY / TYPE TAGS -->
  <tr><td align="center" style="font-size:8pt;font-weight:bold;padding:3px 0;">
    [ {copy_label_u} ] &nbsp; [ {order_type_u} ]
  </td></tr>

  <!-- TOKEN / TABLE BOX -->
  {ref_box_html}

  <!-- CUSTOMER / WAITER -->
  {cust_waiter_html}

  <!-- ITEMS TABLE -->
  <tr><td style="padding-top:3px;">
    <table width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <th align="left"  width="46%"
            style="font-size:8pt;padding:3px 2px 3px 0;{TH}">ITEM</th>
        <th align="center" width="10%"
            style="font-size:8pt;padding:3px 1px;{TH}">QTY</th>
        <th align="right" width="22%"
            style="font-size:8pt;padding:3px 1px;{TH}">RATE</th>
        <th align="right" width="22%"
            style="font-size:8pt;padding:3px 0;{TH}">AMT</th>
      </tr>
      {items_rows}
      <tr>
        <td colspan="4" style="{SEP}font-size:1pt;">&nbsp;</td>
      </tr>
    </table>
  </td></tr>

  <!-- TOTALS -->
  <tr><td style="padding:2px 0;">
    <table width="100%" cellspacing="0" cellpadding="0" border="0"
           style="border:1px solid #aaa;">
      {totals_rows}
    </table>
  </td></tr>

  <!-- GRAND TOTAL -->
  <tr><td style="padding:3px 0;">
    <table width="100%" cellspacing="0" cellpadding="0" border="0"
           style="border:2px solid #000;">
      <tr>
        <td style="font-size:9pt;font-weight:bold;padding:5px 6px;">GRAND TOTAL</td>
        <td align="right" style="font-size:15pt;font-weight:bold;padding:5px 6px;">
          Rs.{grand_total:,.0f}
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="{SEP}font-size:1pt;">&nbsp;</td></tr>
  <tr><td align="center" style="font-size:9pt;font-weight:bold;padding:3px 4px;">
    {rest_footer}
  </td></tr>
  {footer_extra_html}
  <tr><td align="center" style="font-size:7pt;font-weight:normal;color:#888;padding:2px 4px 6px;">
    Abyte POS | {invoice_no} | {datetime.now().strftime('%d-%m-%Y')}
  </td></tr>

</table>
</body>
</html>"""
    return html


# ══════════════════════════════════════════════════════════════════════════════
#  SIMPLE KOT — 80mm Kitchen Order Ticket  (No Black Backgrounds)
# ══════════════════════════════════════════════════════════════════════════════

def generate_kot_html(order_data, restaurant_info=None, print_design=None):
    """
    80mm KOT — pure table-based layout (no flexbox). QTextDocument compatible.
    """
    if print_design is None:
        print_design = load_print_design().get("kot", _DEFAULT_KOT_DESIGN)

    kot_title   = print_design.get("kot_title",       "KITCHEN ORDER TICKET")
    show_table  = print_design.get("show_table",      True)
    show_token  = print_design.get("show_token",      True)
    show_type   = print_design.get("show_order_type", True)
    show_waiter = print_design.get("show_waiter",     True)
    show_notes  = print_design.get("show_notes",      True)

    date_val = order_data.get("updated_at") or order_data.get("created_at") or datetime.now()
    if isinstance(date_val, str):
        date_str = date_val
        time_str = ""
    else:
        date_str = date_val.strftime("%d-%m-%Y")
        time_str = date_val.strftime("%I:%M %p")

    token_no    = order_data.get("token_no",   "")
    table_no    = order_data.get("table_no",   "Takeaway")
    waiter      = order_data.get("waiter",     "")
    type_val    = order_data.get("order_type", "")
    inv_no      = order_data.get("invoice_no", "New")
    items       = order_data.get("items",      [])
    rest_name   = (restaurant_info or {}).get("name", "RESTAURANT")

    S = "font-family:'Courier New',Courier,monospace;"

    # ── Token / Table box ─────────────────────────────────────────────────────
    ref_box_html = ""
    if (show_token and token_no) or show_table:
        tok_cell = (
            f'<td width="50%" align="center"'
            f' style="{S}border-right:2px solid #111;padding:5px 3px;">'
            f'<div style="font-size:7pt;color:#888;font-weight:bold;">TOKEN</div>'
            f'<div style="font-size:24pt;font-weight:bold;line-height:1.1;">#{token_no}</div>'
            f'</td>'
        ) if (show_token and token_no) else ""
        tbl_cell = (
            f'<td width="50%" align="center"'
            f' style="{S}padding:5px 3px;">'
            f'<div style="font-size:7pt;color:#888;font-weight:bold;">TABLE</div>'
            f'<div style="font-size:20pt;font-weight:bold;line-height:1.1;">{table_no}</div>'
            f'</td>'
        ) if show_table else ""
        if tok_cell or tbl_cell:
            ref_box_html = (
                f'<tr><td>'
                f'<table width="100%" cellspacing="0" cellpadding="0"'
                f' style="border-collapse:collapse;border-top:2px solid #111;'
                f'border-bottom:2px solid #111;">'
                f'<tr>{tok_cell}{tbl_cell}</tr></table>'
                f'</td></tr>'
            )

    # ── Info strip ────────────────────────────────────────────────────────────
    info_cells = (
        f'<td style="{S}font-size:7pt;padding:3px 3px;border-right:1px solid #ccc;">'
        f'<div style="color:#888;font-weight:bold;">Order#</div>'
        f'<div style="font-weight:bold;">{inv_no}</div></td>'
        f'<td style="{S}font-size:7pt;padding:3px 3px;border-right:1px solid #ccc;">'
        f'<div style="color:#888;font-weight:bold;">Date</div>'
        f'<div style="font-weight:bold;">{date_str}</div></td>'
    )
    if time_str:
        info_cells += (
            f'<td style="{S}font-size:7pt;padding:3px 3px;border-right:1px solid #ccc;">'
            f'<div style="color:#888;font-weight:bold;">Time</div>'
            f'<div style="font-weight:bold;">{time_str}</div></td>'
        )
    if show_waiter and waiter:
        info_cells += (
            f'<td style="{S}font-size:7pt;padding:3px 3px;border-right:1px solid #ccc;">'
            f'<div style="color:#888;font-weight:bold;">Waiter</div>'
            f'<div style="font-weight:bold;">{waiter}</div></td>'
        )
    if show_type and type_val:
        info_cells += (
            f'<td style="{S}font-size:7pt;padding:3px 3px;">'
            f'<div style="color:#888;font-weight:bold;">Type</div>'
            f'<div style="font-weight:bold;">{type_val}</div></td>'
        )

    # ── Items rows ─────────────────────────────────────────────────────────────
    KROW = "border-bottom:1px solid #bbb;"

    items_rows = ""
    for item in items:
        note_html = ""
        if show_notes and item.get("note"):
            note_html = (
                f'<tr><td colspan="2"'
                f' style="font-size:8pt;font-weight:normal;color:#555;'
                f'font-style:italic;padding:0 3px 4px 14px;">'
                f'&gt; {item["note"]}</td></tr>'
            )
        items_rows += f"""
  <tr>
    <td style="font-size:12pt;font-weight:bold;padding:5px 3px 5px 0;
               vertical-align:middle;width:72%;{KROW}">{item['name']}</td>
    <td align="right" style="font-size:16pt;font-weight:bold;padding:5px 0 5px 3px;
               vertical-align:middle;width:28%;{KROW}">x{item['qty']}</td>
  </tr>
  {note_html}"""

    TH = "border-top:2px solid #000;border-bottom:1px solid #000;"
    SEP = "border-top:2px solid #000;"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 9pt;
      font-weight: bold;
      color: #000;
      background: #fff;
  }}
  td, th {{ padding: 0; margin: 0; }}
</style>
</head>
<body>

<table width="100%" cellspacing="0" cellpadding="0" border="0">

  <!-- HEADER -->
  <tr><td align="center"
          style="font-size:13pt;font-weight:bold;padding:5px 4px 2px;
                 border-bottom:2px solid #000;">
    {kot_title.upper()}
  </td></tr>
  <tr><td align="center"
          style="font-size:8pt;font-weight:normal;color:#444;
                 padding:2px 4px 3px;border-bottom:1px solid #aaa;">
    {rest_name}
  </td></tr>

  <!-- INFO STRIP -->
  <tr><td style="padding:1px 0;">
    <table width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>{info_cells}</tr>
    </table>
  </td></tr>

  <!-- TOKEN / TABLE -->
  {ref_box_html}

  <!-- ITEMS -->
  <tr><td style="padding-top:2px;">
    <table width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <th align="left"  width="72%"
            style="font-size:8pt;padding:3px 3px 3px 0;{TH}">ITEM</th>
        <th align="right" width="28%"
            style="font-size:8pt;padding:3px 0 3px 3px;{TH}">QTY</th>
      </tr>
      {items_rows}
    </table>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="{SEP}font-size:1pt;">&nbsp;</td></tr>
  <tr><td align="center"
          style="font-size:8pt;font-weight:bold;color:#444;padding:3px 4px 6px;">
    -- KITCHEN COPY --
  </td></tr>

</table>
</body>
</html>"""
    return html


# ── Legacy KOT (backward compat) ─────────────────────────────────────────────
def _generate_kot_html_legacy(order_data, restaurant_info=None):
    if not restaurant_info:
        restaurant_info = {"name": "KITCHEN ORDER TICKET", "address": "", "phone": ""}
    items_html = "".join(
        f'<tr><td style="font-size:14px;font-weight:bold;">{i["name"]}</td>'
        f'<td style="font-size:14px;font-weight:bold;">{i["qty"]}</td></tr>'
        for i in order_data.get("items", [])
    )
    date_val = order_data.get("updated_at") or order_data.get("created_at") or datetime.now()
    date_str = date_val if isinstance(date_val, str) else date_val.strftime("%Y-%m-%d %H:%M:%S")
    return f"""<html><head><style>
        body{{font-family:'Courier New',monospace;font-size:12px;}}
        h2{{text-align:center;margin:0;}} p{{margin:2px 0;}} .center{{text-align:center;}}
        table{{width:100%;border-collapse:collapse;margin-top:10px;}}
        th{{border-bottom:1px dashed #000;text-align:left;}} td{{padding:5px 0;}}
    </style></head><body>
        <h2>{restaurant_info.get('name','KITCHEN ORDER TICKET')}</h2><br>
        <p style="font-size:16px;font-weight:bold;">Table: {order_data.get('table_no','Takeaway')}</p>
        <p style="font-size:14px;font-weight:bold;">Token #: {order_data.get('token_no','')}</p>
        <p>Order #: {order_data.get('invoice_no','New')}</p>
        <p>Date: {date_str}</p>
        <p>Waiter: {order_data.get('waiter','Server')}</p>
        <table><thead><tr><th width="80%">Item</th><th width="20%">Qty</th></tr></thead>
        <tbody>{items_html}</tbody></table>
        <br><p class="center">*** KITCHEN COPY ***</p>
    </body></html>"""


# ══════════════════════════════════════════════════════════════════════════════
#  RECEIPT HTML (simple fallback — unchanged)
# ══════════════════════════════════════════════════════════════════════════════

def generate_receipt_html(order_data, restaurant_info=None):
    if not restaurant_info:
        restaurant_info = get_restaurant_info()
    logo_html = ""
    if restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
        lp = resolve_resource_path(restaurant_info["logo_path"])
        if os.path.exists(lp):
            logo_html = f'<div class="center"><img src="{Path(lp).as_uri()}" width="100"></div>'
    items_html = ""
    for item in order_data.get("items", []):
        note = item.get("note", "")
        note_html = f'<br><i style="font-size:10px;">({note})</i>' if note else ""
        items_html += (
            f'<tr><td>{item["name"]}{note_html}</td><td>{item["qty"]}</td>'
            f'<td style="text-align:right;">{item["price"]:.2f}</td>'
            f'<td style="text-align:right;">{item["qty"]*item["price"]:.2f}</td></tr>'
        )
    invoice_no     = order_data.get("invoice_no", "N/A")
    token_no       = order_data.get("token_no", "")
    date_val       = order_data.get("completed_at") or order_data.get("created_at") or datetime.now()
    date_str       = date_val if isinstance(date_val, str) else date_val.strftime("%Y-%m-%d %H:%M:%S")
    order_type     = order_data.get("order_type", "Dine In")
    bill_type      = order_data.get("bill_type", "")
    bill_type_html = (
        f'<p class="center" style="font-size:13px;font-weight:bold;border:1px solid #000;'
        f'display:inline-block;padding:2px 10px;">{bill_type.upper()} BILL</p>'
    ) if bill_type else ""
    pay_status = order_data.get("payment_status", "")
    if pay_status == "UNPAID":
        pay_status_html = (
            '<p class="center" style="font-size:16px;font-weight:900;border:2px solid #c00;'
            'color:#c00;padding:4px 0;margin:6px 0;letter-spacing:2px;">&#10007; UNPAID &#10007;</p>'
        )
    elif pay_status == "PAID":
        pay_status_html = (
            '<p class="center" style="font-size:16px;font-weight:900;border:2px solid #059669;'
            'color:#059669;padding:4px 0;margin:6px 0;letter-spacing:2px;">&#10003; PAID &#10003;</p>'
        )
    else:
        pay_status_html = ""
    return f"""<html><head><style>
        body{{font-family:'Courier New',monospace;font-size:12px;}}
        h2{{text-align:center;margin:0;}} p{{margin:2px 0;}}
        .center{{text-align:center;}} .right{{text-align:right;}}
        table{{width:100%;border-collapse:collapse;margin-top:10px;}}
        th{{border-bottom:1px dashed #000;text-align:left;}} td{{padding:2px 0;}}
        .total-row{{font-weight:bold;border-top:1px dashed #000;}}
    </style></head><body>
        {logo_html}
        <h1>{restaurant_info['name']}</h1>
        <p class="center">{restaurant_info['address']}</p>
        <p class="center">Tel: {restaurant_info['phone']}</p><br>
        {pay_status_html}
        <p class="center">{bill_type_html}</p>
        <p>Order #: {invoice_no}</p>
        <p style="font-size:14px;font-weight:bold;">Token #: {token_no}</p>
        <p>Date: {date_str}</p>
        <p>Type: {order_type}</p>
        <p>Table: {order_data.get('table_no','Takeaway')}</p>
        <p>Customer: {order_data.get('customer_name','Guest')}</p>
        <table><thead><tr>
            <th width="50%">Item</th><th width="10%">Qty</th>
            <th width="20%" class="right">Price</th><th width="20%" class="right">Total</th>
        </tr></thead><tbody>{items_html}</tbody></table><br>
        <div class="right">
            <p>Subtotal: {order_data.get('subtotal',0):.2f}</p>
            <p>Discount: -{order_data.get('discount',0):.2f}</p>
            <p>Service Charge: {order_data.get('service_charge',0):.2f}</p>
            <p>Tax: {order_data.get('tax',0):.2f}</p>
            <p class="total-row" style="font-size:14px;">TOTAL: {order_data.get('grand_total',0):.2f}</p>
        </div><br>
        <p class="center">{restaurant_info.get('footer','*** THANK YOU VISIT AGAIN ***')}</p>
    </body></html>"""


# ══════════════════════════════════════════════════════════════════════════════
#  PRINT FUNCTIONS  (logic unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════

def _unified_print(order_data, config, is_kot=False):
    """
    Universal print function — USB aur Network dono ek jagah handle.
    HTML design dono ke liye same use hoti hai.

    Flow:
      USB   → Windows mein printer check → QPrinter + HTML
      Network → Windows mein check → QPrinter + HTML
              → nahi mila → ESC/POS direct TCP
    """
    if not config:
        return False, "Koi printer configured nahi. Settings > Printers mein add karein."

    ptype = config.get("type", "usb")
    ri    = get_restaurant_info()

    # ── Build verified Windows printer map ──────────────────────────────────────
    available = {
        info.printerName().lower(): info.printerName()
        for info in QPrinterInfo.availablePrinters()
        if not any(kw in info.printerName().lower() for kw in _PDF_PRINTER_KEYWORDS)
    }

    def _qprint(win_name):
        html = generate_kot_html(order_data, ri) if is_kot else generate_thermal_invoice_html(order_data, ri)
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPrinterName(win_name)
            printer.setPageSize(QPageSize(QSizeF(80, 297), QPageSize.Unit.Millimeter, "Thermal 80mm"))
            printer.setPageOrientation(QPageLayout.Orientation.Portrait)
            printer.setPageMargins(QMarginsF(2, 2, 2, 2), QPageLayout.Unit.Millimeter)
            doc = QTextDocument()
            doc.setHtml(html)
            paint_rect = printer.pageLayout().paintRect(QPageLayout.Unit.Point)
            doc.setPageSize(QSizeF(paint_rect.width(), paint_rect.height()))
            doc.print(printer)
            return True, f"Printed to {win_name}"
        except Exception as e:
            return False, str(e)

    # ── USB printer ──────────────────────────────────────────────────────────────
    if ptype == "usb":
        want = (config.get("usb_name") or "").lower()
        matched = available.get(want) or next(iter(available.values()), None)
        if matched:
            return _qprint(matched)
        return False, "Koi Windows printer nahi mila. Control Panel > Devices & Printers check karein."

    # ── Network printer ──────────────────────────────────────────────────────────
    if ptype == "network":
        # First check if printer is installed in Windows (by usb_name label)
        want = (config.get("usb_name") or "").lower()
        matched = available.get(want) if want else None
        if matched:
            return _qprint(matched)
        # Not in Windows — use raw ESC/POS over TCP
        if config.get("ip"):
            return print_network(order_data, config, is_kot=is_kot, restaurant_info=ri)
        return False, "Network printer ka IP nahi mila. Settings check karein."

    return False, f"Unknown printer type: {ptype}"


def print_thermal_invoice(order_data, parent=None):
    printers = get_printers_by_role("receipt")
    if not printers:
        return _print_thermal_usb(order_data, {})
    config = printers[0]
    if config.get("type") == "network":
        return print_network(order_data, config, is_kot=False)
    return _print_thermal_usb(order_data, config)


def _print_thermal_usb(order_data, config, restaurant_info=None):
    try:
        preferred    = config.get("usb_name") or config.get("usb_printer_name")
        printer_name = _get_real_printer_name(preferred)
        if not printer_name:
            return False, "Koi real printer nahi mila. PDF printers skip kiye gaye."
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(printer_name)
        printer.setPageSize(QPageSize(QSizeF(80, 297), QPageSize.Unit.Millimeter, "Thermal 80mm"))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setPageMargins(QMarginsF(2, 2, 2, 2), QPageLayout.Unit.Millimeter)
        printer.setFullPage(False)
        doc = QTextDocument()
        doc.setHtml(generate_thermal_invoice_html(order_data, restaurant_info))
        paint_rect = printer.pageLayout().paintRect(QPageLayout.Unit.Point)
        doc.setPageSize(QSizeF(paint_rect.width(), paint_rect.height()))
        doc.print(printer)
        return True, "Thermal Invoice Printed Successfully"
    except Exception as e:
        print(f"Thermal USB Print Error: {e}")
        return False, str(e)


def print_receipt(order_data, parent=None):
    if not order_data.get("payment_status"):
        order_data = dict(order_data)
        order_data["payment_status"] = "PAID" if order_data.get("status") == "Completed" else "UNPAID"
    log_print_job("receipt", order_data, "attempting")
    printers = get_printers_by_role("receipt")
    config   = printers[0] if printers else {}
    success, msg = _unified_print(order_data, config, is_kot=False)
    if success:
        log_print_job("receipt", order_data, "success")
    else:
        log_print_job("receipt", order_data, "failed", msg)
    return success, msg


def print_kot(order_data, parent=None):
    log_print_job("kot", order_data, "attempting")
    items = order_data.get("items", [])
    if not items:
        return False, "No items to print"
    category_groups = {}
    for item in items:
        cat = item.get("category", "General")
        category_groups.setdefault(cat, []).append(item)
    results, success_count = [], 0
    for category, cat_items in category_groups.items():
        cat_info     = get_category_by_name(category)
        printer_role = cat_info.get("printer_role", f"kot-{category.lower()}") if cat_info else f"kot-{category.lower()}"
        cat_order    = {**order_data, "items": cat_items}
        printers     = get_printers_by_role(printer_role) or get_printers_by_role("kot")
        if not printers:
            results.append(f"No printer for {category}")
            continue
        config  = printers[0]
        ok, msg = _unified_print(cat_order, config, is_kot=True)
        results.append(f"{category}: {msg}")
        if ok:
            success_count += 1
    if success_count > 0:
        log_print_job("kot", order_data, "success")
        return True, "; ".join(results)
    log_print_job("kot", order_data, "failed", "; ".join(results))
    return False, "; ".join(results)


def print_test_page_v2(full_config, print_type="receipt"):
    try:
        dummy = {
            "invoice_no": "TEST-001", "table_no": "Test Table",
            "customer_name": "Test Customer",
            "items": [
                {"name": "Test Item 1", "qty": 1, "price": 100},
                {"name": "Test Item 2", "qty": 2, "price": 50},
            ],
            "subtotal": 200, "discount": 0, "service_charge": 0,
            "tax": 0, "grand_total": 200, "created_at": datetime.now(),
        }
        config          = full_config.get("printer_config", {})
        restaurant_info = full_config.get("restaurant_info")
        if config.get("type") == "network":
            return print_network(dummy, config, is_kot=(print_type == "kot"), restaurant_info=restaurant_info)
        return print_usb(dummy, config, is_kot=(print_type == "kot"), restaurant_info=restaurant_info)
    except Exception as e:
        return False, str(e)


def print_usb(order_data, config, is_kot=False, restaurant_info=None):
    try:
        preferred    = config.get("usb_name") or config.get("usb_printer_name")
        printer_name = _get_real_printer_name(preferred)
        if not printer_name:
            return False, "Koi real printer nahi mila. PDF printers skip kiye gaye."
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(printer_name)
        printer.setPageSize(QPageSize(QSizeF(80, 297), QPageSize.Unit.Millimeter, "Thermal 80mm"))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setPageMargins(QMarginsF(2, 2, 2, 2), QPageLayout.Unit.Millimeter)
        doc = QTextDocument()
        doc.setHtml(
            generate_kot_html(order_data, restaurant_info)
            if is_kot else
            generate_thermal_invoice_html(order_data, restaurant_info)
        )
        paint_rect = printer.pageLayout().paintRect(QPageLayout.Unit.Point)
        doc.setPageSize(QSizeF(paint_rect.width(), paint_rect.height()))
        doc.print(printer)
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
                result[0], result[1] = False, "IP Address Missing"; return
            p  = Network(ip, port=port, timeout=PRINT_TIMEOUT)
            ri = restaurant_info or get_restaurant_info()
            W  = 42

            def _row(lbl, val, w=W):
                v   = str(val)
                pad = w - len(lbl) - len(v)
                return lbl + " " * max(pad, 1) + v + "\n"

            pd  = load_print_design()
            dv  = order_data.get("updated_at") or order_data.get("created_at") or datetime.now()
            ds  = dv if isinstance(dv, str) else dv.strftime("%d-%m-%Y %I:%M %p")

            # ── KOT ──────────────────────────────────────────────────────────
            if is_kot:
                kot_cfg  = pd.get("kot", _DEFAULT_KOT_DESIGN)
                kot_title = kot_cfg.get("kot_title", "KITCHEN ORDER TICKET")

                p.set(align="center", bold=True, double_width=True)
                p.text(f"{kot_title}\n")
                p.set(bold=False, double_width=False)
                p.text("=" * W + "\n")

                p.set(align="left", bold=True)
                p.text(f"Order : {order_data.get('invoice_no','')}\n")
                p.text(f"Time  : {ds}\n")
                if kot_cfg.get("show_waiter") and order_data.get("waiter"):
                    p.text(f"Waiter: {order_data['waiter']}\n")
                if kot_cfg.get("show_order_type") and order_data.get("order_type"):
                    p.text(f"Type  : {order_data['order_type'].upper()}\n")
                p.set(bold=False)
                p.text("-" * W + "\n")

                # Token + Table (big)
                tok = order_data.get("token_no", "")
                tbl = order_data.get("table_no", "")
                if tok and kot_cfg.get("show_token"):
                    p.set(align="center", bold=True, double_height=True, double_width=True)
                    p.text(f"#{tok}\n")
                    p.set(bold=False, double_height=False, double_width=False, align="left")
                    p.text("TOKEN NO.\n")
                if tbl and kot_cfg.get("show_table"):
                    p.set(align="left", bold=True)
                    p.text(f"TABLE: {tbl}\n")
                    p.set(bold=False)

                p.text("=" * W + "\n")
                p.set(bold=True); p.text(f"{'ITEM':<32} {'QTY':>5}\n"); p.set(bold=False)
                p.text("-" * W + "\n")

                # Group by category if enabled
                items = order_data.get("items", [])
                if kot_cfg.get("show_category_headers"):
                    from collections import OrderedDict
                    cat_map = OrderedDict()
                    for item in items:
                        cat = (item.get("category") or "General").strip()
                        cat_map.setdefault(cat, []).append(item)
                else:
                    cat_map = {"": items}

                for cat_name, cat_items in cat_map.items():
                    if cat_name:
                        p.set(bold=True)
                        p.text(f"> {cat_name.upper()}\n")
                        p.set(bold=False)
                    for item in cat_items:
                        name = item["name"]
                        qty  = item["qty"]
                        p.set(bold=True, double_height=True)
                        # Truncate long names for double-width
                        p.text(f"{name[:18]:<18} x{qty}\n")
                        p.set(bold=False, double_height=False)
                        if kot_cfg.get("show_notes") and item.get("note"):
                            p.text(f"  >> {item['note']}\n")

                p.text("=" * W + "\n")
                p.set(align="center", bold=True)
                p.text("-- KITCHEN COPY --\n")
                p.set(bold=False)
                p.cut(); p.close()
                result[0], result[1] = True, "KOT Printed"; return

            # ── INVOICE / RECEIPT ─────────────────────────────────────────────
            bill_cfg = pd.get("bill", _DEFAULT_BILL_DESIGN)
            dv  = order_data.get("completed_at") or order_data.get("created_at") or datetime.now()
            ds  = dv if isinstance(dv, str) else dv.strftime("%d-%m-%Y %I:%M %p")

            # Logo
            if bill_cfg.get("show_logo") and ri.get("print_logo") and ri.get("logo_path"):
                try:
                    lp = resolve_resource_path(ri["logo_path"])
                    if os.path.exists(lp):
                        p.image(lp)
                except Exception:
                    pass

            # Header
            p.set(align="center", bold=True, double_width=True)
            name_str = ri.get("name", "RESTAURANT").strip()[:18]
            p.text(f"{name_str}\n")
            p.set(bold=False, double_width=False)
            if ri.get("address"): p.text(f"{ri['address'].strip()}\n")
            if ri.get("phone"):   p.text(f"Tel: {ri['phone'].strip()}\n")

            if bill_cfg.get("header_extra"):
                p.text(f"{bill_cfg['header_extra']}\n")

            p.text("=" * W + "\n")
            p.set(align="center", bold=True, double_width=True)
            p.text("INVOICE\n")
            p.set(bold=False, double_width=False)
            p.text("=" * W + "\n")

            # Bill copy + order type
            copy_tag  = bill_cfg.get("bill_copy", "").strip()
            order_type = order_data.get("order_type", "Dine In")
            p.set(align="center", bold=True)
            if copy_tag:   p.text(f"[ {copy_tag} ]  ")
            p.text(f"[ {order_type.upper()} ]\n")
            p.set(bold=False)

            # Payment status badge
            pay_st = order_data.get("payment_status", "")
            if pay_st in ("PAID", "UNPAID"):
                p.set(align="center", bold=True, double_width=True)
                p.text(f"*** {pay_st} ***\n")
                p.set(bold=False, double_width=False)

            p.text("-" * W + "\n")

            # Meta
            p.set(align="left")
            p.text(f"Invoice : {order_data.get('invoice_no','N/A')}\n")
            p.text(f"Date    : {ds}\n")
            if bill_cfg.get("show_customer"):
                cust = order_data.get("customer_name", "")
                if cust and cust != "Guest":
                    p.text(f"Customer: {cust}\n")
            if bill_cfg.get("show_waiter") and order_data.get("waiter"):
                p.text(f"Waiter  : {order_data['waiter']}\n")

            # Token + Table box
            tok = order_data.get("token_no", "")
            tbl = order_data.get("table_no", "Takeaway")
            p.text("-" * W + "\n")
            if bill_cfg.get("show_token") and tok:
                p.set(align="center", bold=True, double_height=True, double_width=True)
                p.text(f"#{tok}\n")
                p.set(bold=False, double_height=False, double_width=False)
                p.set(align="left", bold=True)
                p.text(f"TOKEN       TABLE: {tbl}\n")
                p.set(bold=False)
            else:
                p.set(bold=True); p.text(f"Table: {tbl}\n"); p.set(bold=False)

            # Items
            p.text("=" * W + "\n")
            p.set(bold=True)
            p.text(f"{'ITEM':<25} {'Q':>2} {'RATE':>6} {'AMT':>6}\n")
            p.set(bold=False)
            p.text("-" * W + "\n")
            for item in order_data.get("items", []):
                qty, name, price = item["qty"], item["name"], item["price"]
                amt   = qty * price
                ntrunc = name[:24]
                p.set(bold=True)
                p.text(f"{ntrunc:<25} {qty:>2} {int(price):>6} {int(amt):>6}\n")
                p.set(bold=False)
                if len(name) > 24:
                    p.text(f"  {name[24:47]}\n")
                if item.get("note"):
                    p.text(f"  >> {item['note']}\n")

            # Totals
            p.text("=" * W + "\n")
            sub  = order_data.get("subtotal", 0)
            disc = order_data.get("discount", 0)
            svc  = order_data.get("service_charge", 0)
            tax  = order_data.get("tax", 0)
            grd  = order_data.get("grand_total", 0)
            pm   = order_data.get("payment_method", "")

            p.text(_row("Sub Total :", f"Rs.{int(sub):,}"))
            if disc and bill_cfg.get("show_discount"):
                p.text(_row("Discount  :", f"-Rs.{int(disc):,}"))
            if svc and bill_cfg.get("show_service_charge"):
                p.text(_row("Service   :", f"Rs.{int(svc):,}"))
            if tax and bill_cfg.get("show_tax"):
                p.text(_row("Tax/GST   :", f"Rs.{int(tax):,}"))

            # Grand Total — big
            p.text("=" * W + "\n")
            p.set(align="center", bold=True, double_height=True, double_width=True)
            p.text(f"Rs.{int(grd):,}\n")
            p.set(bold=False, double_height=False, double_width=False)
            p.set(align="center", bold=True)
            p.text("TOTAL AMOUNT\n")
            p.set(bold=False)

            # Payment method
            if pm and pm not in ("Pending", ""):
                p.text("-" * W + "\n")
                p.set(bold=True); p.text(_row("Payment   :", pm)); p.set(bold=False)

            p.text("=" * W + "\n")

            # Footer
            footer_msg = ri.get("footer", "Thank You! Visit Again")
            p.set(align="center", bold=True)
            p.text(f"{footer_msg}\n")
            p.set(bold=False)
            if bill_cfg.get("footer_extra"):
                p.text(f"{bill_cfg['footer_extra']}\n")
            p.text(f"Abyte POS | {datetime.now().strftime('%d-%m-%Y')}\n")
            p.text("\n\n")
            p.cut(); p.close()
            result[0], result[1] = True, "Printed Successfully"
        except ImportError:
            result[0], result[1] = False, "python-escpos not found"
        except Exception as e:
            result[0], result[1] = False, str(e)

    t = threading.Thread(target=_print, daemon=True)
    t.start(); t.join(timeout=PRINT_TIMEOUT)
    if t.is_alive():     return False, "Network printer timeout or not responding"
    if result[0] is None: return False, "Print state unknown"
    return result[0], result[1]


def print_http(order_data, config, is_kot=False):
    import requests
    try:
        server_url = config.get("server_url", "http://localhost:9100")
        data       = {**order_data, "print_type": "kot" if is_kot else "receipt"}
        r = requests.post(f"{server_url}/print", json=data,
                          headers={"Content-Type": "application/json"}, timeout=30)
        if r.status_code == 200:
            res = r.json()
            return (True, f"Print job sent: {res.get('job_id','N/A')}") if res.get("success") \
                   else (False, res.get("message", "Unknown error"))
        return False, f"Server returned status {r.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to print server at {config.get('server_url','')}."
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
        lp = os.path.abspath(restaurant_info["logo_path"])
        if os.path.exists(lp):
            logo_html = f'<div class="center"><img src="{Path(lp).as_uri()}" width="100"></div>'
    return f"""<html><head><style>
        body{{font-family:'Courier New',monospace;font-size:12px;}}
        h2{{text-align:center;margin:0;}} p{{margin:2px 0;}}
        .center{{text-align:center;}} .right{{text-align:right;}} .bold{{font-weight:bold;}}
        hr{{border-top:1px dashed #000;}}
        table{{width:100%;border-collapse:collapse;margin-top:10px;}}
        th{{border-bottom:1px dashed #000;text-align:left;}} td{{padding:2px 0;}}
    </style></head><body>
        {logo_html}
        <h2>{restaurant_info['name']}</h2>
        <p class="center">{restaurant_info['address']}</p>
        <p class="center">Tel: {restaurant_info['phone']}</p><br>
        <h3 class="center">{report_data.get('title','REPORT')}</h3>
        <p>Date: {report_data.get('date', datetime.now().strftime('%Y-%m-%d'))}</p>
        <p>Generated: {datetime.now().strftime('%H:%M:%S')}</p>
        <hr><pre>{report_data.get('content','')}</pre><hr>
        <p class="center">{restaurant_info.get('footer','*** END OF REPORT ***')}</p>
    </body></html>"""


def print_report_v2(report_data):
    try:
        ri       = get_restaurant_info()
        printers = get_printers_by_role("receipt")
        cfg      = printers[0] if printers else {}
        if cfg.get("type") == "network":
            from escpos.printer import Network
            ip   = cfg.get("ip")
            port = int(cfg.get("port", 9100))
            if not ip: return False, "IP Missing"
            p = Network(ip, port=port)
            p.set(align="center")
            if ri.get("print_logo") and ri.get("logo_path") and os.path.exists(ri["logo_path"]):
                p.image(ri["logo_path"])
            p.text(f"{ri['name']}\n{report_data.get('title','REPORT')}\n\n")
            p.set(align="left"); p.text(report_data.get("content", ""))
            p.cut(); p.close()
            return True, "Printed to Network Printer"
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        pn = cfg.get("usb_name")
        if pn: printer.setPrinterName(pn)
        doc = QTextDocument()
        doc.setHtml(generate_report_html(report_data, ri))
        doc.print(printer)
        return True, "Printed to System Printer"
    except Exception as e:
        print(f"Print Report Error: {e}")
        return False, str(e)


def print_dummy_receipt(report_text):
    print("Printing Report:\n", report_text)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    if not QPrinterInfo.availablePrinters():
        print("No printers available."); return
    doc = QTextDocument()
    doc.setPlainText(report_text)
    doc.print(printer)


# ══════════════════════════════════════════════════════════════════════════════
#  A4 PDF INVOICE (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════

def generate_pdf_invoice(order_data, restaurant_info=None):
    try:
        if not restaurant_info:
            restaurant_info = get_restaurant_info()
        logo_html = ""
        if restaurant_info.get("print_logo") and restaurant_info.get("logo_path"):
            lp = resolve_resource_path(restaurant_info["logo_path"])
            if os.path.exists(lp):
                logo_html = f'<img src="{Path(lp).as_uri()}" style="height:70px;width:auto;object-fit:contain;">'
        items_html = ""
        for i, item in enumerate(order_data.get("items", [])):
            note      = item.get("note", "")
            note_html = f'<div style="font-size:11px;color:#888;margin-top:3px;font-style:italic;">Note: {note}</div>' if note else ""
            row_bg    = "#FAFBFF" if i % 2 == 0 else "#FFFFFF"
            lt        = item["qty"] * item["price"]
            items_html += (
                f'<tr style="background:{row_bg};">'
                f'<td style="padding:12px 16px;font-size:13px;color:#1E2235;border-bottom:1px solid #EAECF4;">{item["name"]}{note_html}</td>'
                f'<td style="padding:12px 16px;font-size:13px;color:#6B7280;text-align:center;border-bottom:1px solid #EAECF4;">{item["qty"]}</td>'
                f'<td style="padding:12px 16px;font-size:13px;color:#6B7280;text-align:right;border-bottom:1px solid #EAECF4;">Rs. {item["price"]:.2f}</td>'
                f'<td style="padding:12px 16px;font-size:13px;font-weight:600;color:#1E2235;text-align:right;border-bottom:1px solid #EAECF4;">Rs. {lt:.2f}</td>'
                f'</tr>'
            )
        invoice_no = order_data.get("invoice_no", "N/A")
        token_no   = order_data.get("token_no",   "—")
        date_val   = order_data.get("completed_at") or order_data.get("created_at") or datetime.now()
        date_str   = date_val if isinstance(date_val, str) else date_val.strftime("%d %B %Y  •  %I:%M %p")

        def money_row(label, value, color="#4B5563"):
            return (
                f'<tr><td style="padding:7px 0;font-size:13px;color:#6B7280;">{label}</td>'
                f'<td style="padding:7px 0;font-size:13px;color:{color};text-align:right;font-weight:500;">Rs. {value:.2f}</td></tr>'
            )

        sub_row  = money_row("Subtotal", order_data.get("subtotal", 0))
        dv       = order_data.get("discount", 0)
        sv       = order_data.get("service_charge", 0)
        tv       = order_data.get("tax", 0)
        disc_row = (
            f'<tr><td style="padding:7px 0;font-size:13px;color:#EF4444;">Discount</td>'
            f'<td style="padding:7px 0;font-size:13px;color:#EF4444;text-align:right;font-weight:500;">− Rs. {dv:.2f}</td></tr>'
        ) if dv else ""
        svc_row  = money_row("Service Charge", sv) if sv else ""
        tax_row  = money_row("Tax (GST)", tv)       if tv else ""

        html_content = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>
            @page{{size:A4;margin:0;}} *{{margin:0;padding:0;box-sizing:border-box;}}
            body{{font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#1E2235;background:#fff;}}
            .page{{width:210mm;min-height:297mm;display:flex;flex-direction:row;}}
            .sidebar{{width:8px;background:linear-gradient(180deg,#4F46E5 0%,#7C3AED 100%);flex-shrink:0;}}
            .main{{flex:1;padding:32px 36px 36px 36px;}}
            .header{{display:table;width:100%;margin-bottom:32px;padding-bottom:24px;border-bottom:2px solid #EAECF4;}}
            .hl{{display:table-cell;vertical-align:top;width:55%;}}
            .hr{{display:table-cell;vertical-align:top;text-align:right;}}
            .rname{{font-size:22px;font-weight:800;color:#1E2235;letter-spacing:-0.5px;margin-bottom:4px;}}
            .rsub{{font-size:12px;color:#9CA3AF;line-height:1.6;}}
            .ibadge{{display:inline-block;background:#4F46E5;color:white;font-size:11px;font-weight:700;letter-spacing:2px;padding:4px 14px;border-radius:20px;text-transform:uppercase;margin-bottom:10px;}}
            .inum{{font-size:26px;font-weight:800;color:#1E2235;letter-spacing:-0.5px;}}
            .idate{{font-size:12px;color:#9CA3AF;margin-top:4px;}}
            .igrid{{display:table;width:100%;margin-bottom:28px;border:1.5px solid #EAECF4;border-radius:10px;overflow:hidden;}}
            .icell{{display:table-cell;padding:14px 20px;border-right:1.5px solid #EAECF4;width:33%;}}
            .icell:last-child{{border-right:none;}}
            .ilbl{{font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#9CA3AF;margin-bottom:4px;}}
            .ival{{font-size:14px;font-weight:700;color:#1E2235;}}
            .itbl{{width:100%;border-collapse:collapse;margin-bottom:24px;border:1.5px solid #EAECF4;border-radius:10px;overflow:hidden;}}
            .itbl thead tr{{background:#1E2235;}}
            .itbl thead th{{padding:13px 16px;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#A5B4FC;text-align:left;}}
            .itbl thead th:nth-child(2){{text-align:center;}}
            .itbl thead th:nth-child(3),.itbl thead th:nth-child(4){{text-align:right;}}
            .tw{{display:table;width:100%;}}
            .ts{{display:table-cell;width:55%;}}
            .tb{{display:table-cell;width:45%;vertical-align:top;}}
            .ti{{border:1.5px solid #EAECF4;border-radius:10px;overflow:hidden;}}
            .tr2{{padding:16px 20px 0 20px;}}
            .tr2 table{{width:100%;border-collapse:collapse;}}
            .gtr{{background:#4F46E5;padding:16px 20px;display:table;width:100%;margin-top:8px;}}
            .gl{{display:table-cell;font-size:13px;font-weight:800;color:white;letter-spacing:0.5px;text-transform:uppercase;}}
            .gv{{display:table-cell;font-size:18px;font-weight:800;color:white;text-align:right;}}
            .foot{{margin-top:40px;padding-top:20px;border-top:1.5px dashed #EAECF4;text-align:center;}}
            .fm{{font-size:14px;font-weight:700;color:#4F46E5;margin-bottom:6px;}}
            .fs{{font-size:11px;color:#C4C9D8;}}
        </style></head><body>
        <div class="page"><div class="sidebar"></div><div class="main">
            <div class="header">
                <div class="hl">
                    {logo_html}
                    <div class="rname" style="margin-top:{'10px' if logo_html else '0'};">{restaurant_info['name']}</div>
                    <div class="rsub">{restaurant_info['address']}<br>Tel: {restaurant_info['phone']}</div>
                </div>
                <div class="hr">
                    <div class="ibadge">Invoice</div>
                    <div class="inum">#{invoice_no}</div>
                    <div class="idate">{date_str}</div>
                </div>
            </div>
            <div class="igrid">
                <div class="icell"><div class="ilbl">Token No.</div><div class="ival">{token_no}</div></div>
                <div class="icell"><div class="ilbl">Table</div><div class="ival">{order_data.get('table_no','Takeaway')}</div></div>
                <div class="icell"><div class="ilbl">Customer</div><div class="ival">{order_data.get('customer_name','Guest')}</div></div>
            </div>
            <table class="itbl">
                <thead><tr>
                    <th style="width:50%;">Description</th><th style="width:10%;">Qty</th>
                    <th style="width:20%;">Unit Price</th><th style="width:20%;">Total</th>
                </tr></thead>
                <tbody>{items_html}</tbody>
            </table>
            <div class="tw"><div class="ts"></div><div class="tb">
                <div class="ti">
                    <div class="tr2"><table>{sub_row}{disc_row}{svc_row}{tax_row}</table></div>
                    <div class="gtr"><div class="gl">Grand Total</div><div class="gv">Rs. {order_data.get('grand_total',0):.2f}</div></div>
                </div>
            </div></div>
            <div class="foot">
                <div class="fm">{restaurant_info.get('footer','Thank you for your visit!')}</div>
                <div class="fs">This is a computer-generated invoice — no signature required.</div>
            </div>
        </div></div>
        </body></html>"""

        invoice_dir = os.path.join(os.getcwd(), "invoices")
        os.makedirs(invoice_dir, exist_ok=True)
        filename  = "".join(c for c in f"Invoice_{order_data.get('invoice_no','Unknown')}.pdf" if c.isalnum() or c in " ._-")
        file_path = os.path.join(invoice_dir, filename)
        printer   = QPrinter(QPrinter.PrinterMode.HighResolution)
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