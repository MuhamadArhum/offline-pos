import os
import platform
import subprocess
import urllib.parse
import webbrowser
from typing import Tuple, Optional

from backend.core.config import get_setting
from backend.core.logger import get_logger
from backend.utils.print_utils import generate_pdf_invoice


logger = get_logger()


def _format_receipt_message(order: dict) -> str:
    lines = []
    title = f"Invoice {order.get('invoice_no', '')}"
    restaurant_name = get_setting("restaurant_name", "") or "Restaurant"
    lines.append(f"{restaurant_name} - {title}".strip())
    token = order.get("token_no")
    if token:
        lines.append(f"Token: {token}")
    lines.append("")
    for item in order.get("items", []):
        name = str(item.get("name", ""))
        qty = float(item.get("qty", 0) or 0)
        price = float(item.get("price", 0) or 0)
        total = qty * price
        lines.append(f"{qty:g} x {name} = {total:,.2f}")
    lines.append("")
    grand_total = float(order.get("grand_total", 0) or 0)
    lines.append(f"Total: {grand_total:,.2f}")
    customer = order.get("customer_name") or order.get("customer_phone")
    if customer:
        lines.append(f"Customer: {customer}")
    return "\n".join(lines)


def _normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    phone = phone.strip()
    if phone.startswith("+"):
        return phone
    return "+92" + phone.lstrip("0")


def _open_file_location(path: str) -> None:
    if not path or not os.path.exists(path):
        return
    system = platform.system()
    if system == "Windows":
        subprocess.Popen(["explorer", "/select,", path])
    elif system == "Darwin":
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(path)])


def _send_via_browser(phone: str, message: str, pdf_path: Optional[str] = None) -> Tuple[bool, str]:
    try:
        encoded_msg = urllib.parse.quote(message)
        encoded_phone = urllib.parse.quote(phone)
        url = f"https://web.whatsapp.com/send?phone={encoded_phone}&text={encoded_msg}"
        webbrowser.open(url)
        if pdf_path:
            _open_file_location(pdf_path)
        return True, "WhatsApp Web opened"
    except Exception as e:
        logger.error(f"WhatsApp browser error: {e}")
        return False, str(e)


def _send_via_green_api(phone: str, message: str, order: dict) -> Tuple[bool, str]:
    provider = get_setting("whatsapp_api_provider", "none")
    if provider != "green-api":
        return False, "WhatsApp API not enabled"
    instance_id = get_setting("whatsapp_instance_id", "")
    api_token = get_setting("whatsapp_api_token", "")
    if not instance_id or not api_token:
        return False, "WhatsApp API credentials missing"
    pdf_path = generate_pdf_invoice(order)
    if not pdf_path or not os.path.exists(pdf_path):
        return False, "PDF generation failed"
    try:
        import requests
    except Exception as e:
        logger.error(f"Requests library missing: {e}")
        return False, "Requests library not installed"
    chat_id = f"{phone.replace('+', '')}@c.us"
    prefix = instance_id[:4]
    host = f"https://{prefix}.api.greenapi.com"
    url = f"{host}/waInstance{instance_id}/sendFileByUpload/{api_token}"
    files = [
        (
            "file",
            (os.path.basename(pdf_path), open(pdf_path, "rb"), "application/pdf"),
        )
    ]
    data = {
        "chatId": chat_id,
        "fileName": os.path.basename(pdf_path),
        "caption": message,
    }
    try:
        resp = requests.post(url, data=data, files=files, timeout=20)
        if resp.status_code == 200:
            return True, "WhatsApp PDF sent via API"
        logger.error(f"Green API error {resp.status_code}: {resp.text}")
        return False, f"WhatsApp API error {resp.status_code}"
    except Exception as e:
        logger.error(f"Green API exception: {e}")
        return False, str(e)


def send_receipt_via_whatsapp(phone_no: str, order: dict, auto_send: bool = True) -> Tuple[bool, str]:
    try:
        phone = _normalize_phone(phone_no)
        if not phone:
            return False, "Phone number missing"
        message = _format_receipt_message(order)
        use_api = get_setting("whatsapp_api_provider", "none") == "green-api"
        if use_api:
            ok, info = _send_via_green_api(phone, message, order)
            if ok:
                return ok, info
        pdf_path = generate_pdf_invoice(order)
        return _send_via_browser(phone, message, pdf_path)
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return False, str(e)

