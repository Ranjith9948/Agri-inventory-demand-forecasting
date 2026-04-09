from flask import Flask, session, redirect, request, abort, url_for
from flask_login import LoginManager, current_user
from flask_bcrypt import Bcrypt
from functools import wraps

from config import Config
from .models import db, User
from .translations import translate

login_manager = LoginManager()
bcrypt = Bcrypt()


# ============================
# 🔐 ADMIN DECORATOR (FIXED)
# ============================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ["Admin", "Super Admin"]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ============================
    # 🔐 SESSION SECURITY
    # ============================
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=False,  # change to True in production
        SESSION_COOKIE_SAMESITE='Lax'
    )

    # ============================
    # Initialize Extensions
    # ============================
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    login_manager.login_view = "auth.login"

    # ============================
    # 🔐 UNAUTHORIZED HANDLER (FIXED)
    # ============================
    @login_manager.unauthorized_handler
    def unauthorized_callback():
        return redirect(url_for("auth.login"))

    # ============================
    # 🔐 PREVENT CACHE
    # ============================
    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # ============================
    # 🌐 LANGUAGE ROUTE
    # ============================
    @app.route("/set_language/<lang>")
    def set_language(lang):
        if lang not in ["en", "hi", "te"]:
            return redirect("/")
        session["lang"] = lang
        return redirect(request.referrer or "/")

    # ============================
    # 🌐 TRANSLATOR
    # ============================
    @app.context_processor
    def inject_translator():
        def _(text):
            lang = session.get("lang", "en")
            return translate(text, lang)
        return dict(_=_)

    # ============================
    # 🔥 FIXED: PENDING COUNT (SUPER ADMIN INCLUDED)
    # ============================
    @app.context_processor
    def inject_pending_count():
        if current_user.is_authenticated and current_user.role in ["Admin", "Super Admin"]:
            pending = User.query.filter_by(approved=False).count()
        else:
            pending = 0
        return dict(pending_count=pending)

    # ============================
    # 🔐 USER LOADER
    # ============================
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ============================
    # Register Blueprints
    # ============================
    from .auth import auth
    from .dashboard import dashboard
    from .forecast import forecast
    from .inventory import inventory

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(forecast)
    app.register_blueprint(inventory)
    # ============================
    # 🏠 HOME ROUTE (FIXED)
    # ============================
    @app.route("/")
    def home():
      if current_user.is_authenticated:
        return redirect(url_for("dashboard.show_dashboard"))
        return redirect(url_for("auth.login"))

    # ============================
    # Create Database
    # ============================
    with app.app_context():
        db.create_all()

    return app
