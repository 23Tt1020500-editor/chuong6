from flask import (Blueprint, render_template, request, session, redirect,
                   url_for, flash)
from .extensions import db
from .models import Book, Category, Order, OrderItem, OrderLog
from .forms import CheckoutForm

shop = Blueprint("shop", __name__)
SHIP_FEE, FREE_SHIP_FROM = 20000, 200000


def get_cart():
    return session.setdefault("cart", {})      # {"book_id": qty}; KHÔNG lưu giá


def cart_lines():
    cart = get_cart()
    ids = [int(i) for i in cart]
    books = Book.query.filter(Book.id.in_(ids)).order_by(Book.id).all() if ids else []
    lines = [{"book": b, "qty": cart[str(b.id)], "total": b.price * cart[str(b.id)]} for b in books]
    return lines, sum(l["total"] for l in lines)    # giá lấy mới nhất từ CSDL


def safe_next(default):
    n = request.form.get("next") or ""
    return n if n.startswith("/") and not n.startswith("//") else default


@shop.app_context_processor
def inject_cart_count():
    return {"cart_count": sum(session.get("cart", {}).values())}

@shop.route("/")
@shop.route("/books")
def books():
    q = Book.query
    kw = request.args.get("q", "").strip()
    cat = request.args.get("category", type=int)
    if kw:
        q = q.filter(db.or_(Book.title.ilike(f"%{kw}%"), Book.author.ilike(f"%{kw}%")))
    if cat:
        q = q.filter(Book.category_id == cat)
    return render_template("books.html", books=q.order_by(Book.id).all(), kw=kw, cat=cat,
                           categories=Category.query.order_by(Category.name).all())


@shop.route("/books/<int:book_id>")
def book_detail(book_id):
    book = db.get_or_404(Book, book_id)
    in_cart = get_cart().get(str(book_id), 0)
    return render_template("book_detail.html", book=book, in_cart=in_cart,
                           max_qty=max(book.stock - in_cart, 0))


@shop.post("/cart/add/<int:book_id>")
def cart_add(book_id):
    book = db.get_or_404(Book, book_id)
    try:
        qty = int(request.form.get("qty", 1))
    except ValueError:
        qty = 0
    cart = get_cart()
    in_cart = cart.get(str(book_id), 0)
    max_qty = book.stock - in_cart
    if qty < 1 or qty > max_qty:                       # kiểm tra Ở SERVER
        flash(f"Số lượng không hợp lệ (có thể thêm tối đa {max(max_qty, 0)}).", "danger")
    else:
        cart[str(book_id)] = in_cart + qty             # cộng dồn
        session.modified = True
        flash(f"Đã thêm {qty} × {book.title} vào giỏ hàng.", "success")
    return redirect(safe_next(request.referrer or url_for("shop.books")))


@shop.route("/cart")
def cart():
    lines, total = cart_lines()
    return render_template("cart.html", lines=lines, total=total)


@shop.post("/cart/inc/<int:book_id>")
def cart_inc(book_id):
    book = db.get_or_404(Book, book_id)
    cart = get_cart()
    if cart.get(str(book_id), 0) < book.stock:
        cart[str(book_id)] = cart.get(str(book_id), 0) + 1
        session.modified = True
    return redirect(url_for("shop.cart"))


@shop.post("/cart/dec/<int:book_id>")
def cart_dec(book_id):
    cart, k = get_cart(), str(book_id)
    if k in cart:
        cart[k] -= 1
        if cart[k] <= 0:
            del cart[k]
        session.modified = True
    return redirect(url_for("shop.cart"))


@shop.post("/cart/remove/<int:book_id>")
def cart_remove(book_id):
    get_cart().pop(str(book_id), None)
    session.modified = True
    return redirect(url_for("shop.cart"))


@shop.post("/cart/clear")
def cart_clear():
    session.pop("cart", None)
    flash("Đã xoá giỏ hàng.", "success")
    return redirect(url_for("shop.cart"))


@shop.route("/checkout", methods=["GET", "POST"])
def checkout():
    lines, subtotal = cart_lines()
    if not lines:
        flash("Giỏ hàng đang trống, hãy chọn sách trước.", "warning")
        return redirect(url_for("shop.cart"))
    ship = 0 if subtotal >= FREE_SHIP_FROM else SHIP_FEE
    form = CheckoutForm()
    if form.validate_on_submit():
        short = [l["book"].title for l in lines if l["qty"] > l["book"].stock]
        if short:                                       # kiểm tra lại tồn kho
            flash("Không đủ hàng: " + ", ".join(short), "danger")
            return redirect(url_for("shop.cart"))
        order = Order(customer_name=form.name.data.strip(), phone=form.phone.data,
                      email=form.email.data or None, address=form.address.data.strip(),
                      note=form.note.data or None,
                      payment_method=dict(form.payment.choices)[form.payment.data],
                      shipping_fee=ship, total=subtotal + ship, status="Chờ xác nhận")
        for l in lines:
            order.items.append(OrderItem(book_id=l["book"].id, quantity=l["qty"],
                                         unit_price=l["book"].price))   # đơn giá lúc đặt
            l["book"].stock -= l["qty"]                                  # trừ kho
        order.logs.append(OrderLog(status="Chờ xác nhận"))
        db.session.add(order)
        db.session.commit()                 # một transaction: lỗi thì không tạo đơn
        session.pop("cart", None)
        return redirect(url_for("shop.order_done", order_id=order.id))
    return render_template("checkout.html", form=form, lines=lines, subtotal=subtotal, ship=ship)



@shop.route("/orders/<int:order_id>")
def order_done(order_id):
    order = db.get_or_404(Order, order_id)
    return render_template("order_done.html", order=order)