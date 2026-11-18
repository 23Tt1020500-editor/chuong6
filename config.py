import os
BASE = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "doi-thanh-chuoi-bi-mat"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE, "bookstore.db")
    UPLOAD_DIR = os.path.join(BASE, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024   # chặn request quá lớn; giới hạn 2 MB kiểm ở form