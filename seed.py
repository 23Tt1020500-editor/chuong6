"""Chạy: python seed.py   (XOÁ sạch dữ liệu cũ rồi tạo dữ liệu mẫu)"""
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import Category, Book, Order, OrderItem, OrderLog

app = create_app()


def make(name, phone, addr, items, status, days_ago, pay="Tiền mặt khi nhận hàng"):
    sub = sum(b.price * q for b, q in items)
    ship = 0 if sub >= 200000 else 20000
    t = datetime.now() - timedelta(days=days_ago, hours=2)
    o = Order(customer_name=name, phone=phone, address=addr, payment_method=pay,
              status=status, shipping_fee=ship, total=sub + ship, created_at=t)
    o.items = [OrderItem(book=b, quantity=q, unit_price=b.price) for b, q in items]
    o.logs.append(OrderLog(status="Chờ xác nhận", changed_at=t))
    if status != "Chờ xác nhận":
        o.logs.append(OrderLog(status=status, changed_at=t + timedelta(hours=3)))
    db.session.add(o)


with app.app_context():
    db.drop_all()
    db.create_all()
    cats = {n: Category(name=n) for n in
            ["Lập trình", "Cơ sở dữ liệu", "Công cụ", "Mạng", "Kỹ năng lập trình", "Thiết kế"]}
    db.session.add_all(cats.values())
    data = [
        ("Lập trình Python cơ bản", "Nguyễn Văn A", "NXB Đại học Huế", 2024, 95000, 28, "Lập trình"),
        ("Giáo trình Flask", "Miguel Grinberg", "NXB O'Reilly", 2018, 120000, 19, "Lập trình"),
        ("Cơ sở dữ liệu", "Trần Văn B", "NXB Giáo dục", 2020, 85000, 0, "Cơ sở dữ liệu"),
        ("Pro Git", "Scott Chacon", "Apress", 2014, 150000, 14, "Công cụ"),
        ("Mạng máy tính", "Lê Văn C", "NXB Khoa học", 2019, 110000, 12, "Mạng"),
        ("Clean Code", "Robert C. Martin", "Prentice Hall", 2008, 180000, 5, "Kỹ năng lập trình"),
    ]
    b = {}
    for title, author, pub, year, price, stock, cat in data:
        b[title] = Book(title=title, author=author, publisher=pub, year=year, price=price,
                        stock=stock, category=cats[cat],
                        description="Sách mẫu phục vụ bài tập tổng hợp.")
        db.session.add(b[title])

    py, fl, git, net, cc = (b["Lập trình Python cơ bản"], b["Giáo trình Flask"], b["Pro Git"],
                            b["Mạng máy tính"], b["Clean Code"])
    make("Nguyễn Văn An", "0912345678", "12 Lê Lợi, Thuận Hoá, Huế", [(py, 2), (fl, 1), (git, 1)], "Chờ xác nhận", 1)
    make("Hoàng Thu Hà", "0987654321", "5 Hùng Vương, Huế", [(net, 2), (py, 1)], "Chờ xác nhận", 2)
    make("Võ Quốc Khánh", "0901234567", "20 Nguyễn Huệ, Huế", [(cc, 1), (git, 1)], "Chờ xác nhận", 3)
    make("Trần Thị Bình", "0933333333", "8 Trần Phú, Huế", [(fl, 1), (net, 1)], "Đang giao", 4)
    make("Lê Hoàng Cường", "0944444444", "1 Điện Biên Phủ, Huế", [(cc, 1)], "Hoàn tất", 2)
    make("Phạm Minh Dũng", "0955555555", "3 Bạch Đằng, Huế", [(py, 1)], "Đã huỷ", 5)
    make("Đặng Mai Lan", "0966666666", "9 Phan Chu Trinh, Huế", [(git, 2)], "Hoàn tất", 1)
    db.session.commit()
    print("Đã tạo dữ liệu mẫu.")