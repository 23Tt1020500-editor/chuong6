import os
from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from sqlalchemy import func
from wtforms import StringField, TextAreaField, RadioField, SelectField, IntegerField
from wtforms.validators import (DataRequired, InputRequired, Optional, Email, Regexp,
                                NumberRange, ValidationError)
from .models import Book, Category

REQ = "Không được để trống."


class CheckoutForm(FlaskForm):
    name = StringField("Họ tên", validators=[DataRequired(REQ)])
    phone = StringField("Số điện thoại", validators=[
        DataRequired(REQ), Regexp(r"^0\d{9}$", message="Số điện thoại gồm 10 chữ số, bắt đầu bằng 0.")])
    email = StringField("Email", validators=[Optional(), Email("Email không đúng định dạng.")])
    address = TextAreaField("Địa chỉ giao hàng", validators=[DataRequired(REQ)])
    note = StringField("Ghi chú")
    payment = RadioField("Thanh toán", default="cod",
                         choices=[("cod", "Tiền mặt khi nhận hàng"), ("bank", "Chuyển khoản")])


class BookForm(FlaskForm):
    title = StringField("Tên sách", validators=[DataRequired(REQ)])
    author = StringField("Tác giả", validators=[DataRequired(REQ)])
    publisher = StringField("Nhà xuất bản")
    category_id = SelectField("Danh mục", coerce=int, validators=[InputRequired(REQ)])
    year = IntegerField("Năm xuất bản", validators=[Optional()])
    price = IntegerField("Giá (đồng)", validators=[
        InputRequired(REQ), NumberRange(min=1000, message="Giá tối thiểu 1.000 đ.")])
    stock = IntegerField("Tồn kho", validators=[
        InputRequired(REQ), NumberRange(min=0, message="Tồn kho không âm.")])
    description = TextAreaField("Mô tả")
    cover = FileField("Ảnh bìa", validators=[
        FileAllowed(["jpg", "jpeg", "png", "webp"], "Chỉ nhận JPG, PNG, WEBP.")])

    def __init__(self, *args, book_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.book_id = book_id
        self.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name)]

    def validate_title(self, field):
        q = Book.query.filter(func.lower(Book.title) == field.data.strip().lower())
        if self.book_id:
            q = q.filter(Book.id != self.book_id)
        if q.first():
            raise ValidationError("Tên sách đã tồn tại.")

    def validate_year(self, field):
        if field.data is not None and not (1900 <= field.data <= datetime.now().year):
            raise ValidationError(f"Năm từ 1900 đến {datetime.now().year}.")

    def validate_cover(self, field):
        f = field.data
        if f is not None and getattr(f, "filename", ""):
            f.stream.seek(0, os.SEEK_END)
            size = f.stream.tell()
            f.stream.seek(0)
            if size > 2 * 1024 * 1024:
                raise ValidationError("Ảnh tối đa 2 MB.")


class CategoryForm(FlaskForm):
    name = StringField("Tên", validators=[DataRequired(REQ)])
    description = TextAreaField("Mô tả")

    def __init__(self, *args, cat_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cat_id = cat_id

    def validate_name(self, field):
        q = Category.query.filter(func.lower(Category.name) == field.data.strip().lower())
        if self.cat_id:
            q = q.filter(Category.id != self.cat_id)
        if q.first():
            raise ValidationError("Danh mục đã tồn tại.")