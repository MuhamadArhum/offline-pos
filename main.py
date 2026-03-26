import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from frontend.windows.login_window import LoginWindow
from frontend.windows.main_window import MainWindow
from backend.core.config import load_config, resolve_resource_path
from frontend.theme import Theme

def main():
    # 1. Setup Application
    app = QApplication(sys.argv)
    app.setApplicationName("Abyte POS")
    app.setOrganizationName("Abyte")

    # 2. Load Configuration & Styles
    config = load_config()

    # Set App Icon
    icon_path = resolve_resource_path("frontend/resources/POS.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Apply Stylesheet
    stylesheet = Theme.get_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # 3. Show Login Window
    login_window = LoginWindow()

    # Slot to handle successful login
    def on_login_success(user):
        # Create and show Dashboard
        main_window = MainWindow(user)
        main_window.show()

        # Keep reference to avoid garbage collection
        app._main_window = main_window

    login_window.login_success.connect(on_login_success)
    login_window.show()

    # 4. Run Event Loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
