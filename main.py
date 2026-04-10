import sys
import os
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt
import pymysql


class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        try:
            self.conn = pymysql.connect(
                host='localhost',
                user='root',
                password='250806',
                database='pizzeria_db',
            )
            print("Подключение к БД успешно!")
        except Exception as e:
            QMessageBox.critical(None, "Ошибка подключения", f"Не удалось подключиться к БД:\n{e}")
            sys.exit(1)

    def execute_query(self, query, params=None):
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.conn.commit()
        return cursor

    def fetch_all(self, query, params=None):
        cursor = self.execute_query(query, params)
        result = cursor.fetchall()
        cursor.close()
        return result

    def fetch_one(self, query, params=None):
        cursor = self.execute_query(query, params)
        result = cursor.fetchone()
        cursor.close()
        return result

    def close(self):
        if self.conn:
            self.conn.close()


class AuthManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.current_user = None
        self.role = None

    def login(self, username, password):
        result = self.db.fetch_one(
            """SELECT u.user_id, u.username, r.role_name 
               FROM users u
               JOIN roles r ON u.role_id = r.role_id
               WHERE u.username = %s AND u.password_hash = %s""",
            (username, password)
        )

        if result:
            self.current_user = {'id': result[0], 'username': result[1]}
            self.role = result[2]
            return True
        return False

    def login_as_guest(self):
        self.current_user = {'id': None, 'username': 'Гость'}
        self.role = 'guest'
        return True

    def logout(self):
        self.current_user = None
        self.role = None


class LoginWindow(QDialog):
    def __init__(self, auth_manager):
        super().__init__()
        self.auth = auth_manager
        self.setWindowTitle("Вход в систему - Пиццерия")
        self.setFixedSize(350, 250)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Пиццерия")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Логин")
        self.txt_username.setMinimumHeight(35)
        layout.addWidget(self.txt_username)

        self.txt_password = QLineEdit()
        self.txt_password.setPlaceholderText("Пароль")
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setMinimumHeight(35)
        layout.addWidget(self.txt_password)

        self.btn_login = QPushButton("Войти")
        self.btn_login.setMinimumHeight(40)
        self.btn_login.clicked.connect(self.on_login)
        layout.addWidget(self.btn_login)

        self.btn_guest = QPushButton("Войти как гость")
        self.btn_guest.setMinimumHeight(40)
        self.btn_guest.clicked.connect(self.on_guest)
        layout.addWidget(self.btn_guest)

        self.setLayout(layout)

    def on_login(self):
        username = self.txt_username.text().strip()
        password = self.txt_password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        if self.auth.login(username, password):
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль!")

    def on_guest(self):
        self.auth.login_as_guest()
        self.accept()


