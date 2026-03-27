"""
Enhanced Login Window - Modern, Professional Design
"""

import sys
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QApplication, QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy,
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QThread, QTimer, QPropertyAnimation,
    QEasingCurve, QPoint,
)
from PyQt6.QtGui import QPixmap, QColor
import qtawesome as qta
from datetime import datetime
from PyQt6.QtCore import QSettings
from backend.services.user_service import AccountLockedError, AccountInactiveError, InvalidCredentialsError

from backend.core.database import users_col
from backend.services.user_service import authenticate_user


class LoginWorker(QThread):
    """Background thread for authentication"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        try:
            user = authenticate_user(self.username, self.password)
            self.finished.emit(user)
        except (AccountLockedError, AccountInactiveError, InvalidCredentialsError) as e:
            self.error.emit(str(e))
        except Exception:
            self.error.emit("Connection error. Check if the database is running.")


class LoginWindow(QWidget):
    """Modern Login Window with enhanced UI/UX"""
    login_success = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Abyte POS - Login")
        self.resize(1100, 700)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.password_visible = False
        self._drag_pos = None

        self._setup_ui()
        self._load_stylesheet()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Container with shadow
        container = QFrame()
        container.setObjectName("login-container")
        container_shadow = QGraphicsDropShadowEffect()
        container_shadow.setBlurRadius(60)
        container_shadow.setXOffset(0)
        container_shadow.setYOffset(15)
        container_shadow.setColor(QColor(0, 0, 0, 80))
        container.setGraphicsEffect(container_shadow)

        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # ══════════════════════════════════════════════════════════════════════
        #  LEFT PANEL - Branding
        # ══════════════════════════════════════════════════════════════════════
        left_panel = QFrame()
        left_panel.setObjectName("login-left-panel")
        left_panel.setMinimumWidth(420)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(50, 40, 50, 40)
        left_layout.setSpacing(0)

        # Window controls (minimize, close)
        controls_bar = QHBoxLayout()
        controls_bar.setSpacing(8)

        btn_minimize = QPushButton("─")
        btn_minimize.setObjectName("window-btn-minimize")
        btn_minimize.setFixedSize(36, 36)
        btn_minimize.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_minimize.clicked.connect(self.showMinimized)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("window-btn-close")
        btn_close.setFixedSize(36, 36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)

        controls_bar.addWidget(btn_minimize)
        controls_bar.addWidget(btn_close)
        controls_bar.addStretch()
        left_layout.addLayout(controls_bar)

        left_layout.addStretch()

        # Logo
        logo_container = QFrame()
        logo_container.setObjectName("logo-container")
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setObjectName("login-logo")
        from backend.core.config import get_setting, resolve_resource_path
        logo_path = resolve_resource_path(get_setting("logo_path", "frontend/resources/POS.png"))
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(
                140, 140,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_lbl.setPixmap(scaled)
        else:
            icon_lbl.setPixmap(qta.icon('fa5s.utensils', color='white').pixmap(100, 100))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(icon_lbl)
        left_layout.addWidget(logo_container)

        left_layout.addSpacing(30)

        # Restaurant name
        restaurant_name = get_setting("restaurant_name", "KHAYYAM")
        title_lbl = QLabel(restaurant_name.upper())
        title_lbl.setObjectName("login-brand-title")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title_lbl)

        # Tagline
        tagline_lbl = QLabel("Food Court & Restaurant")
        tagline_lbl.setObjectName("login-brand-tagline")
        tagline_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(tagline_lbl)

        left_layout.addSpacing(40)

        # Features list
        features = [
            ("fa5s.bolt", "Fast & Efficient Billing"),
            ("fa5s.chart-line", "Real-time Analytics"),
            ("fa5s.users", "Multi-user Support"),
            ("fa5s.cloud", "Cloud Sync Ready"),
        ]
        for icon_name, text in features:
            row = QHBoxLayout()
            row.setSpacing(12)
            icon = QLabel()
            icon.setPixmap(qta.icon(icon_name, color='#a7f3d0').pixmap(18, 18))
            icon.setFixedWidth(24)
            lbl = QLabel(text)
            lbl.setObjectName("login-feature-text")
            row.addStretch()
            row.addWidget(icon)
            row.addWidget(lbl)
            row.addStretch()
            left_layout.addLayout(row)
            left_layout.addSpacing(8)

        left_layout.addStretch()

        # Version & Copyright
        version_lbl = QLabel("v2.0.0  •  2024")
        version_lbl.setObjectName("login-version")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(version_lbl)

        # ══════════════════════════════════════════════════════════════════════
        #  RIGHT PANEL - Form
        # ══════════════════════════════════════════════════════════════════════
        right_panel = QFrame()
        right_panel.setObjectName("login-right-panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(60, 50, 60, 50)
        right_layout.setSpacing(0)

        right_layout.addStretch()

        # Time-based greeting
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good Morning"
            greeting_icon = "fa5s.sun"
        elif 12 <= hour < 17:
            greeting = "Good Afternoon"
            greeting_icon = "fa5s.cloud-sun"
        elif 17 <= hour < 21:
            greeting = "Good Evening"
            greeting_icon = "fa5s.cloud-moon"
        else:
            greeting = "Welcome"
            greeting_icon = "fa5s.moon"

        greeting_row = QHBoxLayout()
        greeting_row.setSpacing(10)
        greeting_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        g_icon = QLabel()
        g_icon.setPixmap(qta.icon(greeting_icon, color='#f59e0b').pixmap(28, 28))
        g_text = QLabel(greeting)
        g_text.setObjectName("login-greeting")
        greeting_row.addWidget(g_icon)
        greeting_row.addWidget(g_text)
        right_layout.addLayout(greeting_row)

        right_layout.addSpacing(8)

        # Welcome text
        welcome_lbl = QLabel("Sign in to continue")
        welcome_lbl.setObjectName("login-welcome-sub")
        welcome_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(welcome_lbl)

        right_layout.addSpacing(40)

        # Form
        form_frame = QFrame()
        form_frame.setObjectName("login-form-frame")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(20)

        # Username field
        user_label = QLabel("Username")
        user_label.setObjectName("login-field-label")
        form_layout.addWidget(user_label)

        user_container = QFrame()
        user_container.setObjectName("login-input-container")
        user_inner = QHBoxLayout(user_container)
        user_inner.setContentsMargins(16, 0, 16, 0)
        user_inner.setSpacing(12)

        user_icon = QLabel()
        user_icon.setPixmap(qta.icon('fa5s.user', color='#94a3b8').pixmap(20, 20))
        self.user_input = QLineEdit()
        self.user_input.setObjectName("login-input")
        self.user_input.setPlaceholderText("Enter your username")
        self.user_input.returnPressed.connect(lambda: self.pass_input.setFocus())

        user_inner.addWidget(user_icon)
        user_inner.addWidget(self.user_input)
        form_layout.addWidget(user_container)

        # Password field
        pass_label = QLabel("Password")
        pass_label.setObjectName("login-field-label")
        form_layout.addWidget(pass_label)

        pass_container = QFrame()
        pass_container.setObjectName("login-input-container")
        pass_inner = QHBoxLayout(pass_container)
        pass_inner.setContentsMargins(16, 0, 16, 0)
        pass_inner.setSpacing(12)

        pass_icon = QLabel()
        pass_icon.setPixmap(qta.icon('fa5s.lock', color='#94a3b8').pixmap(20, 20))
        self.pass_input = QLineEdit()
        self.pass_input.setObjectName("login-input")
        self.pass_input.setPlaceholderText("Enter your password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.returnPressed.connect(self.do_login)

        self.toggle_pass_btn = QPushButton()
        self.toggle_pass_btn.setObjectName("toggle-pass-btn")
        self.toggle_pass_btn.setIcon(qta.icon('fa5s.eye', color='#94a3b8'))
        self.toggle_pass_btn.setFixedSize(32, 32)
        self.toggle_pass_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_pass_btn.clicked.connect(self.toggle_password_visibility)

        pass_inner.addWidget(pass_icon)
        pass_inner.addWidget(self.pass_input)
        pass_inner.addWidget(self.toggle_pass_btn)
        form_layout.addWidget(pass_container)

        # Remember me row
        options_row = QHBoxLayout()
        self.remember_chk = QCheckBox("Remember me")
        self.remember_chk.setObjectName("login-remember")
        options_row.addWidget(self.remember_chk)
        options_row.addStretch()
        form_layout.addLayout(options_row)

        right_layout.addWidget(form_frame)

        right_layout.addSpacing(10)

        # Error message
        self.error_frame = QFrame()
        self.error_frame.setObjectName("login-error-frame")
        self.error_frame.hide()
        error_inner = QHBoxLayout(self.error_frame)
        error_inner.setContentsMargins(16, 12, 16, 12)
        error_inner.setSpacing(10)

        self.error_icon = QLabel()
        self.error_icon.setPixmap(qta.icon('fa5s.exclamation-circle', color='#ef4444').pixmap(18, 18))
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("login-error-text")
        self.error_lbl.setWordWrap(True)
        error_inner.addWidget(self.error_icon)
        error_inner.addWidget(self.error_lbl, stretch=1)
        right_layout.addWidget(self.error_frame)

        right_layout.addSpacing(30)

        # Login button
        self.login_btn = QPushButton("SIGN IN")
        self.login_btn.setObjectName("login-btn")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setFixedHeight(54)
        self.login_btn.clicked.connect(self.do_login)
        right_layout.addWidget(self.login_btn)

        right_layout.addSpacing(20)

        # Keyboard shortcut hint
        hint_lbl = QLabel("Press Enter to sign in")
        hint_lbl.setObjectName("login-hint")
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(hint_lbl)

        right_layout.addStretch()

        # Current time display
        self.time_lbl = QLabel()
        self.time_lbl.setObjectName("login-time")
        self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_time()
        right_layout.addWidget(self.time_lbl)

        # Time update timer
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self._update_time)
        self.time_timer.start(1000)

        container_layout.addWidget(left_panel, stretch=4)
        container_layout.addWidget(right_panel, stretch=5)

        main_layout.addStretch()
        main_layout.addWidget(container)
        main_layout.addStretch()

        # Restore remembered username
        _s = QSettings("AbytePos", "Login")
        remembered = _s.value("remembered_username", "")
        if remembered:
            self.user_input.setText(remembered)
            self.remember_chk.setChecked(True)
            self.pass_input.setFocus()
        else:
            self.user_input.setFocus()

    def _load_stylesheet(self):
        """Load the enhanced login stylesheet"""
        qss = """
        /* ═══════════════════════════════════════════════════════════════════════
           ENHANCED LOGIN STYLESHEET
           ═══════════════════════════════════════════════════════════════════════ */

        QFrame#login-container {
            background: transparent;
        }

        /* ─── Left Panel (Branding) ─────────────────────────────────────────────── */
        QFrame#login-left-panel {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #064e3b, stop:0.5 #059669, stop:1 #047857);
            border-top-left-radius: 24px;
            border-bottom-left-radius: 24px;
        }

        QFrame#logo-container {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 80px;
            padding: 20px;
            max-width: 180px;
            max-height: 180px;
        }

        QLabel#login-brand-title {
            color: white;
            font-size: 38px;
            font-weight: 900;
            letter-spacing: 3px;
        }

        QLabel#login-brand-tagline {
            color: #a7f3d0;
            font-size: 15px;
            font-weight: 500;
            letter-spacing: 1px;
        }

        QLabel#login-feature-text {
            color: rgba(255, 255, 255, 0.85);
            font-size: 13px;
            font-weight: 500;
        }

        QLabel#login-version {
            color: rgba(255, 255, 255, 0.5);
            font-size: 11px;
        }

        /* Window control buttons */
        QPushButton#window-btn-minimize, QPushButton#window-btn-close {
            background: rgba(255, 255, 255, 0.15);
            border: none;
            border-radius: 18px;
            color: white;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton#window-btn-minimize:hover {
            background: rgba(255, 255, 255, 0.25);
        }
        QPushButton#window-btn-close:hover {
            background: #ef4444;
        }

        /* ─── Right Panel (Form) ────────────────────────────────────────────────── */
        QFrame#login-right-panel {
            background: #ffffff;
            border-top-right-radius: 24px;
            border-bottom-right-radius: 24px;
        }

        QLabel#login-greeting {
            color: #1e293b;
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }

        QLabel#login-welcome-sub {
            color: #64748b;
            font-size: 15px;
        }

        QLabel#login-field-label {
            color: #475569;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 6px;
        }

        /* Input containers */
        QFrame#login-input-container {
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            min-height: 52px;
        }
        QFrame#login-input-container:focus-within {
            border-color: #059669;
            background: #ffffff;
        }

        QLineEdit#login-input {
            background: transparent;
            border: none;
            color: #1e293b;
            font-size: 14px;
            padding: 0;
            selection-background-color: #d1fae5;
        }
        QLineEdit#login-input::placeholder {
            color: #94a3b8;
        }

        QPushButton#toggle-pass-btn {
            background: transparent;
            border: none;
            border-radius: 16px;
        }
        QPushButton#toggle-pass-btn:hover {
            background: #f1f5f9;
        }

        /* Remember checkbox */
        QCheckBox#login-remember {
            color: #64748b;
            font-size: 13px;
            font-weight: 500;
            spacing: 8px;
        }
        QCheckBox#login-remember::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            background: #f8fafc;
        }
        QCheckBox#login-remember::indicator:hover {
            border-color: #059669;
        }
        QCheckBox#login-remember::indicator:checked {
            background: #059669;
            border-color: #059669;
            image: none;
        }

        /* Error frame */
        QFrame#login-error-frame {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 10px;
        }
        QLabel#login-error-text {
            color: #dc2626;
            font-size: 13px;
            font-weight: 500;
        }

        /* Login button */
        QPushButton#login-btn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #059669, stop:1 #10b981);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 1px;
        }
        QPushButton#login-btn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #047857, stop:1 #059669);
        }
        QPushButton#login-btn:pressed {
            background: #064e3b;
        }
        QPushButton#login-btn:disabled {
            background: #94a3b8;
        }

        QLabel#login-hint {
            color: #94a3b8;
            font-size: 12px;
        }

        QLabel#login-time {
            color: #cbd5e1;
            font-size: 12px;
            font-weight: 500;
        }
        """
        self.setStyleSheet(qss)

    def _update_time(self):
        """Update the time display"""
        now = datetime.now()
        self.time_lbl.setText(now.strftime("%A, %B %d  •  %I:%M %p"))

    def toggle_password_visibility(self):
        """Toggle password field visibility"""
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_pass_btn.setIcon(qta.icon('fa5s.eye-slash', color='#059669'))
        else:
            self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_pass_btn.setIcon(qta.icon('fa5s.eye', color='#94a3b8'))

    def _shake_animation(self):
        """Shake animation for error feedback"""
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(400)
        self.anim.setLoopCount(1)
        pos = self.pos()
        self.anim.setKeyValueAt(0, pos)
        self.anim.setKeyValueAt(0.1, pos + QPoint(10, 0))
        self.anim.setKeyValueAt(0.2, pos + QPoint(-10, 0))
        self.anim.setKeyValueAt(0.3, pos + QPoint(8, 0))
        self.anim.setKeyValueAt(0.4, pos + QPoint(-8, 0))
        self.anim.setKeyValueAt(0.5, pos + QPoint(5, 0))
        self.anim.setKeyValueAt(0.6, pos + QPoint(-5, 0))
        self.anim.setKeyValueAt(0.7, pos + QPoint(3, 0))
        self.anim.setKeyValueAt(0.8, pos + QPoint(-3, 0))
        self.anim.setKeyValueAt(1, pos)
        self.anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        self.anim.start()

    def _show_error(self, message):
        """Show error message with animation"""
        self.error_lbl.setText(message)
        self.error_frame.show()
        self._shake_animation()

    def _hide_error(self):
        """Hide error message"""
        self.error_frame.hide()

    def do_login(self):
        """Handle login attempt"""
        user = self.user_input.text().strip()
        pwd = self.pass_input.text().strip()

        if not user or not pwd:
            self._show_error("Please enter both username and password")
            return

        self._hide_error()
        self.login_btn.setText("Signing in...")
        self.login_btn.setEnabled(False)
        self.user_input.setEnabled(False)
        self.pass_input.setEnabled(False)
        self.remember_chk.setEnabled(False)

        self.worker = LoginWorker(user, pwd)
        self.worker.finished.connect(self.on_login_success)
        self.worker.error.connect(self.on_login_error)
        self.worker.start()

    def on_login_success(self, user):
        """Handle successful login"""
        self.login_btn.setText("Success!")
        self.login_btn.setStyleSheet("""
            QPushButton#login-btn {
                background: #10b981;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 700;
            }
        """)
        QTimer.singleShot(500, lambda: self._complete_login(user))

    def _complete_login(self, user):
        """Complete login and emit signal"""
        _s = QSettings("AbytePos", "Login")
        if self.remember_chk.isChecked():
            _s.setValue("remembered_username", self.user_input.text().strip())
        else:
            _s.remove("remembered_username")
        self.login_success.emit(user)
        self.close()

    def on_login_error(self, msg):
        """Handle login error"""
        self.login_btn.setText("SIGN IN")
        self.login_btn.setEnabled(True)
        self.user_input.setEnabled(True)
        self.pass_input.setEnabled(True)
        self.remember_chk.setEnabled(True)
        self._show_error(msg)
        self.pass_input.setFocus()
        self.pass_input.selectAll()

    # ── Window Dragging ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = LoginWindow()
    w.show()
    sys.exit(app.exec())
