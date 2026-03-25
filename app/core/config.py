import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env so os.environ has WhatsApp credentials
if not getattr(sys, 'frozen', False):
    _root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(_root / ".env")

# Base directory
if getattr(sys, 'frozen', False):
    # Executable mode
    CONFIG_DIR = Path(sys.executable).parent
    
    if hasattr(sys, '_MEIPASS'):
        # One-file mode: resources are in temp dir
        RESOURCE_DIR = Path(sys._MEIPASS)
    else:
        # One-dir mode: resources are in _internal or same dir
        RESOURCE_DIR = CONFIG_DIR / "_internal" if (CONFIG_DIR / "_internal").exists() else CONFIG_DIR
else:
    # Dev mode
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    CONFIG_DIR = ROOT_DIR
    RESOURCE_DIR = ROOT_DIR

CONFIG_FILE = CONFIG_DIR / "config.json"

def resolve_resource_path(path_str):
    """
    Resolve a resource path.
    If absolute, return as is.
    If relative, return relative to RESOURCE_DIR.
    """
    if not path_str:
        return path_str
    
    path = Path(path_str)
    if path.is_absolute():
        return str(path)
    
    return str(RESOURCE_DIR / path)

DEFAULT_CONFIG = {
    "printer_name": "",
    "paper_size": "80mm",
    "print_logo": True,
    "logo_path": "app/resources/POS.png",
    "theme": "light",
    "currency": "PKR",
    "tax_rate": 0.0,
    "service_charge": 0.0,
    "admin_pin": "1234",
    # Per-category tax & service charge
    "category_charges": {
        "Dine In":  {"tax_rate": 0.0, "service_charge": 0.0},
        "Takeaway": {"tax_rate": 0.0, "service_charge": 0.0},
        "Delivery": {"tax_rate": 0.0, "service_charge": 0.0},
    },
    # Tax per payment method (Cash / Card)
    "payment_tax": {
        "Cash": 0.0,
        "Card": 0.0,
    },
    # --- WhatsApp API Configuration (Green-API) ---
    # Credentials are loaded from .env file (WHATSAPP_INSTANCE_ID, WHATSAPP_API_TOKEN)
    "whatsapp_api_provider": "green-api",
    "whatsapp_instance_id": os.environ.get("WHATSAPP_INSTANCE_ID", ""),
    "whatsapp_api_token": os.environ.get("WHATSAPP_API_TOKEN", "")
}

def load_config():
    """
    Load configuration from config.json or return defaults.
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**DEFAULT_CONFIG, **config}
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    """
    Save configuration to config.json.
    """
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_setting(key, default=None):
    """
    Get a specific setting value.
    """
    config = load_config()
    return config.get(key, default)
