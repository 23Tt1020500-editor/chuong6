import os
import uuid
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for, flash,
                   current_app)
from sqlalchemy import func
from .extensions import db
from .models import Book, Category, Order, OrderItem, OrderLog, STATUSES, TRANSITIONS
from .forms import BookForm, CategoryForm

admin = Blueprint("admin", __name__)      # url_prefix="/admin" đặt ở create_app
LOW = 5


@admin.context_processor
def inject_pending():
    n = db.session.scalar(db.select(func.count(Order.id)).where(Order.status == "Chờ xác nhận"))
    return {"pending_count": n}


def remove_cover(name):
    if name:
        path = os.path.join(current_app.config["UPLOAD_DIR"], name)
        if os.path.exists(path):
            os.remove(path)


@admin.route("/")
def dashboard():
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    n_books = db.session.scalar(db.select(func.count(Book.id)))
    n_pending = db.session.scalar(db.select(func.count(Order.id)).where(Order.status == "Chờ xác nhận"))
    revenue = db.session.scalar(db.select(func.coalesce(func.sum(Order.total), 0))
                                .where(Order.status == "Hoàn tất", Order.created_at >= month_start))
    n_low = db.session.scalar(db.select(func.count(Book.id)).where(Book.stock <= LOW))
    latest = Order.query.order_by(Order.id.desc()).limit(5).all()
    low_books = Book.query.filter(Book.stock <= LOW).order_by(Book.stock).all()

    days = [now.date() - timedelta(days=i) for i in range(6, -1, -1)]
    rev = {d: 0 for d in days}
    done = Order.query.filter(Order.status == "Hoàn tất",
                              Order.created_at >= datetime.combine(days[0], datetime.min.time())).all()
    for o in done:
        if o.created_at.date() in rev:
            rev[o.created_at.date()] += o.total
    chart = [(d, rev[d]) for d in days]
    top = max(rev.values()) or 1
    return render_template("admin/dashboard.html", n_books=n_books, n_pending=n_pending,
                           revenue=revenue, n_low=n_low, latest=latest, low_books=low_books,
                           chart=chart, top=top, month=now.month, low=LOW)


@admin.route("/books")
def books():
    page = request.args.get("page", 1, type=int)
    kw = request.args.get("q", "").strip()
    cat = request.args.get("category", type=int)
    stock = request.args.get("stock", "")
    q = Book.query
    if kw:
        q = q.filter(db.or_(Book.title.ilike(f"%{kw}%"), Book.author.ilike(f"%{kw}%")))
    if cat:
        q = q.filter(Book.category_id == cat)
    if stock == "in":
        q = q.filter(Book.stock > 0)
    elif stock == "low":
        q = q.filter(Book.stock <= LOW)
    elif stock == "out":
        q = q.filter(Book.stock == 0)
    pagination = q.order_by(Book.id.desc()).paginate(page=page, per_page=5, error_out=False)
    ordered = {r[0] for r in db.session.query(OrderItem.book_id).distinct()}
    return render_template("admin/books.html", pagination=pagination, kw=kw, cat=cat, stock=stock,
                           ordered=ordered, categories=Category.query.order_by(Category.name).all(),
                           total_books=Book.query.count())


@admin.post("/books/<int:id>/delete")
def book_delete(id):
    book = db.get_or_404(Book, id)
    if OrderItem.query.filter_by(book_id=id).first():
        flash("Sách đã có trong đơn hàng, không thể xoá.", "danger")
    else:
        remove_cover(book.cover)
        db.session.delete(book)
        db.session.commit()
        flash("Đã xoá sách.", "success")
    return redirect(request.referrer or url_for("admin.books"))


