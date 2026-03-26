from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QLabel, QPushButton, QGridLayout, QScrollArea,
                             QTableWidget, QHeaderView, QMessageBox, QFileDialog,
                             QProgressBar, QTableWidgetItem, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette, QBrush, QLinearGradient, QPainter
import qtawesome as qta
from datetime import datetime
from backend.services.inventory_service import get_inventory, low_stock_items
from backend.services.report_service import generate_purchase_order, get_item_sales_report
from backend.core.database import orders_col
from frontend.shared_ui import C
from frontend.theme import Theme

# ═════════════════════════════════════════════════════════════════════════
#  ENHANCED DASHBOARD UI - Professional Design
# ═════════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════════
#  PROFESSIONAL CARD STYLE - Enhanced with subtle shadow effect
# ═════════════════════════════════════════════════════════════════════════
def _card(elevated=False):
    from PyQt6.QtWidgets import QGraphicsDropShadowEffect
    from PyQt6.QtGui import QColor as _QColor
    c = QFrame()
    c.setStyleSheet(f"""
        QFrame {{
            background: {C['surface']};
            border: 1px solid #E8ECF0;
            border-radius: 16px;
        }}
    """)
    if elevated:
        shadow = QGraphicsDropShadowEffect(c)
        shadow.setBlurRadius(20)
        shadow.setColor(_QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        c.setGraphicsEffect(shadow)
    return c

# ═════════════════════════════════════════════════════════════════════════
#  IMPROVED DIVIDER - Thinner, more subtle
# ═════════════════════════════════════════════════════════════════════════
def _divider():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"""
        background: linear-gradient(90deg, transparent, #E8ECF0 20%, #E8ECF0 80%, transparent);
        border: none;
    """)
    return line