class MenuWidget(QWidget):
    def __init__(self, db_manager, auth_manager=None, can_order=True):
        super().__init__()
        self.db = db_manager
        self.auth = auth_manager
        self.can_order = can_order
        self.cart = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.menu_container = QWidget()
        self.grid_layout = QGridLayout(self.menu_container)
        self.grid_layout.setSpacing(15)

        self.load_menu()

        scroll.setWidget(self.menu_container)
        layout.addWidget(scroll)

        if self.can_order:
            self.cart_label = QLabel("Корзина пуста")
            self.cart_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            layout.addWidget(self.cart_label)

            self.btn_cart = QPushButton("Корзина")
            self.btn_cart.setMinimumHeight(45)
            self.btn_cart.clicked.connect(self.show_cart)
            layout.addWidget(self.btn_cart)

        self.setLayout(layout)

    def load_menu(self):
        items = self.db.fetch_all("SELECT * FROM menu_items")

        row = col = 0
        for item in items:
            item_id, name, desc, price, category, img_path, tech = item

            card = QGroupBox(name)
            card_layout = QVBoxLayout(card)

            img_label = QLabel()
            if img_path and os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio)
                img_label.setPixmap(pixmap)
            else:
                img_label.setText("Нет фото")
                img_label.setMinimumHeight(150)
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(img_label)

            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            card_layout.addWidget(desc_label)

            price_label = QLabel(f"<b>{price} ₽</b>")
            price_label.setStyleSheet("color: #2ecc71; font-size: 16px;")
            card_layout.addWidget(price_label)

            cat_label = QLabel(f"Категория: {category}")
            cat_label.setStyleSheet("color: gray;")
            card_layout.addWidget(cat_label)

            if self.can_order:
                btn_add = QPushButton("Добавить в корзину")
                btn_add.clicked.connect(lambda checked, iid=item_id, n=name, p=price:
                                        self.add_to_cart(iid, n, p))
                card_layout.addWidget(btn_add)

            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def add_to_cart(self, item_id, name, price):
        if item_id in self.cart:
            self.cart[item_id]['qty'] += 1
        else:
            self.cart[item_id] = {'name': name, 'price': float(price), 'qty': 1}
        self.update_cart_label()

    def update_cart_label(self):
        total_items = sum(item['qty'] for item in self.cart.values())
        total_price = sum(item['price'] * item['qty'] for item in self.cart.values())
        self.cart_label.setText(f"Корзина: {total_items} тов. на сумму {total_price:.2f} ₽")

    def show_cart(self):
        if not self.cart:
            QMessageBox.information(self, "Корзина", "Корзина пуста!")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Корзина")
        dialog.setMinimumWidth(600)

        main_layout = QVBoxLayout(dialog)

        # Таблица корзины
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Блюдо", "Цена за шт.", "Количество", "Сумма"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Метка с итоговой суммой (для автоматического обновления)
        self.total_label = QLabel("Итого: 0.00 ₽")
        self.total_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.total_label.setStyleSheet("color: #2ecc71; padding: 10px;")

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_order = QPushButton("Оформить заказ")
        btn_order.setMinimumHeight(40)
        btn_order.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        btn_order.clicked.connect(lambda: self.checkout(dialog, self.calculate_total()))

        btn_close = QPushButton("Закрыть")
        btn_close.setMinimumHeight(40)
        btn_close.clicked.connect(dialog.close)

        btn_layout.addWidget(btn_order)
        btn_layout.addWidget(btn_close)

        main_layout.addWidget(table)
        main_layout.addWidget(self.total_label)
        main_layout.addLayout(btn_layout)

        # Обновляем таблицу и сохраняем ссылки на спинбоксы
        self.cart_table = table
        self.update_cart_table()

        dialog.exec()

    def calculate_total(self):
        """Вычисление общей суммы корзины"""
        return sum(item['price'] * item['qty'] for item in self.cart.values())

    def update_cart_table(self):
        """Обновление таблицы корзины с автоматическим пересчетом"""
        self.cart_table.setRowCount(len(self.cart))
        total = 0

        for i, (item_id, item) in enumerate(self.cart.items()):
            subtotal = item['price'] * item['qty']
            total += subtotal

            self.cart_table.setItem(i, 0, QTableWidgetItem(str(item_id)))
            self.cart_table.setItem(i, 1, QTableWidgetItem(item['name']))
            self.cart_table.setItem(i, 2, QTableWidgetItem(f"{item['price']:.2f} ₽"))

            # Создаем спинбокс для количества
            spin = QSpinBox()
            spin.setMinimum(1)
            spin.setMaximum(99)
            spin.setValue(item['qty'])
            spin.setStyleSheet("font-size: 14px; padding: 5px;")

            spin.valueChanged.connect(lambda v, iid=item_id: self.on_quantity_changed(iid, v))
            self.cart_table.setCellWidget(i, 3, spin)

            # Ячейка с суммой (будет обновляться автоматически)
            subtotal_item = QTableWidgetItem(f"{subtotal:.2f} ₽")
            subtotal_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.cart_table.setItem(i, 4, subtotal_item)

        # Обновляем итоговую сумму
        self.total_label.setText(f"Итого: {total:.2f} ₽")

    def on_quantity_changed(self, item_id, new_qty):
        """Обработка изменения количества - автоматический пересчет"""
        if item_id in self.cart:
            self.cart[item_id]['qty'] = new_qty

            # Если количество стало 0, удаляем из корзины
            if new_qty == 0:
                del self.cart[item_id]

            # Обновляем таблицу и итоговую сумму
            self.update_cart_table()
            # Также обновляем метку корзины в главном окне
            self.update_cart_label()

    def update_qty(self, item_id, qty):
        """Устаревший метод, теперь используется on_quantity_changed"""
        self.on_quantity_changed(item_id, qty)

    def checkout(self, dialog, total):
        addr, ok = QInputDialog.getText(self, "Адрес доставки",
                                        "Введите адрес (или оставьте пустым для самовывоза):")
        if ok:
            if total <= 0:
                QMessageBox.warning(self, "Ошибка", "Корзина пуста!")
                return

            try:
                user_id = self.auth.current_user['id'] if self.auth and self.auth.current_user else None

                cursor = self.db.conn.cursor()
                cursor.execute("""
                    INSERT INTO orders (user_id, total_amount, delivery_address) 
                    VALUES (%s, %s, %s)
                """, (user_id, total, addr if addr else None))
                order_id = cursor.lastrowid

                for item_id, item in self.cart.items():
                    cursor.execute("""
                        INSERT INTO order_items (order_id, item_id, quantity) 
                        VALUES (%s, %s, %s)
                    """, (order_id, item_id, item['qty']))

                self.db.conn.commit()
                cursor.close()

                QMessageBox.information(self, "Успех", f"Заказ #{order_id} оформлен!\nСумма: {total:.2f} ₽")
                self.cart.clear()
                self.update_cart_label()
                dialog.close()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось оформить заказ: {e}")


