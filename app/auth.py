from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from .models import User, db, AuditLog

auth = Blueprint("auth", __name__)


# ================= 🔐 SUPER ADMIN DECORATOR =================
def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "Super Admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ================= 🔐 ADMIN DECORATOR =================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ["Admin", "Super Admin"]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ================= LOGIN =================
@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            if hasattr(user, "approved") and not user.approved:
                flash("Your account is waiting for Admin approval.")
                return redirect(url_for("auth.login"))

            login_user(user)
            return redirect(url_for("dashboard.show_dashboard"))

        else:
            flash("Invalid username or password")

    return render_template("login.html")


# ================= REGISTER =================
@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        # 🔐 Prevent Admin self-registration
        if role == "Admin":
            role = "Farmer"

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("auth.register"))

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            role=role,
            approved=False
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful. Waiting for Admin approval.")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ================= LOGOUT =================
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# ================= APPROVE USERS =================
@auth.route("/approve_users")
@login_required
@admin_required
def approve_users():

    pending_users = User.query.filter_by(approved=False).all()
    return render_template("approve_users.html", users=pending_users)


# ================= APPROVE USER =================
@auth.route("/approve_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def approve_user(user_id):

    user = User.query.get_or_404(user_id)

    user.approved = True
    db.session.commit()

    # ✅ LOG ENTRY
    log = AuditLog(
        action="Approved User",
        performed_by=current_user.username,
        target_user=user.username
    )
    db.session.add(log)
    db.session.commit()

    flash(f"{user.username} approved.")
    return redirect(url_for("auth.approve_users"))


# ================= CHANGE ROLE =================
@auth.route("/change_role/<int:user_id>", methods=["POST"])
@login_required
def change_role(user_id):

    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")

    # ❌ Prevent self role change
    if user.id == current_user.id:
        flash("You cannot change your own role.")
        return redirect(url_for("auth.approve_users"))

    # 🔐 SUPER ADMIN
    if current_user.role == "Super Admin":
        user.role = new_role
        db.session.commit()

        log = AuditLog(
            action=f"Changed role to {new_role}",
            performed_by=current_user.username,
            target_user=user.username
        )
        db.session.add(log)
        db.session.commit()

        flash("Role updated by Super Admin.")
        return redirect(url_for("auth.approve_users"))

    # 🔐 ADMIN
    if current_user.role == "Admin":

        if new_role == "Super Admin":
            flash("Only Super Admin can assign this role.")
            return redirect(url_for("auth.approve_users"))

        if new_role == "Admin":
            admin_count = User.query.filter_by(role="Admin", approved=True).count()

            if user.role != "Admin" and admin_count >= 3:
                flash("Maximum 3 admins allowed.")
                return redirect(url_for("auth.approve_users"))

        user.role = new_role
        db.session.commit()

        log = AuditLog(
            action=f"Changed role to {new_role}",
            performed_by=current_user.username,
            target_user=user.username
        )
        db.session.add(log)
        db.session.commit()

        flash("Role updated successfully.")
        return redirect(url_for("auth.approve_users"))

    # ❌ Others blocked
    flash("Access denied.")
    return redirect(url_for("dashboard.show_dashboard"))


# ================= VIEW LOGS =================
@auth.route("/logs")
@login_required
@admin_required
def view_logs():

    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template("logs.html", logs=logs)
