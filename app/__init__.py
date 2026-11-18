import os
from flask import Flask
from config import Config
from .extensions import db, migrate, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from . import models  # noqa: F401  (để migrate thấy các model)
    from .shop import shop
    from .admin import admin
    app.register_blueprint(shop)
    app.register_blueprint(admin, url_prefix="/admin")

    @app.template_filter("vnd")
    def vnd(n):
        return f"{int(n or 0):,}".replace(",", ".") + " đ"

    @app.template_filter("dt")
    def dt(d, fmt="%d/%m/%Y %H:%M"):
        return d.strftime(fmt) if d else ""

    return app