class ClientWindow(QMainWindow):
    def __init__(self, db_manager, auth_manager):
        super().__init__()
        self.db = db_manager
        self.auth = auth_manager
        self.setWindowTitle(f"Пиццерия - Клиент: {self.auth.current_user['username']}")
        self.setGeometry(100, 100, 1000, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        tabs = QTabWidget()
        tabs.addTab(MenuWidget(db_manager, auth_manager, can_order=True), "Меню")
        tabs.addTab(self.create_orders_tab(), "Мои заказы")

        layout.addWidget(tabs)

        btn_logout = QPushButton("Выйти")
        btn_logout.clicked.connect(self.logout)
        layout.addWidget(btn_logout)

    def create_orders_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(5)
        self.orders_table.setHorizontalHeaderLabels(["ID", "Статус", "Сумма", "Дата", "Адрес"])
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.load_orders()

        layout.addWidget(self.orders_table)
        return widget

    def load_orders(self):
        orders = self.db.fetch_all("""
            SELECT order_id, status, total_amount, order_date, delivery_address
            FROM orders WHERE user_id = %s ORDER BY order_date DESC
        """, (self.auth.current_user['id'],))

        self.orders_table.setRowCount(len(orders))
        for i, order in enumerate(orders):
            for j, val in enumerate(order):
                self.orders_table.setItem(i, j, QTableWidgetItem(str(val) if val else "-"))

    def logout(self):
        self.auth.logout()
        self.close()


class ManagerWindow(QMainWindow):
    def __init__(self, db_manager, auth_manager):
        super().__init__()
        self.db = db_manager
        self.auth = auth_manager
        self.setWindowTitle(f"Пиццерия - Менеджер: {self.auth.current_user['username']}")
        self.setGeometry(100, 100, 1100, 750)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        tabs = QTabWidget()
        tabs.addTab(self.create_orders_management_tab(), "Управление заказами")
        tabs.addTab(self.create_menu_management_tab(), "Управление меню")

        layout.addWidget(tabs)

        btn_logout = QPushButton("Выйти")
        btn_logout.clicked.connect(self.logout)
        layout.addWidget(btn_logout)

    def create_orders_management_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Фильтр по статусу:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Все", "ожидает приготовления", "готово",
                                     "доставляется", "выдан", "отменен"])
        self.status_filter.currentTextChanged.connect(self.load_all_orders)
        filter_layout.addWidget(self.status_filter)
        layout.addLayout(filter_layout)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(7)
        self.orders_table.setHorizontalHeaderLabels(["ID", "Клиент", "Статус", "Сумма", "Дата", "Адрес", "Действия"])
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.load_all_orders()
        layout.addWidget(self.orders_table)

        return widget

    def load_all_orders(self):
        status = self.status_filter.currentText()

        if status == "Все":
            orders = self.db.fetch_all("""
                SELECT o.order_id, u.username, o.status, o.total_amount, 
                       o.order_date, o.delivery_address
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.user_id
                ORDER BY o.order_date DESC
            """)
        else:
            orders = self.db.fetch_all("""
                SELECT o.order_id, u.username, o.status, o.total_amount, 
                       o.order_date, o.delivery_address
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.user_id
                WHERE o.status = %s
                ORDER BY o.order_date DESC
            """, (status,))

        self.orders_table.setRowCount(len(orders))
        for i, order in enumerate(orders):
            order_id, uname, status, total, date, addr = order

            self.orders_table.setItem(i, 0, QTableWidgetItem(str(order_id)))
            self.orders_table.setItem(i, 1, QTableWidgetItem(uname or "Гость"))
            self.orders_table.setItem(i, 2, QTableWidgetItem(status))
            self.orders_table.setItem(i, 3, QTableWidgetItem(str(total)))
            self.orders_table.setItem(i, 4, QTableWidgetItem(str(date)))
            self.orders_table.setItem(i, 5, QTableWidgetItem(addr or "-"))

            combo = QComboBox()
            combo.addItems(["ожидает приготовления", "готово", "доставляется", "выдан", "отменен"])
            combo.setCurrentText(status)
            combo.currentTextChanged.connect(lambda s, oid=order_id: self.update_order_status(oid, s))
            self.orders_table.setCellWidget(i, 6, combo)

    def update_order_status(self, order_id, new_status):
        self.db.execute_query("UPDATE orders SET status = %s WHERE order_id = %s",
                              (new_status, order_id))
        QMessageBox.information(self, "Успех", f"Статус заказа #{order_id} изменен на '{new_status}'")

    def create_menu_management_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.menu_table = QTableWidget()
        self.menu_table.setColumnCount(6)
        self.menu_table.setHorizontalHeaderLabels(["ID", "Название", "Цена", "Категория", "Описание", "Действия"])
        self.menu_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.load_menu_items()
        layout.addWidget(self.menu_table)

        btn_add = QPushButton("Добавить блюдо")
        btn_add.clicked.connect(self.add_menu_item)
        layout.addWidget(btn_add)

        return widget

    def load_menu_items(self):
        items = self.db.fetch_all("SELECT * FROM menu_items")
        self.menu_table.setRowCount(len(items))

        for i, item in enumerate(items):
            item_id, name, desc, price, cat, img, tech = item

            self.menu_table.setItem(i, 0, QTableWidgetItem(str(item_id)))
            self.menu_table.setItem(i, 1, QTableWidgetItem(name))
            self.menu_table.setItem(i, 2, QTableWidgetItem(str(price)))
            self.menu_table.setItem(i, 3, QTableWidgetItem(cat))
            self.menu_table.setItem(i, 4, QTableWidgetItem(desc))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)

            btn_edit = QPushButton("Изменить")
            btn_edit.clicked.connect(lambda checked, iid=item_id: self.edit_menu_item(iid))
            btn_layout.addWidget(btn_edit)

            btn_del = QPushButton("Удалить")
            btn_del.clicked.connect(lambda checked, iid=item_id: self.delete_menu_item(iid))
            btn_layout.addWidget(btn_del)

            self.menu_table.setCellWidget(i, 5, btn_widget)

    def add_menu_item(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить блюдо")
        layout = QFormLayout(dialog)

        name = QLineEdit()
        desc = QTextEdit()
        desc.setMaximumHeight(80)
        price = QDoubleSpinBox()
        price.setMaximum(9999.99)
        category = QComboBox()
        category.addItems(["pizza", "snack", "salad", "dessert", "drink"])
        img_path = QLineEdit()
        tech = QTextEdit()
        tech.setMaximumHeight(80)

        layout.addRow("Название:", name)
        layout.addRow("Описание:", desc)
        layout.addRow("Цена:", price)
        layout.addRow("Категория:", category)
        layout.addRow("Путь к фото:", img_path)
        layout.addRow("Техкарта:", tech)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.execute_query("""
                INSERT INTO menu_items (name, description, price, category, image_path, tech_card)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name.text(), desc.toPlainText(), price.value(),
                  category.currentText(), img_path.text(), tech.toPlainText()))
            self.load_menu_items()

    def edit_menu_item(self, item_id):
        item = self.db.fetch_one("SELECT * FROM menu_items WHERE item_id = %s", (item_id,))
        if not item:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать блюдо")
        layout = QFormLayout(dialog)

        name = QLineEdit(item[1])
        desc = QTextEdit(item[2])
        desc.setMaximumHeight(80)
        price = QDoubleSpinBox()
        price.setMaximum(9999.99)
        price.setValue(float(item[3]))
        category = QComboBox()
        category.addItems(["pizza", "snack", "salad", "dessert", "drink"])
        category.setCurrentText(item[4])
        img_path = QLineEdit(item[5] or "")
        tech = QTextEdit(item[6] or "")
        tech.setMaximumHeight(80)

        layout.addRow("Название:", name)
        layout.addRow("Описание:", desc)
        layout.addRow("Цена:", price)
        layout.addRow("Категория:", category)
        layout.addRow("Путь к фото:", img_path)
        layout.addRow("Техкарта:", tech)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.execute_query("""
                UPDATE menu_items 
                SET name=%s, description=%s, price=%s, category=%s, image_path=%s, tech_card=%s
                WHERE item_id=%s
            """, (name.text(), desc.toPlainText(), price.value(),
                  category.currentText(), img_path.text(), tech.toPlainText(), item_id))
            self.load_menu_items()

    def delete_menu_item(self, item_id):
        reply = QMessageBox.question(self, "Подтверждение",
                                     "Удалить блюдо?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.execute_query("DELETE FROM menu_items WHERE item_id = %s", (item_id,))
            self.load_menu_items()

    def logout(self):
        self.auth.logout()
        self.close()


class AdminWindow(QMainWindow):
    def __init__(self, db_manager, auth_manager):
        super().__init__()
        self.db = db_manager
        self.auth = auth_manager
        self.setWindowTitle(f"Пиццерия - Администратор: {self.auth.current_user['username']}")
        self.setGeometry(100, 100, 1000, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        tabs = QTabWidget()
        tabs.addTab(self.create_users_tab(), "Пользователи")
        tabs.addTab(self.create_analytics_tab(), "Аналитика")

        layout.addWidget(tabs)

        btn_logout = QPushButton("Выйти")
        btn_logout.clicked.connect(self.logout)
        layout.addWidget(btn_logout)

    def create_users_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["ID", "Логин", "Роль", "Действия"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.load_users()
        layout.addWidget(self.users_table)

        return widget

    def load_users(self):
        users = self.db.fetch_all("""
            SELECT u.user_id, u.username, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
        """)

        self.users_table.setRowCount(len(users))
        for i, (user_id, uname, role) in enumerate(users):
            self.users_table.setItem(i, 0, QTableWidgetItem(str(user_id)))
            self.users_table.setItem(i, 1, QTableWidgetItem(uname))
            self.users_table.setItem(i, 2, QTableWidgetItem(role))

            btn_change = QPushButton("Сменить роль")
            btn_change.clicked.connect(lambda checked, uid=user_id: self.change_user_role(uid))
            self.users_table.setCellWidget(i, 3, btn_change)

    def change_user_role(self, user_id):
        roles = ['guest', 'client', 'manager', 'admin']
        new_role, ok = QInputDialog.getItem(self, "Смена роли",
                                            "Выберите роль:", roles, 0, False)
        if ok:
            role_id = roles.index(new_role) + 1
            self.db.execute_query("UPDATE users SET role_id = %s WHERE user_id = %s",
                                  (role_id, user_id))
            self.load_users()

    def create_analytics_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.analytics_text = QTextEdit()
        self.analytics_text.setReadOnly(True)
        layout.addWidget(self.analytics_text)

        btn_update = QPushButton("Обновить аналитику")
        btn_update.clicked.connect(self.update_analytics)
        layout.addWidget(btn_update)

        self.update_analytics()
        return widget

    def update_analytics(self):
        total_orders = self.db.fetch_one("SELECT COUNT(*) FROM orders")[0]
        total_revenue = self.db.fetch_one("SELECT SUM(total_amount) FROM orders")[0] or 0
        avg_check = total_revenue / total_orders if total_orders > 0 else 0

        report = f"=== АНАЛИТИКА ПИЦЦЕРИИ ===\n\n"
        report += f"Всего заказов: {total_orders}\n"
        report += f"Общая выручка: {total_revenue:.2f} ₽\n"
        report += f"Средний чек: {avg_check:.2f} ₽\n\n"

        report += "Заказы по статусам:\n"
        statuses = self.db.fetch_all("""
            SELECT status, COUNT(*) as cnt 
            FROM orders GROUP BY status
        """)
        for status, cnt in statuses:
            report += f"  {status}: {cnt}\n"

        report += "\nТоп-5 пицц:\n"
        pizzas = self.db.fetch_all("""
            SELECT mi.name, COUNT(oi.item_id) as cnt
            FROM order_items oi
            JOIN menu_items mi ON oi.item_id = mi.item_id
            WHERE mi.category = 'pizza'
            GROUP BY mi.item_id
            ORDER BY cnt DESC
            LIMIT 5
        """)
        for name, cnt in pizzas:
            report += f"  {name}: {cnt} раз\n"

        self.analytics_text.setPlainText(report)

    def logout(self):
        self.auth.logout()
        self.close()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    db = DatabaseManager()
    auth = AuthManager(db)

    login = LoginWindow(auth)
    if login.exec() == QDialog.DialogCode.Accepted:
        if auth.role == 'guest':
            window = QMainWindow()
            window.setWindowTitle("Пиццерия - Гость")
            central = QWidget()
            window.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.addWidget(MenuWidget(db, auth, can_order=False))

            btn_login = QPushButton("Войти")
            btn_login.clicked.connect(lambda: [window.close(), main()])
            layout.addWidget(btn_login)

            window.show()
        elif auth.role == 'client':
            window = ClientWindow(db, auth)
            window.show()
        elif auth.role == 'manager':
            window = ManagerWindow(db, auth)
            window.show()
        elif auth.role == 'admin':
            window = AdminWindow(db, auth)
            window.show()

        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
