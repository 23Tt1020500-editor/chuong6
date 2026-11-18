from datetime import datetime
from .extensions import db

STATUSES = ["Chờ xác nhận", "Đang giao", "Hoàn tất", "Đã huỷ"]
TRANSITIONS = {
    "Chờ xác nhận": ["Đang giao", "Đã huỷ"],
    "Đang giao": ["Hoàn tất", "Đã huỷ"],
    "Hoàn tất": [],
    "Đã huỷ": [],
}


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    books = db.relationship("Book", back_populates="category")


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    publisher = db.Column(db.String(150))
    year = db.Column(db.Integer)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text)
    cover = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    category = db.relationship("Category", back_populates="books")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.String(255), nullable=False)
    note = db.Column(db.String(255))
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Chờ xác nhận")
    shipping_fee = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, nullable=False)  # tạm tính + phí ship
    created_at = db.Column(db.DateTime, default=datetime.now)
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    logs = db.relationship("OrderLog", back_populates="order", order_by="OrderLog.changed_at",
                           cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)  # đơn giá LÚC ĐẶT
    order = db.relationship("Order", back_populates="items")
    book = db.relationship("Book")


class OrderLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.now)
    order = db.relationship("Order", back_populates="logs")