@admin.route("/books/new", methods=["GET", "POST"])
@admin.route("/books/<int:id>/edit", methods=["GET", "POST"])
def book_form(id=None):
    book = db.get_or_404(Book, id) if id else None
    form = BookForm(obj=book, book_id=id)
    if form.validate_on_submit():
        book = book or Book()
        book.title = form.title.data.strip()
        book.author = form.author.data.strip()
        book.publisher = form.publisher.data or None
        book.category_id = form.category_id.data
        book.year = form.year.data
        book.price = form.price.data
        book.stock = form.stock.data
        book.description = form.description.data or None
        f = form.cover.data
        if f is not None and getattr(f, "filename", ""):
            name = uuid.uuid4().hex + os.path.splitext(f.filename)[1].lower()
            f.save(os.path.join(current_app.config["UPLOAD_DIR"], name))
            remove_cover(book.cover)                    # xoá ảnh cũ
            book.cover = name
        db.session.add(book)
        db.session.commit()
        flash("Đã lưu sách.", "success")
        return redirect(url_for("admin.books"))
    return render_template("admin/book_form.html", form=form, book=book)


@admin.route("/categories", methods=["GET", "POST"])
@admin.route("/categories/<int:id>/edit", methods=["GET", "POST"])
def categories(id=None):
    cat = db.get_or_404(Category, id) if id else None
    form = CategoryForm(obj=cat, cat_id=id)
    if form.validate_on_submit():
        cat = cat or Category()
        cat.name = form.name.data.strip()
        cat.description = form.description.data or None
        db.session.add(cat)
        db.session.commit()
        flash("Đã lưu danh mục.", "success")
        return redirect(url_for("admin.categories"))
    rows = (db.session.query(Category, func.count(Book.id))
            .outerjoin(Book, Book.category_id == Category.id)
            .group_by(Category.id).order_by(Category.id).all())
    return render_template("admin/categories.html", rows=rows, form=form, cat=cat)


@admin.post("/categories/<int:id>/delete")
def category_delete(id):
    cat = db.get_or_404(Category, id)
    n = Book.query.filter_by(category_id=id).count()
    if n:
        flash(f'Không thể xoá "{cat.name}": còn {n} sách.', "danger")
    else:
        db.session.delete(cat)
        db.session.commit()
        flash("Đã xoá danh mục.", "success")
    return redirect(url_for("admin.categories"))


@admin.route("/orders")
def orders():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "")
    kw = request.args.get("q", "").strip()
    counts = dict(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    q = Order.query
    if status in STATUSES:
        q = q.filter(Order.status == status)
    if kw:
        like = f"%{kw}%"
        conds = [Order.customer_name.ilike(like), Order.phone.ilike(like)]
        code = kw.lstrip("#")
        if code.isdigit():
            conds.append(Order.id == int(code))
        q = q.filter(db.or_(*conds))
    sum_value = q.with_entities(func.coalesce(func.sum(Order.total), 0)).order_by(None).scalar()
    pagination = q.order_by(Order.id.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template("admin/orders.html", pagination=pagination, counts=counts,
                           total_all=sum(counts.values()), status=status, kw=kw,
                           sum_value=sum_value, statuses=STATUSES)


@admin.route("/orders/<int:id>")
def order_detail(id):
    order = db.get_or_404(Order, id)
    allowed = TRANSITIONS[order.status]
    return render_template("admin/order_detail.html", order=order, allowed=allowed,
                           next_options=[s for s in allowed if s != "Đã huỷ"],
                           subtotal=order.total - (order.shipping_fee or 0))


@admin.post("/orders/<int:id>/status")
def order_status(id):
    order = db.get_or_404(Order, id)
    new = request.form.get("status")
    if new not in TRANSITIONS[order.status]:            # chặn chuyển sai ở SERVER
        flash("Chuyển trạng thái không hợp lệ.", "danger")
    else:
        if new == "Đã huỷ":
            for it in order.items:
                it.book.stock += it.quantity            # hoàn tồn kho
        order.status = new
        order.logs.append(OrderLog(status=new))         # ghi thời điểm
        db.session.commit()
        flash(f"Đã chuyển đơn #{order.id} sang «{new}».", "success")
    return redirect(url_for("admin.order_detail", id=id))