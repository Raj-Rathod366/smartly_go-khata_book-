import sys
import bcrypt
import sqlite3
import qrcode
import shutil
import csv
import openpyxl
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from twilio.rest import Client

# Imports for PDF and Printing
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QTabWidget, QComboBox, QDateEdit, QTextEdit,
                             QDialog, QGroupBox, QScrollArea, QFileDialog, QHeaderView, QFormLayout)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont
from PyQt5 import QtCore, QtGui, QtWidgets

class SmartlyGo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartlyGo - Digital Khata System")
        self.setGeometry(100, 100, 1280, 900)
        self.dark_mode = False
        self.current_user = None

        self.init_db()
        self.setup_ui()
        self.apply_style()

    def init_db(self):
        self.conn = sqlite3.connect("smartlygo.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password BLOB,
                business_name TEXT,
                phone TEXT,
                address TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, phone TEXT, email TEXT,
                address TEXT, balance REAL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY, user_id INTEGER, customer_id INTEGER, amount REAL,
                type TEXT, date TEXT, description TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, price REAL, quantity INTEGER,
                barcode TEXT, category TEXT, FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY, currency TEXT DEFAULT '₹', sms_notifications INTEGER DEFAULT 1,
                dark_mode INTEGER DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        self.conn.commit()

    def setup_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.setup_login_tab()
        self.setup_dashboard_tab()
        self.setup_khata_tab()
        self.setup_inventory_tab()
        self.setup_reports_tab()
        self.setup_visualization_tab()
        self.setup_settings_tab()

        self.tabs.setCurrentIndex(0)
        for i in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(i, False)

    def setup_login_tab(self):
        login_tab = QWidget()
        layout = QVBoxLayout(login_tab)
        layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_pixmap = QPixmap("logo.png") if QtCore.QFile.exists("logo.png") else self.create_default_logo()
        logo_label.setPixmap(logo_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        welcome_label = QLabel("SmartlyGo - Digital Khata System")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(welcome_label)

        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_container.setMaximumWidth(400)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        form_layout.addRow(QLabel("Username:"), self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow(QLabel("Password:"), self.password_input)

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.regular_login)
        form_layout.addRow(login_btn)

        register_btn = QPushButton("Register New User")
        register_btn.clicked.connect(self.show_register_dialog)
        form_layout.addRow(register_btn)

        layout.addWidget(form_container)

        footer_label = QLabel("© 2025 SmartlyGo")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #7f8c8d; margin-top: 20px;")
        layout.addStretch()
        layout.addWidget(footer_label)
        
        self.tabs.addTab(login_tab, "Login")

    def setup_dashboard_tab(self):
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)

        header_layout = QHBoxLayout()
        self.welcome_label = QLabel("Welcome to SmartlyGo!")
        self.welcome_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(self.welcome_label)
        header_layout.addStretch()

        self.dark_mode_btn = QPushButton("Toggle Dark Mode")
        self.dark_mode_btn.clicked.connect(self.toggle_dark_mode)
        header_layout.addWidget(self.dark_mode_btn)
        
        self.logout_btn = QPushButton("Log Out")
        self.logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(self.logout_btn)
        
        layout.addLayout(header_layout)

        stats_group = QGroupBox("Business Overview")
        stats_layout = QHBoxLayout(stats_group)
        self.total_customers_card = self.create_stat_card("Total Customers", "0", "#3498db")
        stats_layout.addWidget(self.total_customers_card)
        self.pending_payments_card = self.create_stat_card("Pending Payments", "₹0", "#e74c3c")
        stats_layout.addWidget(self.pending_payments_card)
        self.recent_transactions_card = self.create_stat_card("Recent Transactions", "0", "#2ecc71")
        stats_layout.addWidget(self.recent_transactions_card)
        self.inventory_items_card = self.create_stat_card("Inventory Items", "0", "#f39c12")
        stats_layout.addWidget(self.inventory_items_card)
        layout.addWidget(stats_group)

        quick_actions_group = QGroupBox("Quick Actions")
        quick_actions_layout = QHBoxLayout(quick_actions_group)
        add_customer_btn = QPushButton("Add Customer")
        add_customer_btn.clicked.connect(self.show_add_customer_dialog)
        quick_actions_layout.addWidget(add_customer_btn)
        add_transaction_btn = QPushButton("Add Transaction")
        
        # --- THIS IS THE CORRECTED LINE ---
        add_transaction_btn.clicked.connect(lambda: self.show_add_transaction_dialog("debit"))
        
        quick_actions_layout.addWidget(add_transaction_btn)
        add_product_btn = QPushButton("Add Product")
        add_product_btn.clicked.connect(self.show_add_product_dialog)
        quick_actions_layout.addWidget(add_product_btn)
        layout.addWidget(quick_actions_group)

        recent_trans_group = QGroupBox("Recent Transactions")
        recent_trans_layout = QVBoxLayout(recent_trans_group)
        self.recent_transactions_table = QTableWidget()
        self.recent_transactions_table.setColumnCount(5)
        self.recent_transactions_table.setHorizontalHeaderLabels(["Date", "Customer", "Type", "Amount", "Description"])
        self.recent_transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        recent_trans_layout.addWidget(self.recent_transactions_table)
        layout.addWidget(recent_trans_group)
        
        self.tabs.addTab(dashboard_tab, "Dashboard")

    def setup_khata_tab(self):
        khata_tab = QWidget()
        layout = QVBoxLayout(khata_tab)

        customer_group = QGroupBox("Customer Management")
        customer_layout = QVBoxLayout(customer_group)
        search_layout = QHBoxLayout()
        self.customer_search = QLineEdit()
        self.customer_search.setPlaceholderText("Search customers...")
        self.customer_search.textChanged.connect(self.filter_customers)
        search_layout.addWidget(self.customer_search)
        add_customer_btn = QPushButton("Add Customer")
        add_customer_btn.clicked.connect(self.show_add_customer_dialog)
        search_layout.addWidget(add_customer_btn)
        customer_layout.addLayout(search_layout)
        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self.load_customer_transactions)
        customer_layout.addWidget(self.customer_combo)
        self.customer_details_label = QLabel("Select a customer to view details")
        customer_layout.addWidget(self.customer_details_label)
        layout.addWidget(customer_group)

        trans_group = QGroupBox("Transactions")
        trans_layout = QVBoxLayout(trans_group)
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(6)
        self.transactions_table.setHorizontalHeaderLabels(["ID", "Date", "Type", "Amount", "Balance", "Description"])
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        trans_layout.addWidget(self.transactions_table)
        transaction_btn_layout = QHBoxLayout()
        add_credit_btn = QPushButton("Add Credit")
        add_credit_btn.clicked.connect(self.show_add_credit_dialog)
        transaction_btn_layout.addWidget(add_credit_btn)
        add_debit_btn = QPushButton("Add Debit")
        add_debit_btn.clicked.connect(self.show_add_debit_dialog)
        transaction_btn_layout.addWidget(add_debit_btn)
        print_btn = QPushButton("Print Statement")
        print_btn.clicked.connect(self.print_customer_statement)
        transaction_btn_layout.addWidget(print_btn)
        trans_layout.addLayout(transaction_btn_layout)
        layout.addWidget(trans_group)

        self.tabs.addTab(khata_tab, "Khata Management")

    def setup_inventory_tab(self):
        inventory_tab = QWidget()
        layout = QVBoxLayout(inventory_tab)

        product_group = QGroupBox("Product Management")
        product_layout = QVBoxLayout(product_group)
        search_layout = QHBoxLayout()
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("Search products...")
        self.product_search.textChanged.connect(self.filter_products)
        search_layout.addWidget(self.product_search)
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", "")
        self.category_filter.currentIndexChanged.connect(self.filter_products)
        search_layout.addWidget(self.category_filter)
        add_product_btn = QPushButton("Add Product")
        add_product_btn.clicked.connect(self.show_add_product_dialog)
        search_layout.addWidget(add_product_btn)
        product_layout.addLayout(search_layout)
        
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels(["ID", "Name", "Price", "Quantity", "Category", "Barcode"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        product_layout.addWidget(self.products_table)

        product_btn_layout = QHBoxLayout()
        edit_product_btn = QPushButton("Edit Product")
        edit_product_btn.clicked.connect(self.edit_product)
        product_btn_layout.addWidget(edit_product_btn)
        delete_product_btn = QPushButton("Delete Product")
        delete_product_btn.clicked.connect(self.delete_product)
        product_btn_layout.addWidget(delete_product_btn)
        qr_btn = QPushButton("Generate QR")
        qr_btn.clicked.connect(self.generate_product_qr)
        product_btn_layout.addWidget(qr_btn)
        payment_qr_btn = QPushButton("Payment QR")
        payment_qr_btn.clicked.connect(self.generate_payment_qr)
        product_btn_layout.addWidget(payment_qr_btn)
        product_layout.addLayout(product_btn_layout)
        layout.addWidget(product_group)

        low_stock_group = QGroupBox("Low Stock Items")
        low_stock_layout = QVBoxLayout(low_stock_group)
        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(4)
        self.low_stock_table.setHorizontalHeaderLabels(["Name", "Price", "Quantity", "Category"])
        self.low_stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        low_stock_layout.addWidget(self.low_stock_table)
        layout.addWidget(low_stock_group)

        self.tabs.addTab(inventory_tab, "Inventory")

    def setup_reports_tab(self):
        reports_tab = QWidget()
        layout = QVBoxLayout(reports_tab)

        controls_group = QGroupBox("Report Controls")
        controls_layout = QFormLayout(controls_group)
        
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(["Daily Sales", "Customer Ledger", "Product Sales", "Transaction Summary", "Customer Balances"])
        controls_layout.addRow(QLabel("Report Type:"), self.report_type_combo)
        
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        date_layout = QHBoxLayout()
        date_layout.addWidget(self.date_from)
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.date_to)
        controls_layout.addRow(QLabel("From:"), date_layout)
        
        self.report_customer_combo = QComboBox()
        controls_layout.addRow(QLabel("Customer:"), self.report_customer_combo)
        self.report_type_combo.currentTextChanged.connect(lambda text: self.report_customer_combo.setEnabled(text == "Customer Ledger"))
        self.report_customer_combo.setEnabled(False)
        
        generate_btn = QPushButton("Generate Report")
        generate_btn.clicked.connect(self.generate_report)
        controls_layout.addRow(generate_btn)
        layout.addWidget(controls_group)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setFont(QFont("Monospace"))
        layout.addWidget(self.report_text)
        
        export_group = QGroupBox("Export Options")
        export_layout = QHBoxLayout(export_group)
        export_pdf_btn = QPushButton("Export to PDF")
        export_pdf_btn.clicked.connect(self.export_to_pdf)
        export_layout.addWidget(export_pdf_btn)
        export_excel_btn = QPushButton("Export to Excel")
        export_excel_btn.clicked.connect(self.export_to_excel)
        export_layout.addWidget(export_excel_btn)
        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self.export_to_csv)
        export_layout.addWidget(export_csv_btn)
        export_print_btn = QPushButton("Print Report")
        export_print_btn.clicked.connect(self.print_report)
        export_layout.addWidget(export_print_btn)
        layout.addWidget(export_group)

        self.tabs.addTab(reports_tab, "Reports")

    def setup_visualization_tab(self):
        visualization_tab = QWidget()
        layout = QVBoxLayout(visualization_tab)

        controls_group = QGroupBox("Visualization Controls")
        controls_layout = QFormLayout(controls_group)
        
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Sales Trend", "Customer Balances", "Product Categories", "Transaction Types", "Monthly Summary"])
        controls_layout.addRow(QLabel("Chart Type:"), self.chart_type_combo)

        self.viz_date_from = QDateEdit(QDate.currentDate().addMonths(-6))
        self.viz_date_from.setCalendarPopup(True)
        self.viz_date_to = QDateEdit(QDate.currentDate())
        self.viz_date_to.setCalendarPopup(True)
        viz_date_layout = QHBoxLayout()
        viz_date_layout.addWidget(self.viz_date_from)
        viz_date_layout.addWidget(QLabel("To:"))
        viz_date_layout.addWidget(self.viz_date_to)
        controls_layout.addRow(QLabel("From:"), viz_date_layout)

        generate_btn = QPushButton("Generate Chart")
        generate_btn.clicked.connect(self.generate_chart)
        controls_layout.addRow(generate_btn)
        layout.addWidget(controls_group)

        self.chart_widget = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_widget)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.chart_widget)
        layout.addWidget(scroll)

        self.tabs.addTab(visualization_tab, "Visualization")

    def setup_settings_tab(self):
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        layout.setAlignment(Qt.AlignTop)

        user_group = QGroupBox("User Settings")
        user_layout = QFormLayout(user_group)
        self.business_name_input = QLineEdit()
        user_layout.addRow("Business Name:", self.business_name_input)
        self.phone_input = QLineEdit()
        user_layout.addRow("Phone:", self.phone_input)
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(80)
        user_layout.addRow("Address:", self.address_input)
        
        logo_layout = QHBoxLayout()
        self.logo_path = QLineEdit()
        self.logo_path.setReadOnly(True)
        logo_layout.addWidget(self.logo_path)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_logo)
        logo_layout.addWidget(browse_btn)
        user_layout.addRow("Business Logo:", logo_layout)
        
        self.logo_preview = QLabel()
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setFixedSize(150, 150)
        user_layout.addRow(self.logo_preview)
        layout.addWidget(user_group)

        app_group = QGroupBox("Application Settings")
        app_layout = QFormLayout(app_group)
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["₹ (Rupee)", "$ (Dollar)", "€ (Euro)", "£ (Pound)"])
        app_layout.addRow("Currency:", self.currency_combo)
        self.notify_check = QtWidgets.QCheckBox()
        app_layout.addRow("Enable SMS Notifications:", self.notify_check)
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        app_layout.addRow(save_btn)
        layout.addWidget(app_group)

        backup_group = QGroupBox("Data Management")
        backup_layout = QHBoxLayout(backup_group)
        backup_btn = QPushButton("Backup Data")
        backup_btn.clicked.connect(self.backup_data)
        backup_layout.addWidget(backup_btn)
        restore_btn = QPushButton("Restore Data")
        restore_btn.clicked.connect(self.restore_data)
        backup_layout.addWidget(restore_btn)
        layout.addWidget(backup_group)

        self.tabs.addTab(settings_tab, "Settings")

    def create_stat_card(self, title, value, color):
        card = QWidget()
        card.setStyleSheet(f"background-color: {color}; border-radius: 10px; padding: 15px;")
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setObjectName("title_label")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: white;")
        value_label = QLabel(value)
        value_label.setObjectName("value_label")
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title_label, alignment=Qt.AlignLeft)
        layout.addWidget(value_label, alignment=Qt.AlignCenter)
        return card

    def create_default_logo(self):
        pixmap = QPixmap(200, 200)
        pixmap.fill(Qt.white)
        painter = QtGui.QPainter(pixmap)
        painter.setPen(QtGui.QPen(Qt.darkGray, 3))
        painter.setFont(QtGui.QFont("Arial", 24, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "SmartlyGo")
        painter.end()
        return pixmap

    def regular_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password.")
            return

        self.cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = self.cursor.fetchone()

        if user and user[1] and bcrypt.checkpw(password.encode('utf-8'), user[1]):
            self.current_user = user[0]
            self.welcome_label.setText(f"Welcome, {username}!")
            self.load_settings()
            self.load_dashboard_data()
            self.tabs.setCurrentIndex(1)
            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, i != 0)
            self.load_customers()
            self.load_products()
            self.load_categories()
        else:
            QMessageBox.warning(self, "Error", "Invalid username or password.")

    def logout(self):
        self.current_user = None
        self.username_input.clear()
        self.password_input.clear()

        self.welcome_label.setText("Welcome to SmartlyGo!")
        for card in [self.total_customers_card, self.pending_payments_card, self.recent_transactions_card, self.inventory_items_card]:
            card.findChild(QLabel, "value_label").setText("0")
        
        self.recent_transactions_table.setRowCount(0)
        self.transactions_table.setRowCount(0)
        self.products_table.setRowCount(0)
        self.low_stock_table.setRowCount(0)
        self.customer_combo.clear()
        self.customer_details_label.setText("Select a customer to view details")

        for i in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(i, False)
        
        self.tabs.setTabEnabled(0, True)
        self.tabs.setCurrentIndex(0)
        self.username_input.setFocus()
        QMessageBox.information(self, "Logged Out", "You have been successfully logged out.")

    def show_register_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Register New User")
        dialog.setMinimumWidth(400)
        layout = QFormLayout(dialog)

        username_input = QLineEdit()
        layout.addRow("Username:", username_input)
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("Password:", password_input)
        confirm_password_input = QLineEdit()
        confirm_password_input.setEchoMode(QLineEdit.Password)
        layout.addRow("Confirm Password:", confirm_password_input)
        business_name_input = QLineEdit()
        layout.addRow("Business Name:", business_name_input)
        phone_input = QLineEdit()
        layout.addRow("Phone:", phone_input)
        address_input = QTextEdit()
        address_input.setMaximumHeight(80)
        layout.addRow("Address:", address_input)
        
        register_user_btn = QPushButton("Register")
        register_user_btn.clicked.connect(lambda: self.register_user(
            username_input.text(), password_input.text(), confirm_password_input.text(),
            business_name_input.text(), phone_input.text(), address_input.toPlainText(), dialog
        ))
        layout.addRow(register_user_btn)
        
        dialog.exec_()

    def register_user(self, username, password, confirm_password, business_name, phone, address, dialog):
        if not all([username, password, confirm_password, business_name, phone, address]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields.")
            return
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            self.cursor.execute("INSERT INTO users (username, password, business_name, phone, address) VALUES (?, ?, ?, ?, ?)",
                                (username, hashed_password, business_name, phone, address))
            self.conn.commit()
            QMessageBox.information(self, "Success", "User registered successfully!")
            dialog.accept()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "Username already exists.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An error occurred: {e}")

    def load_dashboard_data(self):
        if not self.current_user: return
        self.cursor.execute("SELECT COUNT(*) FROM customers WHERE user_id = ?", (self.current_user,))
        total_customers = self.cursor.fetchone()[0]
        self.total_customers_card.findChild(QLabel, "value_label").setText(str(total_customers))

        self.cursor.execute("SELECT SUM(balance) FROM customers WHERE user_id = ? AND balance < 0", (self.current_user,))
        pending_payments = self.cursor.fetchone()[0] or 0.0
        self.pending_payments_card.findChild(QLabel, "value_label").setText(f"{self.get_currency_symbol()}{abs(pending_payments):.2f}")

        self.cursor.execute("SELECT date, c.name, type, amount, description FROM transactions t JOIN customers c ON t.customer_id = c.id WHERE t.user_id = ? ORDER BY date DESC LIMIT 5", (self.current_user,))
        recent_transactions = self.cursor.fetchall()
        self.recent_transactions_card.findChild(QLabel, "value_label").setText(str(len(recent_transactions)))
        self.recent_transactions_table.setRowCount(0)
        for row, trans in enumerate(recent_transactions):
            self.recent_transactions_table.insertRow(row)
            for col, data in enumerate(trans):
                self.recent_transactions_table.setItem(row, col, QTableWidgetItem(str(data)))

        self.cursor.execute("SELECT COUNT(*) FROM products WHERE user_id = ?", (self.current_user,))
        total_products = self.cursor.fetchone()[0]
        self.inventory_items_card.findChild(QLabel, "value_label").setText(str(total_products))
        
    def load_customers(self):
        if not self.current_user: return
        current_id = self.customer_combo.currentData()
        self.customer_combo.clear()
        self.report_customer_combo.clear()
        self.customer_combo.addItem("Select a customer", -1)
        self.report_customer_combo.addItem("All Customers", -1)
        self.cursor.execute("SELECT id, name, balance FROM customers WHERE user_id = ? ORDER BY name", (self.current_user,))
        customers = self.cursor.fetchall()
        for cid, name, balance in customers:
            self.customer_combo.addItem(f"{name} (Bal: {self.get_currency_symbol()}{balance:.2f})", cid)
            self.report_customer_combo.addItem(name, cid)
        index = self.customer_combo.findData(current_id)
        if index != -1: self.customer_combo.setCurrentIndex(index)
        self.filter_customers()

    def filter_customers(self):
        if not self.current_user: return
        search_text = self.customer_search.text().strip().lower()
        current_id = self.customer_combo.currentData()
        
        self.customer_combo.clear()
        self.customer_combo.addItem("Select a customer", -1)

        self.cursor.execute("SELECT id, name, balance FROM customers WHERE user_id = ? ORDER BY name", (self.current_user,))
        customers = self.cursor.fetchall()
        for cid, name, balance in customers:
            if search_text in name.lower():
                self.customer_combo.addItem(f"{name} (Bal: {self.get_currency_symbol()}{balance:.2f})", cid)
        
        index = self.customer_combo.findData(current_id)
        if index != -1:
            self.customer_combo.setCurrentIndex(index)
        else:
            if self.customer_combo.count() > 1:
                self.customer_combo.setCurrentIndex(1)
            else:
                self.load_customer_transactions()

    def load_customer_transactions(self):
        cid = self.customer_combo.currentData()
        if not cid or cid == -1:
            self.customer_details_label.setText("Select a customer to view details")
            self.transactions_table.setRowCount(0)
            return
        self.cursor.execute("SELECT name, phone, email, address, balance FROM customers WHERE id = ? AND user_id = ?", (cid, self.current_user))
        details = self.cursor.fetchone()
        if details:
            name, phone, email, address, balance = details
            self.customer_details_label.setText(f"<b>Name:</b> {name}<br><b>Phone:</b> {phone}<br><b>Email:</b> {email or 'N/A'}<br><b>Address:</b> {address or 'N/A'}<br><b>Current Balance:</b> <span style='color:{'red' if balance < 0 else 'green'}; font-weight:bold;'>{self.get_currency_symbol()}{balance:.2f}</span>")
            self.cursor.execute("SELECT id, date, type, amount, description FROM transactions WHERE customer_id = ? AND user_id = ? ORDER BY date DESC", (cid, self.current_user))
            transactions = self.cursor.fetchall()
            self.transactions_table.setRowCount(len(transactions))
            for row, trans in enumerate(transactions):
                final_balance_item = QTableWidgetItem(f"{self.get_currency_symbol()}{balance:.2f}")
                self.transactions_table.setItem(row, 0, QTableWidgetItem(str(trans[0])))
                self.transactions_table.setItem(row, 1, QTableWidgetItem(str(trans[1])))
                self.transactions_table.setItem(row, 2, QTableWidgetItem(str(trans[2])))
                self.transactions_table.setItem(row, 3, QTableWidgetItem(f"{self.get_currency_symbol()}{float(trans[3]):.2f}"))
                self.transactions_table.setItem(row, 4, final_balance_item)
                self.transactions_table.setItem(row, 5, QTableWidgetItem(str(trans[4])))
        else:
            self.customer_details_label.setText("Customer not found.")
            self.transactions_table.setRowCount(0)

    def show_add_customer_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Customer")
        layout = QFormLayout(dialog)
        name_input = QLineEdit()
        layout.addRow("Name:", name_input)
        phone_input = QLineEdit()
        layout.addRow("Phone:", phone_input)
        email_input = QLineEdit()
        layout.addRow("Email (Optional):", email_input)
        address_input = QTextEdit()
        address_input.setMaximumHeight(80)
        layout.addRow("Address (Optional):", address_input)
        add_btn = QPushButton("Add Customer")
        add_btn.clicked.connect(lambda: self.add_customer(
            name_input.text(), phone_input.text(), email_input.text(), address_input.toPlainText(), dialog
        ))
        layout.addRow(add_btn)
        dialog.exec_()

    def add_customer(self, name, phone, email, address, dialog):
        if not name or not phone:
            QMessageBox.warning(dialog, "Error", "Name and Phone are required.")
            return
        try:
            self.cursor.execute("INSERT INTO customers (user_id, name, phone, email, address) VALUES (?, ?, ?, ?, ?)",
                                (self.current_user, name, phone, email, address))
            self.conn.commit()
            QMessageBox.information(dialog, "Success", "Customer added successfully!")
            self.load_customers()
            self.load_dashboard_data()
            dialog.accept()
        except Exception as e:
            QMessageBox.warning(dialog, "Error", f"Failed to add customer: {e}")

    def show_add_transaction_dialog(self, t_type="debit"):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Add {t_type.capitalize()} Transaction")
        layout = QFormLayout(dialog)
        
        customer_combo = QComboBox()
        self.cursor.execute("SELECT id, name FROM customers WHERE user_id = ?", (self.current_user,))
        customers = self.cursor.fetchall()
        if not customers:
            QMessageBox.warning(self, "Error", "Please add a customer first.")
            return
        for cid, name in customers:
            customer_combo.addItem(name, cid)
        layout.addRow("Customer:", customer_combo)
        
        amount_input = QLineEdit()
        amount_input.setValidator(QtGui.QDoubleValidator(0.00, 9999999.99, 2))
        layout.addRow("Amount:", amount_input)
        
        date_input = QDateEdit(QDate.currentDate())
        date_input.setCalendarPopup(True)
        layout.addRow("Date:", date_input)
        
        desc_input = QTextEdit()
        desc_input.setMaximumHeight(80)
        layout.addRow("Description:", desc_input)
        
        add_btn = QPushButton(f"Add {t_type.capitalize()}")
        add_btn.clicked.connect(lambda: self.add_transaction(
            customer_combo.currentData(), amount_input.text(), t_type,
            date_input.date().toString(Qt.ISODate), desc_input.toPlainText(), dialog
        ))
        layout.addRow(add_btn)
        dialog.exec_()

    def show_add_credit_dialog(self):
        self.show_add_transaction_dialog("credit")

    def show_add_debit_dialog(self):
        self.show_add_transaction_dialog("debit")
        
    def add_transaction(self, customer_id, amount_str, transaction_type, date, description, dialog):
        if not customer_id or not amount_str:
            QMessageBox.warning(dialog, "Error", "Please select a customer and enter an amount.")
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                QMessageBox.warning(dialog, "Error", "Amount must be positive.")
                return

            self.cursor.execute("SELECT balance FROM customers WHERE id = ?", (customer_id,))
            current_balance = self.cursor.fetchone()[0]
            new_balance = current_balance + amount if transaction_type == 'credit' else current_balance - amount
            
            self.cursor.execute("UPDATE customers SET balance = ? WHERE id = ?", (new_balance, customer_id))
            self.cursor.execute("INSERT INTO transactions (user_id, customer_id, amount, type, date, description) VALUES (?, ?, ?, ?, ?, ?)",
                                (self.current_user, customer_id, amount, transaction_type, date, description))
            self.conn.commit()

            QMessageBox.information(dialog, "Success", f"{transaction_type.capitalize()} transaction added!")
            self.load_customers()
            self.load_dashboard_data()
            dialog.accept()
        except ValueError:
            QMessageBox.warning(dialog, "Error", "Invalid amount entered.")
        except Exception as e:
            self.conn.rollback()
            QMessageBox.warning(dialog, "Error", f"Failed to add transaction: {e}")

    def get_currency_symbol(self):
        if not self.current_user: return "₹"
        self.cursor.execute("SELECT currency FROM settings WHERE user_id = ?", (self.current_user,))
        result = self.cursor.fetchone()
        return result[0] if result else "₹"
    
    def apply_style(self):
        base_style = """
            QGroupBox { font-weight: bold; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """
        if self.dark_mode:
            dark_theme = base_style + """
                QMainWindow, QDialog { background-color: #2d2d2d; color: #f0f0f0; }
                QTabWidget::pane { border: 1px solid #454545; background: #3c3c3c; }
                QTabBar::tab { background: #3c3c3c; color: #f0f0f0; border: 1px solid #454545; padding: 8px 15px; }
                QTabBar::tab:selected { background: #0078d7; color: white; }
                QTabBar::tab:hover { background: #4a4a4a; }
                QTableWidget { border: 1px solid #454545; selection-background-color: #0078d7; color: #f0f0f0; background-color: #3c3c3c;}
                QHeaderView::section { background-color: #0078d7; color: white; padding: 5px; border: none; }
                QLineEdit, QTextEdit, QComboBox, QDateEdit { background-color: #4a4a4a; color: #f0f0f0; border: 1px solid #5a5a5a; padding: 5px; border-radius: 3px;}
                QPushButton { background-color: #0078d7; color: white; border: none; padding: 8px 12px; border-radius: 3px; }
                QPushButton:hover { background-color: #005a9e; }
                QLabel { color: #f0f0f0; }
                QGroupBox, QGroupBox::title { color: #f0f0f0; border: 1px solid #454545; }
            """
            self.setStyleSheet(dark_theme)
        else:
            light_theme = base_style + """
                QMainWindow, QDialog { background-color: #f0f0f0; }
                QTabWidget::pane { border: 1px solid #ccc; background: white; }
                QTabBar::tab { background: #e1e1e1; border: 1px solid #ccc; padding: 8px 15px; color: black; }
                QTabBar::tab:selected { background: #0078d7; color: white; }
                QTabBar::tab:hover { background: #cacaca; }
                QTableWidget { border: 1px solid #ccc; selection-background-color: #0078d7; }
                QHeaderView::section { background-color: #0078d7; color: white; padding: 5px; border: none; }
                QLineEdit, QTextEdit, QComboBox, QDateEdit { border: 1px solid #ccc; padding: 5px; border-radius: 3px; }
                QPushButton { background-color: #0078d7; color: white; border: none; padding: 8px 12px; border-radius: 3px; }
                QPushButton:hover { background-color: #005a9e; }
                QLabel { color: black; }
                QGroupBox, QGroupBox::title { color: black; border: 1px solid #ccc; }
            """
            self.setStyleSheet(light_theme)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.apply_style()
        self.save_settings()
        
    def save_settings(self):
        if not self.current_user:
            return

        currency = self.currency_combo.currentText().split(" ")[0]
        sms_notifications = 1 if self.notify_check.isChecked() else 0
        dark_mode_setting = 1 if self.dark_mode else 0
        business_name = self.business_name_input.text()
        phone = self.phone_input.text()
        address = self.address_input.toPlainText()

        try:
            self.cursor.execute("INSERT OR REPLACE INTO settings (user_id, currency, sms_notifications, dark_mode) VALUES (?, ?, ?, ?)",
                                (self.current_user, currency, sms_notifications, dark_mode_setting))
            self.cursor.execute("UPDATE users SET business_name = ?, phone = ?, address = ? WHERE id = ?",
                                (business_name, phone, address, self.current_user))
            self.conn.commit()
            
            sender = self.sender()
            if sender and sender.text() == "Save Settings":
                 QMessageBox.information(self, "Success", "Settings saved successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")

    def load_settings(self):
        if not self.current_user: return
        self.cursor.execute("SELECT currency, sms_notifications, dark_mode FROM settings WHERE user_id = ?", (self.current_user,))
        settings = self.cursor.fetchone()
        if settings:
            currency, sms, dark = settings
            index = self.currency_combo.findText(currency, QtCore.Qt.MatchStartsWith)
            if index != -1: self.currency_combo.setCurrentIndex(index)
            self.notify_check.setChecked(bool(sms))
            self.dark_mode = bool(dark)
            self.apply_style()
        
        self.cursor.execute("SELECT business_name, phone, address FROM users WHERE id = ?", (self.current_user,))
        user_info = self.cursor.fetchone()
        if user_info:
            self.business_name_input.setText(user_info[0])
            self.phone_input.setText(user_info[1])
            self.address_input.setText(user_info[2])
        
        logo_path = f"user_logo_{self.current_user}.png"
        if QtCore.QFile.exists(logo_path):
            self.logo_path.setText(logo_path)
            pixmap = QPixmap(logo_path)
            self.logo_preview.setPixmap(pixmap.scaled(self.logo_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_path.clear()
            self.logo_preview.clear()

    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Image Files (*.png *.jpg)")
        if file_path:
            try:
                destination_path = f"user_logo_{self.current_user}.png"
                shutil.copyfile(file_path, destination_path)
                self.logo_path.setText(destination_path)
                pixmap = QPixmap(destination_path)
                self.logo_preview.setPixmap(pixmap.scaled(self.logo_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                QMessageBox.information(self, "Success", "Logo updated!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load logo: {e}")

    def backup_data(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Backup Database", "smartlygo_backup.db", "SQLite Database (*.db)")
        if file_path:
            try:
                shutil.copyfile("smartlygo.db", file_path)
                QMessageBox.information(self, "Success", f"Database backed up to {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to backup database: {e}")

    def restore_data(self):
        reply = QMessageBox.question(self, "Confirm Restore", "This will overwrite current data. Continue?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Restore Database", "", "SQLite Database (*.db)")
        if file_path:
            try:
                self.conn.close()
                shutil.copyfile(file_path, "smartlygo.db")
                self.conn = sqlite3.connect("smartlygo.db")
                self.cursor = self.conn.cursor()
                self.load_dashboard_data()
                self.load_customers()
                self.load_products()
                self.load_settings()
                QMessageBox.information(self, "Success", "Database restored successfully!")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to restore database: {e}")

    def show_add_product_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Product")
        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        layout.addRow("Name:", name_input)
        
        price_input = QLineEdit()
        price_input.setValidator(QtGui.QDoubleValidator(0.00, 9999999.99, 2))
        layout.addRow("Price:", price_input)

        quantity_input = QLineEdit()
        quantity_input.setValidator(QtGui.QIntValidator(0, 9999999))
        layout.addRow("Quantity:", quantity_input)
        
        category_combo = QComboBox()
        self.cursor.execute("SELECT DISTINCT category FROM products WHERE user_id = ? AND category IS NOT NULL AND category != ''", (self.current_user,))
        categories = [row[0] for row in self.cursor.fetchall()]
        category_combo.addItems([""] + categories)
        category_combo.setEditable(True)
        category_combo.setInsertPolicy(QComboBox.NoInsert)
        layout.addRow("Category:", category_combo)

        barcode_input = QLineEdit()
        layout.addRow("Barcode (Optional):", barcode_input)

        add_btn = QPushButton("Add Product")
        add_btn.clicked.connect(lambda: self.add_product(
            name_input.text(), price_input.text(), quantity_input.text(),
            category_combo.currentText(), barcode_input.text(), dialog
        ))
        layout.addRow(add_btn)
        dialog.exec_()

    def add_product(self, name, price_str, quantity_str, category, barcode, dialog):
        if not (name and price_str and quantity_str):
            QMessageBox.warning(dialog, "Error", "Name, Price, and Quantity are required.")
            return
        try:
            price = float(price_str)
            quantity = int(quantity_str)
            if price <= 0 or quantity < 0:
                QMessageBox.warning(dialog, "Error", "Price must be positive and quantity non-negative.")
                return

            self.cursor.execute("INSERT INTO products (user_id, name, price, quantity, category, barcode) VALUES (?, ?, ?, ?, ?, ?)",
                                (self.current_user, name, price, quantity, category, barcode))
            self.conn.commit()
            QMessageBox.information(dialog, "Success", "Product added successfully!")
            self.load_products()
            self.load_categories()
            self.load_dashboard_data()
            dialog.accept()
        except ValueError:
            QMessageBox.warning(dialog, "Error", "Invalid price or quantity.")
        except Exception as e:
            QMessageBox.warning(dialog, "Error", f"Failed to add product: {e}")

    def edit_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a product to edit.")
            return

        product_id = int(self.products_table.item(selected_row, 0).text())
        
        self.cursor.execute("SELECT name, price, quantity, category, barcode FROM products WHERE id=?", (product_id,))
        p_data = self.cursor.fetchone()
        if not p_data:
            QMessageBox.warning(self, "Error", "Could not retrieve product data.")
            return
        current_name, current_price, current_quantity, current_category, current_barcode = p_data

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Product")
        layout = QFormLayout(dialog)

        name_input = QLineEdit(current_name)
        layout.addRow("Name:", name_input)
        
        price_input = QLineEdit(str(current_price))
        price_input.setValidator(QtGui.QDoubleValidator(0.00, 9999999.99, 2))
        layout.addRow("Price:", price_input)

        quantity_input = QLineEdit(str(current_quantity))
        quantity_input.setValidator(QtGui.QIntValidator(0, 9999999))
        layout.addRow("Quantity:", quantity_input)

        category_combo = QComboBox()
        self.cursor.execute("SELECT DISTINCT category FROM products WHERE user_id = ? AND category IS NOT NULL AND category != ''", (self.current_user,))
        categories = [row[0] for row in self.cursor.fetchall()]
        category_combo.addItems([""] + categories)
        category_combo.setEditable(True)
        category_combo.setInsertPolicy(QComboBox.NoInsert)
        category_combo.setCurrentText(current_category)
        layout.addRow("Category:", category_combo)

        barcode_input = QLineEdit(current_barcode)
        layout.addRow("Barcode (Optional):", barcode_input)

        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(lambda: self.update_product(
            product_id, name_input.text(), price_input.text(), quantity_input.text(),
            category_combo.currentText(), barcode_input.text(), dialog
        ))
        layout.addRow(save_btn)
        dialog.exec_()

    def update_product(self, product_id, name, price_str, quantity_str, category, barcode, dialog):
        if not (name and price_str and quantity_str):
            QMessageBox.warning(dialog, "Error", "Name, Price, and Quantity are required.")
            return
        try:
            price = float(price_str)
            quantity = int(quantity_str)
            if price <= 0 or quantity < 0:
                QMessageBox.warning(dialog, "Error", "Price must be positive and quantity non-negative.")
                return

            self.cursor.execute("UPDATE products SET name=?, price=?, quantity=?, category=?, barcode=? WHERE id=?",
                                (name, price, quantity, category, barcode, product_id))
            self.conn.commit()
            QMessageBox.information(dialog, "Success", "Product updated successfully!")
            self.load_products()
            self.load_categories()
            dialog.accept()
        except ValueError:
            QMessageBox.warning(dialog, "Error", "Invalid price or quantity.")
        except Exception as e:
            QMessageBox.warning(dialog, "Error", f"Failed to update product: {e}")

    def delete_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a product to delete.")
            return

        product_id = int(self.products_table.item(selected_row, 0).text())
        product_name = self.products_table.item(selected_row, 1).text()

        reply = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete '{product_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
                self.conn.commit()
                QMessageBox.information(self, "Success", "Product deleted.")
                self.load_products()
                self.load_dashboard_data()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete product: {e}")

    def generate_product_qr(self):
        selected_row = self.products_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a product to generate a QR code.")
            return

        product_name = self.products_table.item(selected_row, 1).text()
        product_price = self.products_table.item(selected_row, 2).text()
        product_barcode = self.products_table.item(selected_row, 5).text()
        
        qr_data = f"Product: {product_name}\nPrice: {product_price}\nBarcode: {product_barcode or 'N/A'}"
        img = qrcode.make(qr_data)

        file_path, _ = QFileDialog.getSaveFileName(self, "Save QR Code", f"{product_name}_QR.png", "PNG Images (*.png)")
        if file_path:
            try:
                img.save(file_path)
                QMessageBox.information(self, "Success", f"QR code saved to {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save QR code: {e}")

    def generate_payment_qr(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Generate Payment QR")
        layout = QFormLayout(dialog)
        
        amount_input = QLineEdit()
        amount_input.setPlaceholderText("Leave empty for general QR")
        amount_input.setValidator(QtGui.QDoubleValidator(0.00, 9999999.99, 2))
        layout.addRow("Amount (Optional):", amount_input)

        qr_display_label = QLabel()
        qr_display_label.setAlignment(Qt.AlignCenter)
        layout.addRow(qr_display_label)

        generate_btn = QPushButton("Generate QR")
        generate_btn.clicked.connect(lambda: self._generate_payment_qr_internal(amount_input.text(), qr_display_label))
        layout.addRow(generate_btn)
        
        dialog.exec_()

    def _generate_payment_qr_internal(self, amount_str, qr_label):
        self.cursor.execute("SELECT business_name FROM users WHERE id=?", (self.current_user,))
        business_name_tuple = self.cursor.fetchone()
        if not business_name_tuple:
            QMessageBox.warning(qr_label.parent(), "Error", "Business name not found.")
            return
            
        business_name = business_name_tuple[0]
        payment_info = f"Pay to: {business_name}"
        if amount_str:
            try:
                amount = float(amount_str)
                payment_info += f"\nAmount: {self.get_currency_symbol()}{amount:.2f}"
            except ValueError:
                QMessageBox.warning(qr_label.parent(), "Invalid Amount", "Please enter a valid number.")
                return
        
        img = qrcode.make(payment_info)
        
        qt_image = QImage(img.convert('RGBA').tobytes('raw', 'RGBA'), img.size[0], img.size[1], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qt_image)
        qr_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
        
    def print_customer_statement(self):
        cid = self.customer_combo.currentData()
        if not cid or cid == -1:
            QMessageBox.warning(self, "Error", "Please select a customer to generate a statement.")
            return
        
        self.cursor.execute("SELECT name, phone, email, address, balance FROM customers WHERE id = ?", (cid,))
        details = self.cursor.fetchone()
        if not details: return
        
        name, phone, email, address, final_balance = details
        
        self.cursor.execute("SELECT date, type, amount, description FROM transactions WHERE customer_id = ? ORDER BY date ASC", (cid,))
        transactions = self.cursor.fetchall()
        
        statement_content = f"--- Statement for {name} ---\n\n"
        statement_content += f"Phone: {phone or 'N/A'}\nEmail: {email or 'N/A'}\n"
        statement_content += f"----------------------------------------------------------------\n"
        statement_content += f"{'Date':<12} | {'Type':<8} | {'Amount':>15} | {'Balance':>15} | Description\n"
        statement_content += f"----------------------------------------------------------------\n"

        total_change = sum(amount if t_type == 'credit' else -amount for _, t_type, amount, _ in transactions)
        opening_balance = final_balance - total_change
        running_balance = opening_balance

        statement_content += f"{'':<12} | {'':<8} | {'':>15} | {self.get_currency_symbol()}{running_balance: >14.2f} | Opening Balance\n"

        for date, trans_type, amount, description in transactions:
            running_balance += amount if trans_type == 'credit' else -amount
            statement_content += (
                f"{date:<12} | {trans_type.capitalize():<8} | "
                f"{self.get_currency_symbol()}{amount: >14.2f} | "
                f"{self.get_currency_symbol()}{running_balance: >14.2f} | "
                f"{description or 'N/A'}\n"
            )

        statement_content += f"----------------------------------------------------------------\n"
        statement_content += f"Final Balance: {self.get_currency_symbol()}{final_balance:.2f}\n"
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Statement for {name}")
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit(statement_content)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Monospace"))
        layout.addWidget(text_edit)
        dialog.exec_()
        
    def load_products(self):
        if not self.current_user: return
        search_text = self.product_search.text().strip()
        category = self.category_filter.currentData()
        
        query = "SELECT id, name, price, quantity, category, barcode FROM products WHERE user_id = ?"
        params = [self.current_user]
        
        if search_text:
            query += " AND (name LIKE ? OR barcode LIKE ?)"
            params.extend([f"%{search_text}%"] * 2)
        if category:
            query += " AND category = ?"
            params.append(category)
            
        self.cursor.execute(query, tuple(params))
        products = self.cursor.fetchall()
        
        self.products_table.setRowCount(len(products))
        for row_idx, product in enumerate(products):
            for col_idx, data in enumerate(product):
                item_text = str(data) if data is not None else ""
                if col_idx == 2: item_text = f"{self.get_currency_symbol()}{float(data):.2f}"
                self.products_table.setItem(row_idx, col_idx, QTableWidgetItem(item_text))
        
        self.load_low_stock_items()

    def filter_products(self): self.load_products()
    def load_categories(self):
        if not self.current_user: return
        current_cat = self.category_filter.currentData()
        self.category_filter.clear()
        self.category_filter.addItem("All Categories", "")
        self.cursor.execute("SELECT DISTINCT category FROM products WHERE user_id=? AND category IS NOT NULL AND category != '' ORDER BY category", (self.current_user,))
        categories = [row[0] for row in self.cursor.fetchall()]
        for cat in categories: self.category_filter.addItem(cat, cat)
        index = self.category_filter.findData(current_cat)
        if index != -1: self.category_filter.setCurrentIndex(index)

    def load_low_stock_items(self):
        if not self.current_user: return
        self.cursor.execute("SELECT name, price, quantity, category FROM products WHERE user_id=? AND quantity < 10 ORDER BY quantity ASC", (self.current_user,))
        low_stock = self.cursor.fetchall()
        
        self.low_stock_table.setRowCount(len(low_stock))
        for row_idx, product in enumerate(low_stock):
            for col_idx, data in enumerate(product):
                item_text = str(data) if data is not None else ""
                if col_idx == 1: item_text = f"{self.get_currency_symbol()}{float(data):.2f}"
                self.low_stock_table.setItem(row_idx, col_idx, QTableWidgetItem(item_text))

    def generate_report(self):
        report_type = self.report_type_combo.currentText()
        date_from = self.date_from.date().toString(Qt.ISODate)
        date_to = self.date_to.date().toString(Qt.ISODate)
        customer_id = self.report_customer_combo.currentData()
        if customer_id == -1: customer_id = None
        
        report_content = f"--- {report_type} Report ({date_from} to {date_to}) ---\n\n"
        
        if report_type == "Daily Sales":
            report_content += self._generate_daily_sales_report(date_from, date_to)
        elif report_type == "Customer Ledger":
            if customer_id:
                report_content += self._generate_customer_ledger_report(customer_id, date_from, date_to)
            else:
                report_content += "Please select a customer for this report."
        elif report_type == "Transaction Summary":
            report_content += self._generate_transaction_summary_report(date_from, date_to)
        elif report_type == "Customer Balances":
            report_content += self._generate_customer_balances_report()
        else: 
            report_content += "This report type is under development."
            
        self.report_text.setText(report_content)

    def _generate_daily_sales_report(self, date_from, date_to):
        query = """
            SELECT date, 
                   SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END),
                   SUM(CASE WHEN type = 'debit' THEN amount ELSE 0 END)
            FROM transactions WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY date ORDER BY date ASC
        """
        self.cursor.execute(query, (self.current_user, date_from, date_to))
        results = self.cursor.fetchall()
        if not results: return "No data for this period."

        header = f"{'Date':<12} | {'Sales':>15} | {'Returns/Debits':>15}\n" + "-"*47
        rows = [f"{date:<12} | {self.get_currency_symbol()}{sales or 0:>14.2f} | {self.get_currency_symbol()}{returns or 0:>14.2f}" for date, sales, returns in results]
        return header + "\n" + "\n".join(rows)

    def _generate_customer_ledger_report(self, customer_id, date_from, date_to):
        self.cursor.execute("SELECT name FROM customers WHERE id=?", (customer_id,))
        customer_name = self.cursor.fetchone()[0]
        
        query = "SELECT date, type, amount, description FROM transactions WHERE customer_id=? AND date BETWEEN ? AND ? ORDER BY date ASC"
        self.cursor.execute(query, (customer_id, date_from, date_to))
        results = self.cursor.fetchall()
        if not results: return f"No transactions for {customer_name} in this period."
        
        header = f"Ledger for {customer_name}\n" + "-"*60 + f"\n{'Date':<12} | {'Type':<8} | {'Amount':>15} | Description\n" + "-"*60
        rows = [f"{date:<12} | {t_type.capitalize():<8} | {self.get_currency_symbol()}{amount:>14.2f} | {desc or 'N/A'}" for date, t_type, amount, desc in results]
        return header + "\n" + "\n".join(rows)

    def _generate_transaction_summary_report(self, date_from, date_to):
        query = """
            SELECT type, COUNT(id), SUM(amount) FROM transactions
            WHERE user_id = ? AND date BETWEEN ? AND ? GROUP BY type
        """
        self.cursor.execute(query, (self.current_user, date_from, date_to))
        results = self.cursor.fetchall()
        if not results: return "No transactions in this period."

        header = f"{'Type':<10} | {'Count':>10} | {'Total Amount':>20}\n" + "-"*47
        rows = [f"{t_type.capitalize():<10} | {count:>10} | {self.get_currency_symbol()}{total or 0:>19.2f}" for t_type, count, total in results]
        return header + "\n" + "\n".join(rows)

    def _generate_customer_balances_report(self):
        self.cursor.execute("SELECT name, phone, balance FROM customers WHERE user_id=? ORDER BY name", (self.current_user,))
        results = self.cursor.fetchall()
        if not results: return "No customers found."
        
        header = f"{'Customer Name':<20} | {'Phone':<15} | {'Balance':>15}\n" + "-"*55
        rows = [f"{name:<20} | {phone:<15} | {self.get_currency_symbol()}{balance:>14.2f}" for name, phone, balance in results]
        return header + "\n" + "\n".join(rows)
    
    def export_to_csv(self):
        report_text = self.report_text.toPlainText()
        if not report_text or "---" not in report_text:
            QMessageBox.warning(self, "No Report", "Please generate a report first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Report", "report.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                lines = report_text.split('\n')
                data_started = False
                data_to_write = []
                for line in lines:
                    if '---' in line and not data_started:
                        data_started = True
                        header = [h.strip() for h in prev_line.split('|')]
                        data_to_write.append(header)
                        continue
                    if data_started and '|' in line:
                        row = [d.strip() for d in line.split('|')]
                        data_to_write.append(row)
                    prev_line = line
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(data_to_write)
                QMessageBox.information(self, "Success", f"Report saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save CSV: {e}")

    def export_to_pdf(self):
        report_text = self.report_text.toPlainText()
        if not report_text or "---" not in report_text:
            QMessageBox.warning(self, "No Report", "Please generate a report first.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "report.pdf", "PDF Files (*.pdf)")
        if file_path:
            try:
                doc = SimpleDocTemplate(file_path)
                styles = getSampleStyleSheet()
                style = styles["Code"]
                story = [Paragraph(line.replace(" ", "&nbsp;"), style) for line in report_text.split('\n')]
                doc.build(story)
                QMessageBox.information(self, "Success", f"PDF report saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save PDF. Ensure 'reportlab' is installed (`pip install reportlab`).\nError: {e}")

    def export_to_excel(self):
        report_text = self.report_text.toPlainText()
        if not report_text or "---" not in report_text:
            QMessageBox.warning(self, "No Report", "Please generate a report first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Excel Report", "report.xlsx", "Excel Files (*.xlsx)")
        if file_path:
            try:
                workbook = openpyxl.Workbook()
                sheet = workbook.active
                
                lines = report_text.split('\n')
                data_started = False
                for line in lines:
                    if '---' in line and not data_started:
                        data_started = True
                        header = [h.strip() for h in prev_line.split('|')]
                        sheet.append(header)
                        continue
                    if data_started and '|' in line:
                        row = [d.strip() for d in line.split('|')]
                        sheet.append(row)
                    prev_line = line
                    
                workbook.save(file_path)
                QMessageBox.information(self, "Success", f"Excel report saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save Excel file. Ensure 'openpyxl' is installed (`pip install openpyxl`).\nError: {e}")

    def print_report(self):
        report_text = self.report_text.toPlainText()
        if not report_text or "---" not in report_text:
            QMessageBox.warning(self, "No Report", "Please generate a report first.")
            return

        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec_() == QDialog.Accepted:
            self.report_text.print_(printer)

    def generate_chart(self):
        for i in reversed(range(self.chart_layout.count())):
            self.chart_layout.itemAt(i).widget().setParent(None)

        chart_type = self.chart_type_combo.currentText()
        date_from = self.viz_date_from.date().toString(Qt.ISODate)
        date_to = self.viz_date_to.date().toString(Qt.ISODate)

        fig, ax = plt.subplots()
        
        if self.dark_mode:
            fig.patch.set_facecolor('#2d2d2d')
            ax.set_facecolor('#3c3c3c')
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white') 
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
            ax.yaxis.label.set_color('white')
            ax.xaxis.label.set_color('white')
            ax.title.set_color('white')

        if chart_type == "Sales Trend":
            self._plot_sales_trend(ax, date_from, date_to)
        elif chart_type == "Customer Balances":
            self._plot_customer_balances(ax)
        elif chart_type == "Product Categories":
            self._plot_product_categories(ax)
        elif chart_type == "Transaction Types":
            self._plot_transaction_types(ax, date_from, date_to)
        elif chart_type == "Monthly Summary":
            self._plot_monthly_summary(ax, date_from, date_to)

        canvas = FigureCanvas(fig)
        self.chart_layout.addWidget(canvas)

    def _plot_sales_trend(self, ax, date_from, date_to):
        query = """
            SELECT date, SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END),
                   SUM(CASE WHEN type = 'debit' THEN amount ELSE 0 END)
            FROM transactions WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY date ORDER BY date ASC
        """
        self.cursor.execute(query, (self.current_user, date_from, date_to))
        results = self.cursor.fetchall()
        if not results:
            ax.text(0.5, 0.5, "No data to display.", ha='center', va='center', color='gray')
            return

        dates, credits, debits = zip(*results)
        ax.plot(dates, credits, marker='o', linestyle='-', label='Credits')
        ax.plot(dates, debits, marker='x', linestyle='--', label='Debits')
        ax.set_title("Sales Trend")
        ax.set_ylabel(f"Amount ({self.get_currency_symbol()})")
        ax.legend(facecolor=('#3c3c3c' if self.dark_mode else 'white'), edgecolor=('white' if self.dark_mode else 'black'), labelcolor=('white' if self.dark_mode else 'black'))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        fig = ax.get_figure()
        fig.tight_layout()

    def _plot_customer_balances(self, ax):
        self.cursor.execute("SELECT name, balance FROM customers WHERE user_id = ? ORDER BY balance DESC", (self.current_user,))
        results = self.cursor.fetchall()
        if not results:
            ax.text(0.5, 0.5, "No customers to display.", ha='center', va='center', color='gray')
            return

        names, balances = zip(*results)
        colors = ['red' if b < 0 else 'green' for b in balances]
        ax.bar(names, balances, color=colors)
        ax.axhline(0, color='grey', linewidth=0.8)
        ax.set_title("Customer Balances")
        ax.set_ylabel(f"Balance ({self.get_currency_symbol()})")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        fig = ax.get_figure()
        fig.tight_layout()

    def _plot_product_categories(self, ax):
        self.cursor.execute("SELECT category, COUNT(id) FROM products WHERE user_id = ? GROUP BY category", (self.current_user,))
        results = self.cursor.fetchall()
        if not results:
            ax.text(0.5, 0.5, "No products to display.", ha='center', va='center', color='gray')
            return

        labels, sizes = zip(*results)
        text_props = {'color': 'white' if self.dark_mode else 'black'}
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops=text_props)
        ax.axis('equal')
        ax.set_title("Products by Category")
        fig = ax.get_figure()
        fig.tight_layout()

    def _plot_transaction_types(self, ax, date_from, date_to):
        query = "SELECT type, COUNT(id) FROM transactions WHERE user_id=? AND date BETWEEN ? AND ? GROUP BY type"
        self.cursor.execute(query, (self.current_user, date_from, date_to))
        results = self.cursor.fetchall()
        if not results:
            ax.text(0.5, 0.5, "No transactions to display.", ha='center', va='center', color='gray')
            return
            
        types, counts = zip(*results)
        ax.bar(types, counts, color=['#2ecc71', '#e74c3c'])
        ax.set_title("Transaction Types")
        ax.set_ylabel("Number of Transactions")
        fig = ax.get_figure()
        fig.tight_layout()
        
    def _plot_monthly_summary(self, ax, date_from, date_to):
        query = """
            SELECT STRFTIME('%Y-%m', date) as month, 
                   SUM(CASE WHEN type='credit' THEN amount ELSE 0 END),
                   SUM(CASE WHEN type='debit' THEN amount ELSE 0 END)
            FROM transactions WHERE user_id=? AND date BETWEEN ? AND ?
            GROUP BY month ORDER BY month
        """
        self.cursor.execute(query, (self.current_user, date_from, date_to))
        results = self.cursor.fetchall()
        if not results:
            ax.text(0.5, 0.5, "No data to display.", ha='center', va='center', color='gray')
            return
            
        months, credits, debits = zip(*results)
        x = range(len(months))
        ax.bar([i - 0.2 for i in x], credits, 0.4, label='Credits')
        ax.bar([i + 0.2 for i in x], debits, 0.4, label='Debits')
        ax.set_ylabel(f"Amount ({self.get_currency_symbol()})")
        ax.set_title('Monthly Summary')
        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha='right')
        ax.legend(facecolor=('#3c3c3c' if self.dark_mode else 'white'), edgecolor=('white' if self.dark_mode else 'black'), labelcolor=('white' if self.dark_mode else 'black'))
        fig = ax.get_figure()
        fig.tight_layout()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = SmartlyGo()
    window.show()
    sys.exit(app.exec_())
