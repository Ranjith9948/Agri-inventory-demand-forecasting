from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ================= USER MODEL =================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)

    password = db.Column(db.String(200), nullable=False)

    # Roles: Farmer, Officer, Data Analyst, Admin, Super Admin
    role = db.Column(db.String(50), default="Farmer")

    approved = db.Column(db.Boolean, default=False)

    # 🔐 Password functions
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


# ================= AUDIT LOG MODEL =================
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    action = db.Column(db.String(200))
    performed_by = db.Column(db.String(100))
    target_user = db.Column(db.String(100))

    timestamp = db.Column(db.DateTime, default=db.func.now())
