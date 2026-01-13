from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    lock_until = db.Column(db.DateTime, nullable=True)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    monthly_contribution = db.Column(db.Integer, nullable=False, default=10)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    archived = db.Column(db.Boolean, nullable=False, default=False)
    creator = db.relationship('User', backref='created_groups')

class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    balance = db.Column(db.Integer, nullable=False, default=0)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    auto_pay = db.Column(db.Boolean, nullable=False, default=True)
    user = db.relationship('User', backref='memberships')
    group = db.relationship('Group', backref='memberships')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='approved')
    reason = db.Column(db.String(255), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    provider = db.Column(db.String(20), nullable=True)
    external_id = db.Column(db.String(120), nullable=True)
    group = db.relationship('Group', backref='transactions')
    user = db.relationship('User', backref='transactions')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    type = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship('User', backref='notifications')
    group = db.relationship('Group', backref='notifications')

def group_balance(group_id):
    from sqlalchemy import func
    import os
    rate = 0.02
    try:
        rate = float(os.environ.get('MYTAKAFUL_COMMISSION_RATE', '0.02'))
    except Exception:
        rate = 0.02
    cotisations = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.group_id == group_id, Transaction.status == 'approved', Transaction.type == 'cotisation').scalar() or 0
    aides = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.group_id == group_id, Transaction.status == 'approved', Transaction.type == 'aide').scalar() or 0
    commission = int(cotisations * rate)
    return int(cotisations - aides - commission)
