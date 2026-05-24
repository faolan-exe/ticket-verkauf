import os
import secrets
from flask import Flask, session

from .db import init_pool, ensure_admin_user, run_migrations
from .routes.main import bp as main_bp
from .routes.admin import bp as admin_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ["SECRET_KEY"]
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    init_pool()
    run_migrations()
    ensure_admin_user(
        os.environ.get("ADMIN_USERNAME", "admin"),
        os.environ["ADMIN_PASSWORD"],
    )

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.before_request
    def set_csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_hex(32)

    return app
