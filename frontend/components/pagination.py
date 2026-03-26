from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtCore import pyqtSignal, Qt
import qtawesome as qta

class PaginationControl(QWidget):
    page_changed = pyqtSignal(int)
    limit_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 1
        self.total_pages = 1
        self.total_records = 0
        self.page_size = 20
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        
        # Limit Selector
        layout.addWidget(QLabel("Show:"))
        self.limit_combo = QComboBox()
        self.limit_combo.addItems(["10", "20", "50", "100"])
        self.limit_combo.setCurrentText(str(self.page_size))
        self.limit_combo.currentTextChanged.connect(self.on_limit_change)
        self.limit_combo.setFixedWidth(60)
        layout.addWidget(self.limit_combo)
        
        layout.addStretch()
        
        # Info Label
        self.info_lbl = QLabel("Showing 0-0 of 0")
        self.info_lbl.setStyleSheet("color: #666;")
        layout.addWidget(self.info_lbl)
        
        layout.addSpacing(10)
        
        # Controls
        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(qta.icon('fa5s.chevron-left'))
        self.btn_prev.setFixedWidth(30)
        self.btn_prev.clicked.connect(self.go_prev)
        
        self.page_lbl = QLabel("Page 1")
        self.page_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_lbl.setFixedWidth(60)
        
        self.btn_next = QPushButton()
        self.btn_next.setIcon(qta.icon('fa5s.chevron-right'))
        self.btn_next.setFixedWidth(30)
        self.btn_next.clicked.connect(self.go_next)
        
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.page_lbl)
        layout.addWidget(self.btn_next)
        
        self.update_ui()

    def set_total_records(self, total):
        self.total_records = total
        self.total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        
        # Adjust current page if out of bounds
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        self.update_ui()

    def update_ui(self):
        start = (self.current_page - 1) * self.page_size + 1
        end = min(self.current_page * self.page_size, self.total_records)
        
        if self.total_records == 0:
            start, end = 0, 0
            
        self.info_lbl.setText(f"Showing {start}-{end} of {self.total_records}")
        self.page_lbl.setText(f"Page {self.current_page}/{self.total_pages}")
        
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < self.total_pages)

    def go_prev(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_ui()
            self.page_changed.emit(self.current_page)

    def go_next(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_ui()
            self.page_changed.emit(self.current_page)

    def reset(self):
        self.current_page = 1
        self.update_ui()

    def on_limit_change(self, text):
        try:
            new_limit = int(text)
            if new_limit != self.page_size:
                self.page_size = new_limit
                self.current_page = 1
                self.limit_changed.emit(self.page_size)
        except ValueError:
            pass