# ═════════════════════════════════════════════════════════════════════════
#  MODERN SECTION HEADER - With better typography
# ═════════════════════════════════════════════════════════════════════════
def _section_header(title: str, right_widget=None, icon=None):
    row = QHBoxLayout()
    row.setSpacing(10)
    
    # Add icon if provided
    if icon:
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon, color=C['primary']).pixmap(18, 18))
        icon_lbl.setStyleSheet("background: transparent;")
        row.addWidget(icon_lbl)
    
    lbl = QLabel(title)
    lbl.setStyleSheet(f"""
        font-size: 15px; 
        font-weight: 700; 
        color: {C['text_primary']};
        letter-spacing: -0.2px;
    """)
    row.addWidget(lbl)
    row.addStretch()
    if right_widget:
        row.addWidget(right_widget)
    return row

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        
        # Root layout — zero margins so scroll fills the whole tab
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scroll area ──────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {C['bg']}; border: none;")
        root.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background: {C['bg']};")
        scroll.setWidget(content)

        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(32, 24, 32, 24)  # Professional margins
        self.content_layout.setSpacing(24)  # Consistent spacing

        # ── Sections in order ────────────────────────────────────────────────
        self._build_header()          # 1. Page header + actions
        self._build_stats_row()       # 2. KPI cards
        self._build_targets_row()     # 3. Monthly targets (full width)
        self._build_main_content()    # 4. Orders table + right column
        
        # Load live data
        QTimer.singleShot(100, self.refresh_data)

    # ═════════════════════════════════════════════════════════════════════════
    #  1. HEADER - Professional look with modern buttons
    # ═════════════════════════════════════════════════════════════════════════
    def _build_header(self):
        row = QHBoxLayout()
        row.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(4)

        title = QLabel("Dashboard Overview")
        title.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {C['text_primary']};
            letter-spacing: -0.5px;
        """)

        # Breadcrumb with icon
        breadcrumb_row = QHBoxLayout()
        breadcrumb_row.setSpacing(6)
        
        home_icon = QLabel()
        home_icon.setPixmap(qta.icon("fa5s.home", color=C['text_sec']).pixmap(12, 12))
        home_icon.setStyleSheet("background: transparent;")
        
        breadcrumb = QLabel("Home  ›  Dashboard")
        breadcrumb.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {C['text_sec']};")
        
        breadcrumb_row.addWidget(home_icon)
        breadcrumb_row.addWidget(breadcrumb)
        breadcrumb_row.addStretch()

        left.addWidget(title)
        left.addLayout(breadcrumb_row)

        row.addLayout(left)
        row.addStretch()

        # Modernized buttons with icons
        refresh_btn = QPushButton(" Refresh")
        refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color=C['text_sec']))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setMinimumHeight(40)
        refresh_btn.setMaximumHeight(40)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface']}; 
                border: 1px solid #E8ECF0; 
                border-radius: 10px; 
                color: {C['text_sec']}; 
                font-weight: 600; 
                padding: 0 18px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: #F8FAFC; 
                color: {C['text_primary']}; 
                border-color: #CBD5E1;
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_data)

        export_btn = QPushButton(" Export Report")
        export_btn.setIcon(qta.icon("fa5s.file-export", color="white"))
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setMinimumHeight(40)
        export_btn.setMaximumHeight(40)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['primary']}; 
                border: none; 
                border-radius: 10px; 
                color: white; 
                font-weight: 600; 
                padding: 0 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {C['primary_dk']}; 
            }}
        """)

        export_btn.clicked.connect(self._export_dashboard_report)
        row.addWidget(refresh_btn)
        row.addWidget(export_btn)

        # Add top padding
        spacer = QWidget()
        spacer.setFixedHeight(8)
        self.content_layout.addWidget(spacer)
        self.content_layout.addLayout(row)
        self.content_layout.addWidget(_divider())

    # ═════════════════════════════════════════════════════════════════════════
    #  2. KPI STAT CARDS - Enhanced with modern design
    # ═════════════════════════════════════════════════════════════════════════
    def _build_stats_row(self):
        self.stats_row_layout = QHBoxLayout()
        self.stats_row_layout.setSpacing(16)

        self._stat_labels = {}  # title -> (val_lbl, chg_lbl)
        
        # Enhanced stat cards with gradient backgrounds and better icons
        cards = [
            ("Total Sales",    "Loading…", "Today", "fa5s.rupee-sign",  C['success'], "#ecfdf5", C['success_lt']),
            ("Total Orders",   "Loading…", "Today", "fa5s.receipt", C['info'],    "#f0fdfa", C['info_lt']),
            ("New Customers",  "Loading…", "Today", "fa5s.user-plus",   C['amber'],   "#fffbeb", C['amber_lt']),
            ("Pending Orders", "Loading…", "Active","fa5s.clock",        C['danger'],  "#fef2f2", C['danger_lt']),
        ]

        for title, value, change, icon_name, color, bg, badge_bg in cards:
            card, val_lbl, chg_lbl = self._make_stat_card(title, value, change, icon_name, color, bg, badge_bg)
            self._stat_labels[title] = (val_lbl, chg_lbl)
            self.stats_row_layout.addWidget(card)

        self.content_layout.addLayout(self.stats_row_layout)

    def _make_stat_card(self, title, value, change, icon_name, color, bg, badge_bg):
        card = QFrame()
        card.setMinimumHeight(120)
        card.setStyleSheet(f"""
            QFrame {{
                background: {C['surface']};
                border: 1px solid #E8ECF0;
                border-radius: 16px;
            }}
            QFrame:hover {{
                border-color: {color};
                background: {badge_bg}40;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Top: icon + title with modern styling
        top = QHBoxLayout()
        top.setSpacing(10)
        
        # Icon container with colored background
        icon_container = QFrame()
        icon_container.setFixedSize(36, 36)
        icon_container.setStyleSheet(f"""
            background: {badge_bg};
            border-radius: 10px;
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color=color).pixmap(18, 18))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        icon_layout.addWidget(icon_lbl)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C['text_sec']}; border: none; background: transparent;")

        top.addWidget(icon_container)
        top.addWidget(title_lbl)
        top.addStretch()

        # Bottom: value + badge with improved typography
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {C['text_primary']}; border: none; background: transparent; letter-spacing: -0.5px;")

        chg_lbl = QLabel(change)
        chg_lbl.setStyleSheet(f"""
            font-size: 11px; 
            font-weight: 700; 
            color: {color}; 
            background: {badge_bg}; 
            border-radius: 6px; 
            padding: 4px 10px; 
            border: none;
        """)

        bottom.addWidget(val_lbl)
        bottom.addStretch()
        bottom.addWidget(chg_lbl)
        bottom.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(top)
        layout.addLayout(bottom)
        return card, val_lbl, chg_lbl

    # ═════════════════════════════════════════════════════════════════════════
    #  3. MONTHLY TARGETS - Enhanced styling
    # ═════════════════════════════════════════════════════════════════════════
    def _build_targets_row(self):
        card = _card(elevated=True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(18)

        card_layout.addLayout(_section_header("Monthly Targets", icon="fa5s.bullseye"))
        card_layout.addWidget(_divider())

        targets_row = QHBoxLayout()
        targets_row.setSpacing(48)

        metrics = [
            ("Revenue Target",    85, C['success']),
            ("Customer Growth",   62, C['info']),
            ("Order Efficiency",  94, C['amber']),
        ]

        for label, val, color in metrics:
            col = QVBoxLayout()
            col.setSpacing(10)

            lbl_row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {C['text_sec']};")
            
            pct = QLabel(f"{val}%")
            pct.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {color};")
            
            lbl_row.addWidget(lbl)
            lbl_row.addStretch()
            lbl_row.addWidget(pct)
            col.addLayout(lbl_row)

            bar = QProgressBar()
            bar.setValue(val)
            bar.setTextVisible(False)
            bar.setFixedHeight(10)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    background: #F1F5F9;
                    border-radius: 5px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color}, stop:1 {color}CC);
                    border-radius: 5px;
                }}
            """)
            
            col.addWidget(bar)
            targets_row.addLayout(col)

        card_layout.addLayout(targets_row)
        self.content_layout.addWidget(card)

    # ═════════════════════════════════════════════════════════════════════════
    #  4. MAIN CONTENT - Improved table and layout
    # ═════════════════════════════════════════════════════════════════════════
    def _build_main_content(self):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(24)

        row.addWidget(self._build_orders_table(), stretch=3)
        row.addLayout(self._build_right_column(),  stretch=2)

        self.content_layout.addWidget(container)

    def _build_orders_table(self):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Modern view all button
        view_all_btn = QPushButton("View All")
        view_all_btn.setFlat(True)
        view_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_all_btn.setStyleSheet(f"""
            color: {C['primary']}; 
            font-weight: 700; 
            font-size: 13px;
            border: none;
            background: transparent;
            padding: 4px 8px;
        """)
        
        layout.addLayout(_section_header("Recent Orders", view_all_btn, icon="fa5s.shopping-cart"))
        layout.addWidget(_divider())

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Order ID", "Customer", "Amount", "Status"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setStyleSheet(f"""
            QHeaderView::section {{
                background: #F8FAFC; color: {C['text_sec']};
                font-size: 12px; font-weight: 700; padding: 12px 8px;
                border: none; border-bottom: 2px solid #E8ECF0;
                letter-spacing: 0.3px;
            }}
        """)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setFrameShape(QFrame.Shape.NoFrame)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().setDefaultSectionSize(52)
        table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent; 
                border: none;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #F1F5F9;
            }}
            QTableWidget::item:selected {{
                background: #ECFDF5;
                color: {C['primary']};
            }}
            QTableWidget::item:hover {{
                background: #F8FAFC;
            }}
        """)

        self._orders_table = table
        layout.addWidget(table)
        return card

    def _build_right_column(self):
        col = QVBoxLayout()
        col.setSpacing(20)

        col.addWidget(self._build_top_products())
        col.addWidget(self._build_quick_actions())
        self._build_alerts_card(col)

        return col

    def _build_top_products(self):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addLayout(_section_header("Top Products", icon="fa5s.fire"))
        layout.addWidget(_divider())

        self._top_products_layout = layout
        return card

    def _build_quick_actions(self):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        layout.addLayout(_section_header("Quick Actions", icon="fa5s.bolt"))
        layout.addWidget(_divider())

        grid = QGridLayout()
        grid.setSpacing(12)

        # Modernized quick action buttons with icons
        buttons = [
            ("New Order",     "fa5s.plus-circle",       C['success'], "#ecfdf5"),
            ("Add Stock",     "fa5s.box-open",          C['warning'], "#fffbeb"),
            ("Add Customer",  "fa5s.user-plus",         C['info'],    "#f0fdfa"),
            ("Reports",       "fa5s.chart-pie",         C['primary'], "#ecfdf5"),
        ]

        for idx, (label, icon, color, bg) in enumerate(buttons):
            btn = QPushButton(f"  {label}")
            btn.setIcon(qta.icon(icon, color=color))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(48)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {bg}; 
                    border: 1px solid #E8ECF0;
                    border-radius: 12px; 
                    color: {C['text_primary']}; 
                    font-weight: 600;
                    font-size: 13px;
                    text-align: left; 
                    padding-left: 16px;
                }}
                QPushButton:hover {{
                    background: {color}15;
                    color: {color}; 
                    border-color: {color}50;
                }}
            """)
            grid.addWidget(btn, idx // 2, idx % 2)

        layout.addLayout(grid)
        return card

    def _build_alerts_card(self, parent_layout):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Modern PO button
        self.po_btn = QPushButton("  Gen PO")
        self.po_btn.setIcon(qta.icon("fa5s.file-invoice", color="white"))
        self.po_btn.setFixedHeight(32)
        self.po_btn.setStyleSheet(f"""
            background: {C['danger']}; 
            color: white; 
            border: none; 
            border-radius: 8px; 
            font-weight: 700; 
            font-size: 12px;
            padding: 0 14px;
        """)
        self.po_btn.clicked.connect(self.generate_po)
        self.po_btn.setVisible(False)

        h_row = QHBoxLayout()
        h_row.setSpacing(10)
        
        # Alert icon
        alert_icon = QLabel()
        alert_icon.setPixmap(qta.icon("fa5s.exclamation-triangle", color=C['danger']).pixmap(16, 16))
        alert_icon.setStyleSheet("background: transparent;")
        
        title_lbl = QLabel("Stock Alerts")
        title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {C['text_primary']};")
        
        h_row.addWidget(alert_icon)
        h_row.addWidget(title_lbl)
        h_row.addStretch()
        h_row.addWidget(self.po_btn)
        
        layout.addLayout(h_row)
        layout.addWidget(_divider())

        self.alerts_list = QVBoxLayout()
        self.alerts_list.setSpacing(10)
        layout.addLayout(self.alerts_list)

        parent_layout.addWidget(card)
        self.refresh_alerts()

    def refresh_alerts(self):
        if not hasattr(self, "alerts_list"): return

        while self.alerts_list.count():
            child = self.alerts_list.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        try:
            all_items, _ = get_inventory()
            self.low_stock_items = []

            for item in all_items:
                qty    = item.get("qty", 0)
                thresh = item.get("threshold", 5)

                if qty <= thresh:
                    self.low_stock_items.append(item)

                    w  = QWidget()
                    wl = QHBoxLayout(w)
                    wl.setContentsMargins(4, 6, 4, 6)

                    # Item name with icon
                    item_icon = QLabel()
                    item_icon.setPixmap(qta.icon("fa5s.cube", color=C['danger']).pixmap(14, 14))
                    item_icon.setStyleSheet("background: transparent;")
                    
                    lbl = QLabel(item["item_name"])
                    lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C['text_primary']}; background: transparent;")

                    stat = QLabel(f"{qty} / {thresh}")
                    stat.setStyleSheet(f"background: {C['danger_lt']}; color: {C['danger']}; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px;")

                    wl.addWidget(item_icon)
                    wl.addSpacing(8)
                    wl.addWidget(lbl)
                    wl.addStretch()
                    wl.addWidget(stat)
                    self.alerts_list.addWidget(w)

            if not self.low_stock_items:
                ok_icon = QLabel()
                ok_icon.setPixmap(qta.icon("fa5s.check-circle", color=C['success']).pixmap(16, 16))
                ok_icon.setStyleSheet("background: transparent;")
                
                ok_row = QHBoxLayout()
                ok_row.addWidget(ok_icon)
                ok_row.addSpacing(8)
                ok_lbl = QLabel("Inventory is healthy")
                ok_lbl.setStyleSheet(f"color: {C['success']}; font-weight: 600; font-size: 13px;")
                ok_row.addWidget(ok_lbl)
                ok_row.addStretch()
                
                ok_widget = QWidget()
                ok_widget.setStyleSheet(f"background: {C['success_lt']}; border-radius: 8px; padding: 12px;")
                ok_widget.setLayout(ok_row)
                self.alerts_list.addWidget(ok_widget)
                self.po_btn.setVisible(False)
            else:
                self.po_btn.setVisible(True)

        except Exception:
            err_icon = QLabel()
            err_icon.setPixmap(qta.icon("fa5s.exclamation-circle", color=C['danger']).pixmap(16, 16))
            err_icon.setStyleSheet("background: transparent;")
            
            err_row = QHBoxLayout()
            err_row.addWidget(err_icon)
            err_row.addSpacing(8)
            err_lbl = QLabel("Failed to load inventory.")
            err_lbl.setStyleSheet(f"color: {C['danger']}; font-weight: 600; font-size: 13px;")
            err_row.addWidget(err_lbl)
            err_row.addStretch()
            
            err_widget = QWidget()
            err_widget.setStyleSheet(f"background: {C['danger_lt']}; border-radius: 8px; padding: 12px;")
            err_widget.setLayout(err_row)
            self.alerts_list.addWidget(err_widget)

    def generate_po(self):
        if not hasattr(self, "low_stock_items") or not self.low_stock_items:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Purchase Order", "purchase_order.pdf", "PDF Files (*.pdf)"
        )
        if not path: return

        success, msg = generate_purchase_order(self.low_stock_items, path)
        if success:
            QMessageBox.information(self, "Success", f"Purchase Order saved to:\n{path}")
        else:
            QMessageBox.critical(self, "Error", f"Failed to generate PO: {msg}")

    def refresh_data(self):
        self.refresh_alerts()
        self._refresh_kpi_cards()
        self._refresh_orders_table()
        self._refresh_top_products()

    def _refresh_kpi_cards(self):
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_orders = list(orders_col.find({
                "updated_at": {"$gte": today_start},
                "status": "Completed"
            }))
            total_sales   = sum(o.get('grand_total', 0) for o in today_orders)
            total_orders  = len(today_orders)
            new_customers = len(set(
                o.get('customer_phone', '') for o in today_orders
                if o.get('customer_phone')
            ))
            pending = orders_col.count_documents({
                "status": {"$in": ["Running", "Pending", "Hold"]}
            })

            vals = {
                "Total Sales":    (f"Rs {total_sales:,.0f}", "Today"),
                "Total Orders":   (str(total_orders),        "Today"),
                "New Customers":  (str(new_customers),       "Today"),
                "Pending Orders": (str(pending),             "Active"),
            }
            for title, (value, badge) in vals.items():
                if title in self._stat_labels:
                    val_lbl, chg_lbl = self._stat_labels[title]
                    val_lbl.setText(value)
                    chg_lbl.setText(badge)
        except Exception as e:
            pass

    def _refresh_orders_table(self):
        if not hasattr(self, '_orders_table'): return
        try:
            recent = list(orders_col.find().sort("created_at", -1).limit(8))
            table = self._orders_table
            table.setRowCount(len(recent))
            for r, order in enumerate(recent):
                oid  = order.get('invoice_no') or str(order['_id'])[:8]
                cust = order.get('customer_name') or order.get('waiter') or '—'
                amt  = f"Rs {order.get('grand_total', 0):,.0f}"
                stat = order.get('status', '—')

                for c, txt in enumerate([oid, cust, amt]):
                    cell_item = QTableWidgetItem(txt)
                    cell_item.setForeground(QColor(C['text_primary']))
                    cell_item.setFont(QFont("Segoe UI", 10))
                    cell_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                    if c == 0:
                        cell_item.setForeground(QColor(C['primary']))
                        cell_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                    table.setItem(r, c, cell_item)

                # Status Badge
                badge = QLabel(stat)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                bg_color = C['bg']
                fg_color = C['text_sec']
                
                if stat == "Completed":
                    bg_color = C['success_lt']; fg_color = C['success']
                elif stat in ("Running", "Pending", "Kitchen"):
                    bg_color = C['warning_lt']; fg_color = C['warning']
                elif stat in ("Void", "Refunded", "Cancelled"):
                    bg_color = C['danger_lt']; fg_color = C['danger']

                badge.setStyleSheet(f"background: {bg_color}; color: {fg_color}; border-radius: 6px; font-weight: 700; font-size: 11px; padding: 4px;")
                
                cell_w = QWidget()
                cl = QHBoxLayout(cell_w)
                cl.setContentsMargins(8, 6, 8, 6)
                cl.addStretch(); cl.addWidget(badge); cl.addStretch()
                table.setCellWidget(r, 3, cell_w)
        except Exception:
            pass

    def _refresh_top_products(self):
        if not hasattr(self, '_top_products_layout'): return
        try:
            layout = self._top_products_layout
            while layout.count() > 2:
                item = layout.takeAt(layout.count() - 1)
                if item.widget(): item.widget().deleteLater()
                elif item.layout():
                    while item.layout().count():
                        sub = item.layout().takeAt(0)
                        if sub.widget(): sub.widget().deleteLater()

            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            report = get_item_sales_report(today_start, datetime.now())
            top3   = report[:3] if report else []

            if not top3:
                lbl = QLabel("No sales data for today")
                lbl.setStyleSheet(f"color: {C['text_hint']}; padding: 10px;")
                layout.addWidget(lbl)
                return

            rank_colors = [C['success'], C['info'], C['amber']]
            for i, item in enumerate(top3):
                row = QHBoxLayout()
                row.setSpacing(12)

                rank_lbl = QLabel(str(i + 1))
                rank_lbl.setFixedSize(28, 28)
                rank_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                rank_lbl.setStyleSheet(f"background:{rank_colors[i]}; color: white; border-radius: 14px; font-weight: 800; font-size: 12px;")

                info = QVBoxLayout()
                info.setSpacing(2)
                name_lbl = QLabel(item.get('_id', '—'))
                name_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C['text_primary']};")
                
                revenue = item.get('total', 0)
                price_lbl = QLabel(f"Rs {revenue:,.0f} revenue")
                price_lbl.setStyleSheet(f"font-size: 11px; color: {C['text_sec']};")
                
                info.addWidget(name_lbl)
                info.addWidget(price_lbl)

                sales_lbl = QLabel(f"{item.get('qty', 0)} sold")
                sales_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {C['primary']};")

                row.addWidget(rank_lbl)
                row.addLayout(info)
                row.addStretch()
                row.addWidget(sales_lbl)
                layout.addLayout(row)
        except Exception:
            pass

    def resizeEvent(self, event):
        """Handle window resize for responsive behavior"""
        super().resizeEvent(event)
        width = self.width()
        
        # Adjust stats row layout
        if hasattr(self, 'stats_row_layout'):
            is_horizontal = isinstance(self.stats_row_layout, QHBoxLayout)
            
            if width < 800 and is_horizontal:
                # Switch to QVBoxLayout
                new_layout = QVBoxLayout()
                new_layout.setSpacing(12)
                while self.stats_row_layout.count():
                    item = self.stats_row_layout.takeAt(0)
                    if item.widget():
                        new_layout.addWidget(item.widget())
                
                # Replace old layout
                self.content_layout.removeItem(self.stats_row_layout)
                self.stats_row_layout.deleteLater()
                self.stats_row_layout = new_layout
                self.content_layout.insertLayout(2, self.stats_row_layout)

            elif width >= 800 and not is_horizontal:
                # Switch to QHBoxLayout
                new_layout = QHBoxLayout()
                new_layout.setSpacing(12)
                while self.stats_row_layout.count():
                    item = self.stats_row_layout.takeAt(0)
                    if item.widget():
                        new_layout.addWidget(item.widget())

                # Replace old layout
                self.content_layout.removeItem(self.stats_row_layout)
                self.stats_row_layout.deleteLater()
                self.stats_row_layout = new_layout
                self.content_layout.insertLayout(2, self.stats_row_layout)

    def _export_dashboard_report(self):
        from backend.services.report_service import export_to_csv, today_sales
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Today's Sales", "today_sales.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            data = today_sales()
            headers = ["invoice_no", "order_type", "payment_method", "grand_total", "timestamp"]
            ok, msg = export_to_csv(data, path, headers)
            if ok:
                QMessageBox.information(self, "Export Success", f"Report saved to:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", msg)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

