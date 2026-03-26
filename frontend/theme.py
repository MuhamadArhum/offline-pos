import os

class Theme:
    # Color Palette - Professional Green Theme
    PRIMARY         = "#059669"   # Emerald 600
    PRIMARY_HOVER   = "#047857"   # Emerald 700
    PRIMARY_DARK    = "#064e3b"   # Emerald 900
    PRIMARY_LIGHT   = "#34d399"   # Emerald 400
    PRIMARY_SUBTLE  = "#ECFDF5"   # Emerald 50

    # Navbar (Dark)
    NAVBAR_BG       = "#0F172A"   # Slate 950
    NAVBAR_SURFACE  = "#1E293B"   # Slate 800
    NAVBAR_BORDER   = "#334155"   # Slate 700
    NAVBAR_TEXT     = "#CBD5E1"   # Slate 300
    NAVBAR_TEXT_ACTIVE = "#FFFFFF"

    # App Surfaces
    BACKGROUND      = "#F1F5F9"   # Slate 100
    SURFACE         = "#FFFFFF"
    SURFACE_RAISED  = "#FAFBFC"

    # Text
    TEXT_PRIMARY    = "#0F172A"   # Slate 950
    TEXT_SECONDARY  = "#475569"   # Slate 600
    TEXT_HINT       = "#94A3B8"   # Slate 400

    # Borders
    BORDER          = "#E2E8F0"   # Slate 200
    BORDER_LIGHT    = "#F1F5F9"   # Slate 100
    DIVIDER         = "#F1F5F9"

    # Status
    SUCCESS         = "#22C55E"
    ERROR           = "#EF4444"
    WARNING         = "#F59E0B"
    INFO            = "#0EA5E9"

    # Legacy aliases (keep compatibility)
    EMERALD         = PRIMARY
    TEAL            = "#14b8a6"
    LIME            = "#84cc16"
    GREEN           = SUCCESS
    SECONDARY       = TEAL
    SECONDARY_LIGHT = "#5eead4"
    SECONDARY_DARK  = "#0f766e"
    ACCENT          = LIME

    @staticmethod
    def get_stylesheet():
        """Loads and concatenates all QSS stylesheets from app/resources/styles."""
        import sys
        if getattr(sys, 'frozen', False):
            # PyInstaller frozen mode
            base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            styles_dir = os.path.join(base, "frontend", "resources", "styles")
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))  # app/ui
            project_root = os.path.dirname(os.path.dirname(current_dir))  # RESTAURANT-POS
            styles_dir = os.path.join(project_root, "frontend", "resources", "styles")
        
        stylesheet = ""
        
        # 1. Load Base Styles
        base_path = os.path.join(styles_dir, "base.qss")
        if os.path.exists(base_path):
            with open(base_path, "r", encoding="utf-8") as f:
                stylesheet += f.read() + "\n"
                
        # 2. Load Modules recursively
        modules_dir = os.path.join(styles_dir, "modules")
        if os.path.exists(modules_dir):
            for filename in os.listdir(modules_dir):
                if filename.endswith(".qss"):
                    file_path = os.path.join(modules_dir, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            stylesheet += f"\n/* MODULE: {filename} */\n"
                            stylesheet += f.read() + "\n"
                    except Exception as e:
                        print(f"[WARN] Failed to load {filename}: {e}")
                        
        return stylesheet

class DarkTheme:
    """
    Future Dark Theme Palette 🌙
    """
    BACKGROUND = "#0f172a"       # Slate 900
    SURFACE = "#1e293b"          # Slate 800
    
    TEXT_PRIMARY = "#f8fafc"     # Slate 50
    TEXT_SECONDARY = "#94a3b8"   # Slate 400
    
    BORDER = "#334155"           # Slate 700
    DIVIDER = "#1e293b"          # Slate 800
    
    PRIMARY = "#10b981"          # Emerald 500 (Brighter for dark mode)

    @staticmethod
    def get_stylesheet():
        """
        To be implemented: Dynamic QSS generation for Dark Mode.
        Currently returns the default (Light) stylesheet.
        """
        return Theme.get_stylesheet()
