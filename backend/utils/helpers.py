from PyQt6.QtWidgets import QPushButton
from frontend.theme import Theme

def get_color(name: str) -> str:
    n = (name or "").lower()
    if n in ("bg", "background"):
        return Theme.BACKGROUND
    if n in ("surface", "card"):
        return Theme.SURFACE
    if n in ("text", "text_primary"):
        return Theme.TEXT_PRIMARY
    if n in ("text_secondary", "muted"):
        return Theme.TEXT_SECONDARY
    if n in ("primary",):
        return Theme.PRIMARY
    if n in ("success",):
        return Theme.SUCCESS
    if n in ("warning", "amber"):
        return Theme.WARNING
    if n in ("danger", "error"):
        return Theme.ERROR
    if n in ("info",):
        return Theme.INFO
    if n in ("border",):
        return Theme.BORDER
    if n in ("divider",):
        return Theme.DIVIDER
    return Theme.TEXT_PRIMARY

def create_button(text: str, kind: str = "primary") -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(36)
    k = (kind or "").lower()
    if k in ("add", "save", "primary", "ok"):
        btn.setProperty("class", "Primary")
    elif k in ("cancel", "secondary"):
        btn.setProperty("class", "Secondary")
    elif k in ("delete", "danger", "remove"):
        btn.setProperty("class", "Danger")
    else:
        # Default to Secondary for neutral actions
        btn.setProperty("class", "Secondary")
    return btn
