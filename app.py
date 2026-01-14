"""
Application MyTakaful (Flask)
- Authentification USER/ADMIN avec anti-bruteforce
- Dashboards USER/ADMIN, paiements Stripe/PayPal, notifications SSE
- Exports CSV/PDF, gestion utilisateurs/groupes
"""
import os
from functools import wraps
import time
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from models import db, User, Group, Membership, Transaction, Notification, group_balance
from config import Config
from i18n import t, get_current_language, set_language, get_available_languages, get_language_direction
from ai_assistant import ai_assistant

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
STRIPE_SECRET_KEY = app.config.get('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = app.config.get('STRIPE_PUBLIC_KEY')
PAYPAL_CLIENT_ID = app.config.get('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = app.config.get('PAYPAL_CLIENT_SECRET')

def current_user():
    uid = session.get('user_id')
    if not uid:
        g.user = None
        return None
    u = User.query.get(uid)
    g.user = u
    return u

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash('Veuillez vous connecter')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return wrapper

def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            u = current_user()
            if not u:
                flash('Veuillez vous connecter')
                return redirect(url_for('login', next=request.path))
            if u.role != role:
                flash('Accès non autorisé')
                if u.role == 'admin':
                    return redirect(url_for('admin'))
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.before_request
def load_user():
    current_user()

@app.route('/')
def home():
    if 'user_id' in session:
        u = User.query.get(session.get('user_id'))
        if u and u.role == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('groups'))
    return render_template('home.html')

def notify_user(user_id, type_, message, group_id=None):
    n = Notification(user_id=user_id, group_id=group_id, type=type_, message=message)
    db.session.add(n)
    db.session.commit()

def notify_admins(type_, message, group_id=None):
    admins = User.query.filter_by(role='admin').all()
    for a in admins:
        n = Notification(user_id=a.id, group_id=group_id, type=type_, message=message)
        db.session.add(n)
    db.session.commit()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not name or not email or not password:
            flash('Veuillez remplir tous les champs')
            return redirect(url_for('register'))
        existing_username = User.query.filter_by(name=name).first()
        existing_email = User.query.filter_by(email=email).first()
        if existing_username or existing_email:
            flash('Utilisateur ou email déjà utilisé')
            return redirect(url_for('register'))
        role = 'user'
        has_admin = User.query.filter_by(role='admin').first()
        if not has_admin:
            role = 'admin'
        password_hash = generate_password_hash(password)
        user = User(name=name, email=email, password_hash=password_hash, role=role)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        if role == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('groups'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip() or request.form.get('name', '').strip()
        password = request.form.get('password', '')
        next_url = request.args.get('next')
        user = User.query.filter_by(name=identifier).first()
        if not user:
            user = User.query.filter_by(email=identifier.lower()).first()
        if user:
            if user.is_blocked:
                flash('Compte bloqué')
                return redirect(url_for('login'))
            if user.lock_until and user.lock_until > datetime.utcnow():
                flash('Trop de tentatives, réessayez plus tard')
                return redirect(url_for('login'))
        if not user or not check_password_hash(user.password_hash, password):
            if user:
                user.failed_attempts = (user.failed_attempts or 0) + 1
                if user.failed_attempts % 5 == 0:
                    user.lock_until = datetime.utcnow() + timedelta(minutes=15)
                if user.failed_attempts >= 15:
                    user.is_blocked = True
                db.session.commit()
            flash('Identifiants invalides')
            return redirect(url_for('login'))
        session['user_id'] = user.id
        user.failed_attempts = 0
        user.lock_until = None
        db.session.commit()
        if next_url:
            return redirect(next_url)
        if user.role == 'admin':
            return redirect(url_for('admin'))
        return redirect(url_for('groups'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    flash('Déconnecté')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    u = g.user
    if u.role == 'admin':
        return redirect(url_for('admin'))
    memberships = Membership.query.filter_by(user_id=u.id).all()
    joined_groups = [m.group for m in memberships]
    available_groups = Group.query.filter(~Group.memberships.any(Membership.user_id == u.id), Group.archived == False).all()
    transactions = Transaction.query.filter_by(user_id=u.id).order_by(Transaction.date.desc()).all()
    transactions_json = [{
        'date': t.date.isoformat(),
        'type': t.type,
        'amount': t.amount,
        'status': t.status
    } for t in transactions]
    balances = {g.id: group_balance(g.id) for g in joined_groups}
    total_balance = sum(balances.values()) if balances else 0
    total_monthly_due = sum(getattr(g, 'monthly_contribution', 0) for g in joined_groups)
    aids_received = sum(t.amount for t in Transaction.query.filter_by(user_id=u.id, type='aide', status='approved').all())
    notes = Notification.query.filter_by(user_id=u.id).order_by(Notification.date.desc()).limit(20).all()
    
    group_funds = [{'name': g.name, 'fund': balances.get(g.id, 0)} for g in joined_groups]
    return render_template('dashboard_user.html', user=u, joined_groups=joined_groups, available_groups=available_groups, transactions=transactions, transactions_json=transactions_json, balances=balances, total_balance=total_balance, total_monthly_due=total_monthly_due, aids_received=aids_received, notifications=notes, group_funds=group_funds, paypal_client_id=PAYPAL_CLIENT_ID, stripe_public_key=STRIPE_PUBLIC_KEY)

@app.route('/groups')
@login_required
def groups():
    u = g.user
    if u.role == 'admin':
        return redirect(url_for('admin'))
    all_groups = Group.query.filter_by(archived=False).order_by(Group.created_at.desc()).all()
    membership_ids = {m.group_id for m in Membership.query.filter_by(user_id=u.id).all()}
    funds = {gobj.id: group_balance(gobj.id) for gobj in all_groups}
    return render_template('groups.html', user=u, all_groups=all_groups, membership_ids=membership_ids, funds=funds)

@app.route('/admin')
@role_required('admin')
def admin():
    users = User.query.count()
    groups_qs = Group.query.filter_by(archived=False).all()
    groups = len(groups_qs)
    txs = Transaction.query.count()
    totals = {g.id: group_balance(g.id) for g in groups_qs}
    total_funds = sum(totals.values())
    notes = Notification.query.filter_by(user_id=g.user.id).order_by(Notification.date.desc()).limit(20).all()
    chart_labels = [g.name for g in groups_qs]
    chart_values = [totals.get(g.id, 0) for g in groups_qs]
    # Only show pending transactions in the recent transactions section
    recent = Transaction.query.filter_by(status='pending').order_by(Transaction.date.desc()).limit(50).all()

    gid = request.args.get('group_id', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    from datetime import datetime, timedelta
    filters = []
    if gid:
        try:
            filters.append(Transaction.group_id == int(gid))
        except Exception:
            pass
    if start:
        try:
            sd = datetime.strptime(start, '%Y-%m-%d')
            filters.append(Transaction.date >= sd)
        except Exception:
            pass
    if end:
        try:
            ed = datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            filters.append(Transaction.date <= ed)
        except Exception:
            pass
    base_q = Transaction.query
    if filters:
        for f in filters:
            base_q = base_q.filter(f)
    cotisations = base_q.filter(Transaction.type == 'cotisation', Transaction.status == 'approved').order_by(Transaction.date.desc()).all()
    # Only show pending aids in the admin dashboard
    aides = base_q.filter(Transaction.type == 'aide', Transaction.status == 'pending').order_by(Transaction.date.desc()).all()

    active_members = Membership.query.join(Group, Membership.group_id == Group.id).filter(Group.archived == False).count()
    pending_aids = Transaction.query.filter_by(type='aide', status='pending').count()
    from datetime import datetime
    now_dt = datetime.utcnow()
    start_month = datetime(now_dt.year, now_dt.month, 1)
    monthly_revenue = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0)).filter(Transaction.type == 'cotisation', Transaction.status == 'approved', Transaction.date >= start_month).scalar() or 0

    aid_status_counts = {
        'pending': Transaction.query.filter_by(type='aide', status='pending').count(),
        'approved': Transaction.query.filter_by(type='aide', status='approved').count(),
        'rejected': Transaction.query.filter_by(type='aide', status='rejected').count(),
    }
    # contributions per day for current month
    revenue_by_day = {}
    for t in Transaction.query.filter(Transaction.type == 'cotisation', Transaction.status == 'approved', Transaction.date >= start_month).all():
        d = t.date.strftime('%Y-%m-%d')
        revenue_by_day[d] = revenue_by_day.get(d, 0) + t.amount
    revenue_labels = sorted(revenue_by_day.keys())
    revenue_values = [revenue_by_day[d] for d in revenue_labels]

    return render_template(
        'dashboard_admin.html',
        user_count=users,
        group_count=groups,
        tx_count=txs,
        total_funds=total_funds,
        notifications=notes,
        chart_labels=chart_labels,
        chart_values=chart_values,
        transactions=recent,
        active_members=active_members,
        pending_aids=pending_aids,
        monthly_revenue=monthly_revenue,
        aid_status_counts=aid_status_counts,
        revenue_labels=revenue_labels,
        revenue_values=revenue_values,
        groups_list=groups_qs,
        selected_group_id=gid,
        start_date=start,
        end_date=end,
        cotisations=cotisations,
        aides=aides,
    )

@app.route('/create-group', methods=['GET', 'POST'])
@login_required
def create_group():
    u = g.user
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        monthly_val = 10
        if not name:
            flash('Nom du groupe requis')
            return redirect(url_for('create_group'))
        existing = Group.query.filter_by(name=name).first()
        if existing:
            flash('Nom du groupe déjà utilisé')
            return redirect(url_for('create_group'))
        gobj = Group(name=name, description=description, monthly_contribution=monthly_val, created_by=u.id)
        db.session.add(gobj)
        db.session.commit()
        member = Membership(user_id=u.id, group_id=gobj.id)
        db.session.add(member)
        db.session.commit()
        flash('Groupe créé')
        notify_admins('group_created', f"Groupe '{name}' créé", group_id=gobj.id)
        return redirect(url_for('group_details', id=gobj.id))
    return render_template('create_group.html')

@app.route('/group/<int:id>')
@login_required
def group_details(id):
    u = g.user
    gobj = Group.query.get_or_404(id)
    members = [m.user for m in gobj.memberships]
    txs = Transaction.query.filter_by(group_id=id, status='approved').order_by(Transaction.date.desc()).all()
    bal = group_balance(id)
    # Get user's aids for this group
    user_aids = Transaction.query.filter_by(group_id=id, user_id=u.id, type='aide').order_by(Transaction.date.desc()).all()
    return render_template('group_details.html', group=gobj, members=members, transactions=txs, balance=bal, user_aids=user_aids)

@app.route('/join-group/<int:id>', methods=['POST'])
@login_required
def join_group(id):
    u = g.user
    gobj = Group.query.get_or_404(id)
    existing = Membership.query.filter_by(user_id=u.id, group_id=id).first()
    if existing:
        flash('Déjà membre')
        return redirect(url_for('dashboard'))
    m = Membership(user_id=u.id, group_id=id)
    db.session.add(m)
    db.session.commit()
    flash('Groupe rejoint')
    notify_user(u.id, 'group_join', f"Vous avez rejoint le groupe '{gobj.name}'", group_id=id)
    notify_admins('group_join', f"{u.name} a rejoint le groupe '{gobj.name}'", group_id=id)
    return redirect(url_for('dashboard'))

@app.route('/leave-group/<int:id>', methods=['POST'])
@login_required
def leave_group(id):
    u = g.user
    gobj = Group.query.get_or_404(id)
    m = Membership.query.filter_by(user_id=u.id, group_id=id).first()
    if not m:
        flash('Vous n’êtes pas membre de ce groupe')
        return redirect(url_for('dashboard'))
    db.session.delete(m)
    db.session.commit()
    notify_user(u.id, 'group_leave', f"Vous avez quitté le groupe '{gobj.name}'", group_id=id)
    notify_admins('group_leave', f"{u.name} a quitté le groupe '{gobj.name}'", group_id=id)
    flash('Groupe quitté')
    return redirect(url_for('dashboard'))

@app.route('/request-aid/<int:id>', methods=['POST'])
@login_required
def request_aid(id):
    u = g.user
    gobj = Group.query.get_or_404(id)
    amount = request.form.get('amount', '0').strip()
    reason = request.form.get('reason', '').strip()
    try:
        amt = int(amount)
        if amt <= 0:
            raise ValueError()
    except Exception:
        flash("Montant d'aide invalide")
        return redirect(url_for('group_details', id=id))
    t = Transaction(group_id=id, user_id=u.id, amount=amt, type='aide', status='pending', reason=reason)
    db.session.add(t)
    db.session.commit()
    flash('Demande d’aide envoyée')
    msg = f"Demande d’aide de {u.name} pour {amt} MAD"
    if reason:
        msg += f" — Motif: {reason}"
    notify_admins('aid_request', msg, group_id=id)
    return redirect(url_for('group_details', id=id))

@app.route('/admin/transactions')
@role_required('admin')
def admin_transactions():
    txs = Transaction.query.order_by(Transaction.date.desc()).all()
    return render_template('dashboard_admin.html', transactions=txs, users=User.query.all(), groups=Group.query.all())

@app.route('/admin/export/csv')
@role_required('admin')
def export_csv():
    import csv
    from io import StringIO
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['id','date','type','amount','status','user','group'])
    for t in Transaction.query.order_by(Transaction.date.asc()).all():
        writer.writerow([t.id, t.date.isoformat(), t.type, t.amount, t.status, getattr(t.user, 'name', ''), getattr(t.group, 'name', '')])
    resp = app.response_class(si.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    return resp

@app.route('/admin/export/cotisations.csv')
@role_required('admin')
def export_cotisations_csv():
    import csv
    from io import StringIO
    gid = request.args.get('group_id', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    from datetime import datetime, timedelta
    q = Transaction.query.filter(Transaction.type == 'cotisation', Transaction.status == 'approved')
    if gid:
        try:
            q = q.filter(Transaction.group_id == int(gid))
        except Exception:
            pass
    if start:
        try:
            sd = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Transaction.date >= sd)
        except Exception:
            pass
    if end:
        try:
            ed = datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            q = q.filter(Transaction.date <= ed)
        except Exception:
            pass
    si = StringIO()
    w = csv.writer(si)
    w.writerow(['id','date','amount','user','group'])
    for t in q.order_by(Transaction.date.asc()).all():
        w.writerow([t.id, t.date.isoformat(), t.amount, getattr(t.user, 'name', ''), getattr(t.group, 'name', '')])
    resp = app.response_class(si.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = 'attachment; filename="cotisations.csv"'
    return resp

@app.route('/admin/export/aides.csv')
@role_required('admin')
def export_aides_csv():
    import csv
    from io import StringIO
    gid = request.args.get('group_id', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    from datetime import datetime, timedelta
    q = Transaction.query.filter(Transaction.type == 'aide')
    if gid:
        try:
            q = q.filter(Transaction.group_id == int(gid))
        except Exception:
            pass
    if start:
        try:
            sd = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Transaction.date >= sd)
        except Exception:
            pass
    if end:
        try:
            ed = datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            q = q.filter(Transaction.date <= ed)
        except Exception:
            pass
    si = StringIO()
    w = csv.writer(si)
    w.writerow(['id','date','amount','user','group','reason','status'])
    for t in q.order_by(Transaction.date.asc()).all():
        w.writerow([t.id, t.date.isoformat(), t.amount, getattr(t.user, 'name', ''), getattr(t.group, 'name', ''), getattr(t, 'reason', '') or '', t.status])
    resp = app.response_class(si.getvalue(), mimetype='text/csv')
    resp.headers['Content-Disposition'] = 'attachment; filename="aides.csv"'
    return resp

@app.route('/admin/export/cotisations.pdf')
@role_required('admin')
def export_cotisations_pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from io import BytesIO
    gid = request.args.get('group_id', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    from datetime import datetime, timedelta
    q = Transaction.query.filter(Transaction.type == 'cotisation', Transaction.status == 'approved')
    if gid:
        try:
            q = q.filter(Transaction.group_id == int(gid))
        except Exception:
            pass
    if start:
        try:
            sd = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Transaction.date >= sd)
        except Exception:
            pass
    if end:
        try:
            ed = datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            q = q.filter(Transaction.date <= ed)
        except Exception:
            pass
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Cotisations")
    y -= 24
    c.setFont("Helvetica", 11)
    for t in q.order_by(Transaction.date.asc()).all():
        line = f"{t.date.strftime('%Y-%m-%d')} | {t.amount} MAD | {getattr(t.user,'name','')} | {getattr(t.group,'name','')}"
        c.drawString(40, y, line)
        y -= 18
        if y < 60:
            c.showPage(); y = h - 50; c.setFont("Helvetica", 11)
    c.showPage(); c.save()
    pdf = buf.getvalue()
    buf.close()
    resp = app.response_class(pdf, mimetype='application/pdf')
    resp.headers['Content-Disposition'] = 'attachment; filename="cotisations.pdf"'
    return resp

@app.route('/admin/export/aides.pdf')
@role_required('admin')
def export_aides_pdf():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from io import BytesIO
    gid = request.args.get('group_id', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    from datetime import datetime, timedelta
    q = Transaction.query.filter(Transaction.type == 'aide')
    if gid:
        try:
            q = q.filter(Transaction.group_id == int(gid))
        except Exception:
            pass
    if start:
        try:
            sd = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Transaction.date >= sd)
        except Exception:
            pass
    if end:
        try:
            ed = datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            q = q.filter(Transaction.date <= ed)
        except Exception:
            pass
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Aides")
    y -= 24
    c.setFont("Helvetica", 11)
    for t in q.order_by(Transaction.date.asc()).all():
        line = f"{t.date.strftime('%Y-%m-%d')} | {getattr(t.user,'name','')} | {t.amount} MAD | {getattr(t,'reason','') or ''} | {t.status}"
        c.drawString(40, y, line)
        y -= 18
        if y < 60:
            c.showPage(); y = h - 50; c.setFont("Helvetica", 11)
    c.showPage(); c.save()
    pdf = buf.getvalue()
    buf.close()
    resp = app.response_class(pdf, mimetype='application/pdf')
    resp.headers['Content-Disposition'] = 'attachment; filename="aides.pdf"'
    return resp

@app.route('/admin/export/pdf')
@role_required('admin')
def export_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from io import BytesIO
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 16)
    c.drawString(50, 800, "MyTakaful - Rapport global")
    c.setFont("Helvetica", 12)
    y = 770
    c.drawString(50, y, f"Utilisateurs: {User.query.count()}  | Groupes: {Group.query.filter_by(archived=False).count()}  | Transactions: {Transaction.query.count()}")
    y -= 30
    c.drawString(50, y, "Fonds par groupe:")
    y -= 20
    for gobj in Group.query.filter_by(archived=False).all():
        c.drawString(60, y, f"- {gobj.name}: {group_balance(gobj.id)} MAD")
        y -= 20
        if y < 100:
            c.showPage(); y = 800
    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    resp = app.response_class(pdf, mimetype='application/pdf')
    resp.headers['Content-Disposition'] = 'attachment; filename="rapport.pdf"'
    return resp

@app.route('/admin/transaction/<int:tx_id>/approve', methods=['POST'])
@role_required('admin')
def approve_transaction(tx_id):
    t = Transaction.query.get_or_404(tx_id)
    if t.type == 'aide':
        bal = group_balance(t.group_id)
        if bal < t.amount:
            flash('Fonds insuffisants pour approuver l’aide')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return '', 200
            return redirect(url_for('admin'))
    
    # Approve the transaction
    old_status = t.status
    t.status = 'approved'
    db.session.commit()
    
    # Update group funds if this is a contribution
    if t.type == 'cotisation' and old_status != 'approved':
        # Add the amount to the group balance
        membership = Membership.query.filter_by(user_id=t.user_id, group_id=t.group_id).first()
        if membership:
            try:
                # Credit the group with the contribution amount
                group_membership = Membership.query.filter_by(group_id=t.group_id).first()
                if group_membership and hasattr(group_membership, 'balance'):
                    group_membership.balance = (group_membership.balance or 0) + t.amount
            except Exception:
                pass
            db.session.commit()
    
    flash('Transaction approuvée avec succès', 'success')
    notify_user(t.user_id, 'aid_approved' if t.type == 'aide' else 'tx_approved', 'Transaction approuvée', group_id=t.group_id)
    if t.type == 'aide':
        notify_admins('aid_approved', f"Aide de {t.amount} MAD validée pour {t.user.name}", group_id=t.group_id)
    
    # Return appropriate response based on request type
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return '', 200
    return redirect(url_for('admin'))

@app.route('/admin/transaction/<int:tx_id>/reject', methods=['POST'])
@role_required('admin')
def reject_transaction(tx_id):
    t = Transaction.query.get_or_404(tx_id)
    t.status = 'rejected'
    db.session.commit()
    flash('Transaction refusée avec succès', 'success')
    
    # Return appropriate response based on request type
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return '', 200
    return redirect(url_for('admin'))

@app.route('/admin/aide/<int:aid_id>/approve', methods=['POST'])
@role_required('admin')
def approve_aid(aid_id):
    t = Transaction.query.get_or_404(aid_id)
    
    # Check that this is an aid transaction
    if t.type != 'aide':
        flash('Transaction invalide')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return '', 400
        return redirect(url_for('admin'))
    
    # Check if group has sufficient funds
    bal = group_balance(t.group_id)
    if bal < t.amount:
        flash('Fonds insuffisants pour approuver l’aide')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return '', 400
        return redirect(url_for('admin'))
    
    # Approve the aid
    t.status = 'approved'
    db.session.commit()
    
    flash('Aide approuvée avec succès', 'success')
    notify_user(t.user_id, 'aid_approved', 'Votre demande d’aide a été approuvée', group_id=t.group_id)
    notify_admins('aid_approved', f"Aide de {t.amount} MAD approuvée pour {t.user.name}", group_id=t.group_id)
    
    # Return appropriate response based on request type
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return '', 200
    return redirect(url_for('admin'))

@app.route('/admin/aide/<int:aid_id>/reject', methods=['POST'])
@role_required('admin')
def reject_aid(aid_id):
    t = Transaction.query.get_or_404(aid_id)
    
    # Check that this is an aid transaction
    if t.type != 'aide':
        flash('Transaction invalide')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return '', 400
        return redirect(url_for('admin'))
    
    # Reject the aid
    t.status = 'rejected'
    db.session.commit()
    
    flash('Aide refusée avec succès', 'success')
    notify_user(t.user_id, 'aid_rejected', 'Votre demande d’aide a été refusée', group_id=t.group_id)
    
    # Return appropriate response based on request type
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return '', 200
    return redirect(url_for('admin'))

@app.route('/admin/force-contribution/<int:user_id>/<int:group_id>', methods=['POST'])
@role_required('admin')
def force_contribution(user_id, group_id):
    gobj = Group.query.get_or_404(group_id)
    User.query.get_or_404(user_id)
    t = Transaction(group_id=group_id, user_id=user_id, amount=gobj.monthly_contribution, type='cotisation', status='approved')
    db.session.add(t)
    db.session.commit()
    flash('Cotisation forcée')
    notify_user(user_id, 'contribution_paid', f"Cotisation de {gobj.monthly_contribution} MAD enregistrée", group_id=group_id)
    notify_admins('contribution_paid', f"Cotisation enregistrée pour utilisateur #{user_id}", group_id=group_id)
    return redirect(url_for('admin'))

@app.route('/pay-contribution/<int:group_id>', methods=['POST'])
@login_required
def pay_contribution(group_id):
    u = g.user
    gobj = Group.query.get_or_404(group_id)
    membership = Membership.query.filter_by(user_id=u.id, group_id=group_id).first()
    if not membership:
        flash('Vous devez rejoindre le groupe pour cotiser')
        return redirect(url_for('dashboard'))
    t = Transaction(group_id=group_id, user_id=u.id, amount=gobj.monthly_contribution, type='cotisation', status='approved')
    db.session.add(t)
    db.session.commit()
    flash('Cotisation payée')
    notify_user(u.id, 'contribution_paid', f"Cotisation de {gobj.monthly_contribution} MAD payée", group_id=group_id)
    notify_admins('contribution_paid', f"{u.name} a payé sa cotisation", group_id=group_id)
    return redirect(url_for('dashboard'))

@app.route('/pay/stripe/create-checkout-session/<int:group_id>', methods=['POST'])
@login_required
def create_checkout_session(group_id):
    if not STRIPE_SECRET_KEY or not STRIPE_PUBLIC_KEY:
        flash('Paiement Stripe indisponible (clé manquante)')
        return redirect(url_for('dashboard'))
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    u = g.user
    gobj = Group.query.get_or_404(group_id)
    membership = Membership.query.filter_by(user_id=u.id, group_id=group_id).first()
    if not membership:
        flash('Vous devez rejoindre le groupe pour cotiser')
        return redirect(url_for('dashboard'))
    amount_cents = int(gobj.monthly_contribution) * 100
    session_obj = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'mad',
                'product_data': {'name': f'Cotisation {gobj.name}'},
                'unit_amount': amount_cents,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=url_for('stripe_success', group_id=group_id, _external=True),
        cancel_url=url_for('stripe_cancel', group_id=group_id, _external=True),
    )
    t = Transaction(group_id=group_id, user_id=u.id, amount=gobj.monthly_contribution, type='cotisation', status='pending', provider='stripe', external_id=session_obj.id)
    db.session.add(t)
    db.session.commit()
    return redirect(session_obj.url)

@app.route('/pay', methods=['GET', 'POST'])
@login_required
def pay():
    u = g.user
    if request.method == 'POST':
        provider = request.form.get('provider', 'internal')
        group_id = int(request.form.get('group_id', '0'))
        gobj = Group.query.get_or_404(group_id)
        membership = Membership.query.filter_by(user_id=u.id, group_id=group_id).first()
        if not membership:
            flash('Vous devez rejoindre le groupe pour cotiser')
            return redirect(url_for('dashboard'))
        if provider == 'stripe':
            return redirect(url_for('create_checkout_session', group_id=group_id))
        elif provider == 'internal':
            t = Transaction(group_id=group_id, user_id=u.id, amount=gobj.monthly_contribution, type='cotisation', status='approved')
            db.session.add(t)
            db.session.commit()
            notify_user(u.id, 'contribution_paid', f"Cotisation de {gobj.monthly_contribution} MAD payée", group_id=group_id)
            notify_admins('contribution_paid', f"{u.name} a payé sa cotisation", group_id=group_id)
            flash('Cotisation payée')
            return redirect(url_for('dashboard'))
        elif provider == 'paypal':
            flash('Utilisez le bouton PayPal sur la page de paiement')
            return redirect(url_for('pay', group_id=group_id))
        else:
            flash('Fournisseur inconnu')
            return redirect(url_for('pay'))
    # GET
    q_group_id = request.args.get('group_id', None)
    groups = Group.query.filter(~Group.memberships.any(Membership.user_id == u.id) == False, Group.archived == False).all()
    selected = None
    if q_group_id:
        try:
            gid = int(q_group_id)
            selected = Group.query.get(gid)
        except Exception:
            selected = None
    return render_template('pay.html', user=u, groups=groups, selected_group=selected, paypal_client_id=PAYPAL_CLIENT_ID, stripe_public_key=STRIPE_PUBLIC_KEY)

@app.route('/paiement', methods=['GET', 'POST'])
@login_required
def paiement():
    u = g.user
    if request.method == 'POST':
        # Handle simulated payment modes
        mode = (request.form.get('mode_paiement', '') or request.form.get('provider', '')).strip()
        group_id = int(request.form.get('group_id', '0'))
        amount_str = (request.form.get('montant', '') or request.form.get('amount', '0')).strip()
        
        # Log the payment attempt
        print(f"Processing simulated payment for group {group_id} with mode {mode}")
        
        try:
            amount = int(amount_str)
            if amount < 10:
                raise ValueError()
        except Exception:
            flash('Montant invalide (minimum 10 MAD)')
            return redirect(url_for('paiement'))
        
        if not mode:
            flash('Veuillez choisir un mode de paiement')
            return redirect(url_for('paiement', group_id=group_id))
        
        # Map mode to provider
        provider = 'stripe' if mode == 'carte' else ('paypal' if mode == 'paypal' else 'internal')
        
        gobj = Group.query.get_or_404(group_id)
        membership = Membership.query.filter_by(user_id=u.id, group_id=group_id).first()
        if not membership:
            flash('Vous devez rejoindre le groupe pour cotiser')
            return redirect(url_for('dashboard'))
        
        # Process payment directly (simulated) - create with pending status
        t = Transaction(group_id=group_id, user_id=u.id, amount=amount, type='cotisation', status='pending', provider=provider)
        db.session.add(t)
        # Débit du solde interne du membre (si utilisé)
        try:
            if hasattr(membership, 'balance') and membership.balance is not None:
                membership.balance = max((membership.balance or 0) - amount, 0)
        except Exception:
            pass
        db.session.commit()
        
        # Display appropriate message based on payment mode
        mode_text = 'Stripe' if mode == 'carte' else ('PayPal' if mode == 'paypal' else 'Compte interne')
        notify_user(u.id, 'contribution_paid', f"Cotisation de {amount} MAD payée (Simulation {mode_text})", group_id=group_id)
        notify_admins('contribution_paid', f"Cotisation simulée via {mode_text} pour utilisateur #{u.id}", group_id=group_id)
        flash(f'Paiement simulé via {mode_text}')
        return redirect(url_for('dashboard'))
    # GET
    q_group_id = request.args.get('group_id', None)
    groups = Group.query.filter(Group.memberships.any(Membership.user_id == u.id), Group.archived == False).all()
    balances = {g.id: group_balance(g.id) for g in groups}
    selected = None
    if q_group_id:
        try:
            gid = int(q_group_id)
            selected = Group.query.get(gid)
        except Exception:
            selected = None
    return render_template('paiement.html', user=u, groups=groups, balances=balances, selected_group=selected, paypal_client_id=PAYPAL_CLIENT_ID, stripe_public_key=STRIPE_PUBLIC_KEY)

def paypal_access_token():
    import base64, requests
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        return None
    auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
    r = requests.post('https://api-m.sandbox.paypal.com/v1/oauth2/token', headers={'Authorization': f'Basic {auth}'}, data={'grant_type': 'client_credentials'})
    if r.status_code == 200:
        return r.json().get('access_token')
    return None

@app.route('/pay/paypal/create-order/<int:group_id>', methods=['POST'])
@login_required
def paypal_create_order(group_id):
    import requests
    u = g.user
    gobj = Group.query.get_or_404(group_id)
    membership = Membership.query.filter_by(user_id=u.id, group_id=group_id).first()
    if not membership:
        return {'error': 'join_required'}, 400
    token = paypal_access_token()
    if not token:
        return {'error': 'paypal_not_configured'}, 400
    body = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'amount': {'currency_code': 'USD', 'value': str(gobj.monthly_contribution)}
        }]
    }
    r = requests.post('https://api-m.sandbox.paypal.com/v2/checkout/orders', json=body, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    if r.status_code != 201:
        return {'error': 'order_failed'}, 400
    order = r.json()
    t = Transaction(group_id=group_id, user_id=u.id, amount=gobj.monthly_contribution, type='cotisation', status='pending', provider='paypal', external_id=order['id'])
    db.session.add(t)
    db.session.commit()
    return {'id': order['id']}

@app.route('/pay/paypal/capture/<order_id>')
@login_required
def paypal_capture(order_id):
    import requests
    token = paypal_access_token()
    if not token:
        flash('PayPal indisponible')
        return redirect(url_for('dashboard'))
    r = requests.post(f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture', headers={'Authorization': f'Bearer {token}'})
    if r.status_code != 201:
        flash('Échec capture PayPal')
        return redirect(url_for('dashboard'))
    t = Transaction.query.filter_by(external_id=order_id, provider='paypal', status='pending').first()
    if t:
        t.status = 'approved'
        db.session.commit()
        notify_user(t.user_id, 'contribution_paid', f"Cotisation de {t.amount} MAD payée (PayPal)", group_id=t.group_id)
        notify_admins('contribution_paid', f"Cotisation PayPal capturée pour utilisateur #{t.user_id}", group_id=t.group_id)
    flash('Paiement PayPal réussi')
    return redirect(url_for('dashboard'))

@app.route('/pay/stripe/success')
@login_required
def stripe_success():
    group_id = int(request.args.get('group_id'))
    u = g.user
    t = Transaction.query.filter_by(group_id=group_id, user_id=u.id, type='cotisation', status='pending', provider='stripe').order_by(Transaction.date.desc()).first()
    if t:
        t.status = 'approved'
        db.session.commit()
        notify_user(u.id, 'contribution_paid', f"Cotisation de {t.amount} MAD payée (Stripe)", group_id=group_id)
        notify_admins('contribution_paid', f"{u.name} a payé sa cotisation (Stripe)", group_id=group_id)
    flash('Paiement réussi')
    return redirect(url_for('dashboard'))

@app.route('/pay/stripe/cancel')
@login_required
def stripe_cancel():
    flash('Paiement annulé')
    return redirect(url_for('dashboard'))

@app.route('/notifications/stream')
@login_required
def notifications_stream():
    def event_stream(uid):
        last_id = None
        while True:
            q = Notification.query.filter_by(user_id=uid).order_by(Notification.date.desc()).limit(5).all()
            payload = [{'id': getattr(n, 'id', 0), 'message': n.message, 'date': n.date.isoformat()} for n in q]
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(3)
    return app.response_class(event_stream(g.user.id), mimetype='text/event-stream')

@app.route('/admin/users')
@role_required('admin')
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<int:id>')
@role_required('admin')
def admin_user_detail(id):
    u = User.query.get_or_404(id)
    groups = [m.group for m in Membership.query.filter_by(user_id=id).all()]
    cotisations = Transaction.query.filter_by(user_id=id, type='cotisation', status='approved').order_by(Transaction.date.desc()).all()
    aides = Transaction.query.filter_by(user_id=id, type='aide').order_by(Transaction.date.desc()).all()
    return render_template('admin_user_detail.html', user_detail=u, groups=groups, cotisations=cotisations, aides=aides)

@app.route('/admin/user/<int:id>/block', methods=['POST'])
@role_required('admin')
def admin_user_block(id):
    u = User.query.get_or_404(id)
    u.is_blocked = True
    db.session.commit()
    flash('Utilisateur bloqué')
    return redirect(url_for('admin_users'))

def calculate_group_stats(group, start_date='', end_date=''):
    """Calculate statistics for a specific group"""
    from datetime import datetime, timedelta
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        except Exception:
            pass
    
    # Get all members
    members = Membership.query.filter_by(group_id=group.id).all()
    total_members = len(members)
    
    # Get active members (those who have paid in the last 3 months)
    active_threshold = datetime.utcnow() - timedelta(days=90)
    active_members = Membership.query.filter(
        Membership.group_id == group.id,
        Membership.joined_at >= active_threshold
    ).count()
    
    # Calculate activity rate
    activity_rate = (active_members / total_members * 100) if total_members > 0 else 0
    
    # Get transactions with filters
    tx_query = Transaction.query.filter_by(group_id=group.id)
    
    # Apply date filters
    if start_dt:
        tx_query = tx_query.filter(Transaction.date >= start_dt)
    if end_dt:
        tx_query = tx_query.filter(Transaction.date <= end_dt)
    
    # Get approved contributions
    contributions = tx_query.filter(
        Transaction.type == 'cotisation',
        Transaction.status == 'approved'
    ).all()
    
    # Get approved aids
    aids = tx_query.filter(
        Transaction.type == 'aide',
        Transaction.status == 'approved'
    ).all()
    
    # Calculate totals
    total_contributions = sum(t.amount for t in contributions)
    total_aids = sum(t.amount for t in aids)
    
    # Get current group balance
    current_balance = group_balance(group.id)
    
    # Get contributions this month
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    monthly_contributions = Transaction.query.filter(
        Transaction.group_id == group.id,
        Transaction.type == 'cotisation',
        Transaction.status == 'approved',
        Transaction.date >= start_of_month
    ).count()
    
    # Get total aid requests
    total_aid_requests = Transaction.query.filter(
        Transaction.group_id == group.id,
        Transaction.type == 'aide'
    ).count()
    
    return {
        'total_members': total_members,
        'current_balance': current_balance,
        'total_contributions': total_contributions,
        'monthly_contributions': monthly_contributions,
        'total_aid_requests': total_aid_requests,
        'total_aids': total_aids,
        'activity_rate': round(activity_rate, 1)
    }

def get_group_transactions(group, start_date='', end_date=''):
    """Get transaction data for charts and table"""
    from datetime import datetime, timedelta
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        except Exception:
            pass
    
    # Get transactions with filters
    tx_query = Transaction.query.filter_by(group_id=group.id)
    
    # Apply date filters
    if start_dt:
        tx_query = tx_query.filter(Transaction.date >= start_dt)
    if end_dt:
        tx_query = tx_query.filter(Transaction.date <= end_dt)
    
    # Order by date descending
    transactions = tx_query.order_by(Transaction.date.desc()).all()
    
    return transactions

def calculate_overall_stats(start_date='', end_date=''):
    """Calculate overall statistics for all groups"""
    from datetime import datetime, timedelta
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        except Exception:
            pass
    
    # Get all groups
    groups = Group.query.all()
    total_groups = len(groups)
    
    # Get all members across all groups
    total_members = Membership.query.count()
    
    # Get transactions with filters
    tx_query = Transaction.query
    
    # Apply date filters
    if start_dt:
        tx_query = tx_query.filter(Transaction.date >= start_dt)
    if end_dt:
        tx_query = tx_query.filter(Transaction.date <= end_dt)
    
    # Get approved contributions
    contributions = tx_query.filter(
        Transaction.type == 'cotisation',
        Transaction.status == 'approved'
    ).all()
    
    # Get approved aids
    aids = tx_query.filter(
        Transaction.type == 'aide',
        Transaction.status == 'approved'
    ).all()
    
    # Calculate totals
    total_contributions = sum(t.amount for t in contributions)
    total_aids = sum(t.amount for t in aids)
    
    # Get current total balance across all groups
    total_balance = sum(group_balance(g.id) for g in groups)
    
    # Get contributions this month
    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    
    monthly_tx_query = Transaction.query
    if start_dt:
        monthly_tx_query = monthly_tx_query.filter(Transaction.date >= start_dt)
    if end_dt:
        monthly_tx_query = monthly_tx_query.filter(Transaction.date <= end_dt)
    
    monthly_contributions = monthly_tx_query.filter(
        Transaction.type == 'cotisation',
        Transaction.status == 'approved',
        Transaction.date >= start_of_month
    ).count()
    
    # Get total aid requests
    aid_query = Transaction.query.filter(Transaction.type == 'aide')
    if start_dt:
        aid_query = aid_query.filter(Transaction.date >= start_dt)
    if end_dt:
        aid_query = aid_query.filter(Transaction.date <= end_dt)
    
    total_aid_requests = aid_query.count()
    
    # Calculate average activity rate (simplified)
    activity_rate = 75.0  # Placeholder - would need more complex calculation
    
    return {
        'total_groups': total_groups,
        'total_members': total_members,
        'current_balance': total_balance,
        'total_contributions': total_contributions,
        'monthly_contributions': monthly_contributions,
        'total_aid_requests': total_aid_requests,
        'total_aids': total_aids,
        'activity_rate': activity_rate
    }

def get_all_transactions(start_date='', end_date=''):
    """Get all transactions for charts and table"""
    from datetime import datetime, timedelta
    
    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except Exception:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        except Exception:
            pass
    
    # Get transactions with filters
    tx_query = Transaction.query
    
    # Apply date filters
    if start_dt:
        tx_query = tx_query.filter(Transaction.date >= start_dt)
    if end_dt:
        tx_query = tx_query.filter(Transaction.date <= end_dt)
    
    # Order by date descending
    transactions = tx_query.order_by(Transaction.date.desc()).all()
    
    return transactions

@app.route('/admin/group-statistics')
@role_required('admin')
def admin_group_statistics():
    # Get all groups
    groups = Group.query.all()
    
    # Get selected group
    group_id = request.args.get('group_id', '').strip()
    selected_group = None
    if group_id:
        try:
            selected_group = Group.query.get(int(group_id))
        except Exception:
            pass
    
    # Get date filters
    start_date = request.args.get('start', '').strip()
    end_date = request.args.get('end', '').strip()
    
    # Get group status filter
    group_status = request.args.get('group_status', 'all').strip()
    
    # Filter groups by status if needed
    if group_status == 'active':
        groups = [g for g in groups if not g.archived]
    elif group_status == 'suspended':
        groups = [g for g in groups if g.archived]
    
    # Calculate statistics
    stats = {}
    transactions_data = []
    
    if selected_group:
        # Calculate statistics for selected group
        stats = calculate_group_stats(selected_group, start_date, end_date)
        transactions_data = get_group_transactions(selected_group, start_date, end_date)
    elif not group_id:
        # Calculate overall statistics if no group selected
        stats = calculate_overall_stats(start_date, end_date)
        transactions_data = get_all_transactions(start_date, end_date)
    
    return render_template(
        'admin_group_statistics.html',
        groups=groups,
        selected_group=selected_group,
        stats=stats,
        transactions=transactions_data,
        start_date=start_date,
        end_date=end_date,
        group_status=group_status
    )

@app.route('/admin/user/<int:id>/unblock', methods=['POST'])
@role_required('admin')
def admin_user_unblock(id):
    u = User.query.get_or_404(id)
    u.is_blocked = False
    u.failed_attempts = 0
    u.lock_until = None
    db.session.commit()
    flash('Utilisateur débloqué')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:id>/make-admin', methods=['POST'])
@role_required('admin')
def admin_user_make_admin(id):
    u = User.query.get_or_404(id)
    u.role = 'admin'
    db.session.commit()
    flash('Utilisateur promu admin')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:id>/make-user', methods=['POST'])
@role_required('admin')
def admin_user_make_user(id):
    u = User.query.get_or_404(id)
    u.role = 'user'
    db.session.commit()
    flash('Utilisateur rétrogradé en user')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:id>', methods=['DELETE', 'POST'])
@role_required('admin')
def admin_user_delete(id):
    me = g.user
    target = User.query.get_or_404(id)
    if target.id == me.id:
        if request.method == 'POST':
            flash('Impossible de supprimer votre propre compte')
            return redirect(url_for('admin_users'))
        return {'error': 'cannot_delete_self'}, 400
    admin_count = User.query.filter_by(role='admin').count()
    if target.role == 'admin' and admin_count <= 1:
        if request.method == 'POST':
            flash('Impossible de supprimer le dernier admin')
            return redirect(url_for('admin_users'))
        return {'error': 'cannot_delete_last_admin'}, 400
    Membership.query.filter_by(user_id=id).delete()
    Transaction.query.filter_by(user_id=id).delete()
    Notification.query.filter_by(user_id=id).delete()
    db.session.delete(target)
    db.session.commit()
    if request.method == 'POST':
        flash('Utilisateur supprimé')
        return redirect(url_for('admin_users'))
    return {'ok': True}

@app.route('/admin/export/group-statistics.csv')
@role_required('admin')
def export_group_statistics_csv():
    from io import StringIO
    import csv
    from flask import Response
    
    # Get parameters
    group_id = request.args.get('group_id', '').strip()
    start_date = request.args.get('start', '').strip()
    end_date = request.args.get('end', '').strip()
    
    # Get transactions
    if group_id:
        try:
            group = Group.query.get(int(group_id))
            transactions = get_group_transactions(group, start_date, end_date)
        except Exception:
            transactions = []
    else:
        transactions = get_all_transactions(start_date, end_date)
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        t('admin.statistics.date'),
        t('admin.statistics.type'),
        t('admin.statistics.member'),
        t('admin.statistics.amount'),
        t('admin.statistics.status')
    ])
    
    # Write data
    for tx in transactions:
        writer.writerow([
            tx.date.strftime('%d/%m/%Y %H:%M'),
            t('admin.statistics.contribution') if tx.type == 'cotisation' else t('admin.statistics.aid'),
            tx.user.name,
            f'{tx.amount} MAD',
            t('admin.transactions.status.' + tx.status)
        ])
    
    # Return as CSV file
    csv_data = output.getvalue()
    output.close()
    
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=group-statistics.csv'}
    )

@app.route('/admin/export/group-statistics.pdf')
@role_required('admin')
def export_group_statistics_pdf():
    from io import BytesIO
    from flask import Response
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    
    # Get parameters
    group_id = request.args.get('group_id', '').strip()
    start_date = request.args.get('start', '').strip()
    end_date = request.args.get('end', '').strip()
    
    # Get transactions
    if group_id:
        try:
            group = Group.query.get(int(group_id))
            transactions = get_group_transactions(group, start_date, end_date)
        except Exception:
            transactions = []
    else:
        transactions = get_all_transactions(start_date, end_date)
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Content
    story = []
    
    # Title
    title = Paragraph(t('admin.statistics.detailed_transactions'), styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Table data
    data = [[
        t('admin.statistics.date'),
        t('admin.statistics.type'),
        t('admin.statistics.member'),
        t('admin.statistics.amount'),
        t('admin.statistics.status')
    ]]
    
    for tx in transactions:
        data.append([
            tx.date.strftime('%d/%m/%Y %H:%M'),
            t('admin.statistics.contribution') if tx.type == 'cotisation' else t('admin.statistics.aid'),
            tx.user.name,
            f'{tx.amount} MAD',
            t('admin.transactions.status.' + tx.status)
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return Response(
        pdf_data,
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=group-statistics.pdf'}
    )

@app.route('/admin/groups', methods=['GET', 'POST'])
@role_required('admin')
def admin_groups():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        monthly_val = 10
        if not name:
            flash('Nom du groupe requis')
            return redirect(url_for('admin_groups'))
        existing = Group.query.filter_by(name=name).first()
        if existing:
            flash('Nom du groupe déjà utilisé')
            return redirect(url_for('admin_groups'))
        gobj = Group(name=name, description=description, monthly_contribution=monthly_val, created_by=g.user.id)
        db.session.add(gobj)
        db.session.commit()
        flash('Groupe créé')
        notify_admins('group_created', f"Groupe '{name}' créé", group_id=gobj.id)
        return redirect(url_for('admin_groups'))
    groups = Group.query.order_by(Group.created_at.desc()).all()
    funds = {g.id: group_balance(g.id) for g in groups}
    return render_template('admin_groups.html', groups=groups, funds=funds)

@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    u = g.user
    # Delete user's transactions
    Transaction.query.filter_by(user_id=u.id).delete()
    # Delete user's memberships
    Membership.query.filter_by(user_id=u.id).delete()
    # Delete user's notifications
    Notification.query.filter_by(user_id=u.id).delete()
    # Delete the user
    db.session.delete(u)
    db.session.commit()
    flash('Votre compte a été supprimé définitivement')
    return redirect(url_for('logout'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    u = g.user
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        # Check if passwords match when changing password
        if password and password != password_confirm:
            flash('Les mots de passe ne correspondent pas')
            return redirect(url_for('profile'))
        
        if email:
            exists = User.query.filter(User.email == email, User.id != u.id).first()
            if exists:
                flash('Email déjà utilisé')
                return redirect(url_for('profile'))
            u.email = email
        if password:
            if len(password) < 6:
                flash('Mot de passe trop court (minimum 6 caractères)')
                return redirect(url_for('profile'))
            u.password_hash = generate_password_hash(password)
        db.session.commit()
        flash('Profil mis à jour avec succès')
        return redirect(url_for('profile'))
    
    # Prepare statistics data based on user role
    if u.role == 'user':
        # User statistics
        total_contributions = sum(t.amount for t in Transaction.query.filter_by(user_id=u.id, type='cotisation', status='approved').all())
        aids_requested = Transaction.query.filter_by(user_id=u.id, type='aide').count()
        return render_template('profile.html', user=u, total_contributions=total_contributions, aids_requested=aids_requested)
    else:
        # Admin statistics
        user_count = User.query.count()
        group_count = Group.query.count()
        transaction_count = Transaction.query.count()
        
        # Calculate monthly revenue
        from datetime import datetime
        now_dt = datetime.utcnow()
        start_month = datetime(now_dt.year, now_dt.month, 1)
        monthly_revenue = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0)).filter(
            Transaction.type == 'cotisation', 
            Transaction.status == 'approved', 
            Transaction.date >= start_month
        ).scalar() or 0
        
        return render_template('profile.html', user=u, user_count=user_count, group_count=group_count, 
                             transaction_count=transaction_count, monthly_revenue=monthly_revenue)

@app.route('/admin/groups/<int:id>/delete', methods=['POST'])
@role_required('admin')
def delete_group(id):
    gobj = Group.query.get_or_404(id)
    
    # Delete related transactions
    Transaction.query.filter_by(group_id=gobj.id).delete()
    
    # Delete related memberships
    Membership.query.filter_by(group_id=gobj.id).delete()
    
    # Delete related notifications
    Notification.query.filter_by(group_id=gobj.id).delete()
    
    # Finally delete the group
    db.session.delete(gobj)
    db.session.commit()
    flash('Groupe supprimé définitivement')
    return redirect(url_for('admin_groups'))

@app.route('/admin/groups/<int:id>/activate', methods=['POST'])
@role_required('admin')
def activate_group(id):
    gobj = Group.query.get_or_404(id)
    gobj.archived = False
    db.session.commit()
    flash('Groupe activé')
    return redirect(url_for('admin_groups'))

@app.route('/admin/groups/<int:id>/suspend', methods=['POST'])
@role_required('admin')
def suspend_group(id):
    gobj = Group.query.get_or_404(id)
    gobj.archived = True
    db.session.commit()
    flash('Groupe suspendu')
    return redirect(url_for('admin_groups'))

@app.route('/admin/groups/bulk-action', methods=['POST'])
@role_required('admin')
def bulk_group_action():
    action = request.form.get('action')
    group_ids = request.form.getlist('group_ids')
    
    if not group_ids:
        flash('Aucun groupe sélectionné')
        return redirect(url_for('admin_groups'))
    
    # Convert string IDs to integers
    group_ids = [int(id) for id in group_ids]
    
    # Get all selected groups
    groups = Group.query.filter(Group.id.in_(group_ids)).all()
    
    if action == 'delete':
        # Delete all selected groups permanently
        for group in groups:
            # Delete related transactions
            Transaction.query.filter_by(group_id=group.id).delete()
            
            # Delete related memberships
            Membership.query.filter_by(group_id=group.id).delete()
            
            # Delete related notifications
            Notification.query.filter_by(group_id=group.id).delete()
            
            # Finally delete the group
            db.session.delete(group)
        db.session.commit()
        flash(f'{len(groups)} groupe(s) supprimé(s) définitivement')
    elif action == 'activate':
        # Activate all selected groups
        for group in groups:
            group.archived = False
        db.session.commit()
        flash(f'{len(groups)} groupe(s) activé(s)')
    elif action == 'suspend':
        # Suspend all selected groups
        for group in groups:
            group.archived = True
        db.session.commit()
        flash(f'{len(groups)} groupe(s) suspendu(s)')
    else:
        flash('Action non reconnue')
    
    return redirect(url_for('admin_groups'))

@app.route('/set_language/<lang_code>')
def set_language_route(lang_code):
    set_language(lang_code)
    # Redirect back to the previous page or home
    referer = request.headers.get('Referer')
    if referer:
        return redirect(referer)
    return redirect(url_for('home'))

@app.context_processor
def inject_i18n():
    return dict(
        t=t,
        current_language=get_current_language(),
        available_languages=get_available_languages(),
        language_direction=get_language_direction()
    )

@app.route('/ai_assistant', methods=['POST'])
def ai_assistant_endpoint():
    """Endpoint for AI assistant queries."""
    question = request.form.get('question', '').strip()
    if not question:
        return {'response': t('ai_assistant.placeholder')}
    
    # Get response from AI assistant
    response = ai_assistant.get_response(question)
    
    # Log the question and response
    app.logger.info(f'AI Assistant Query: {question} | Response: {response}')
    
    return {'response': response}

@app.route('/ai_suggestions')
def ai_suggestions_endpoint():
    """Endpoint for AI assistant suggestions."""
    user_role = 'admin' if g.user and g.user.role == 'admin' else 'user'
    suggestions = ai_assistant.get_suggestions(user_role)
    return {'suggestions': suggestions}

with app.app_context():
    db.create_all()
    def column_exists(table, column):
        try:
            rows = db.session.execute(text(f"PRAGMA table_info('{table}')")).mappings().all()
            return any(r.get('name') == column for r in rows)
        except Exception:
            return False
    try:
        if not column_exists('transaction', 'provider'):
            db.session.execute(text("ALTER TABLE 'transaction' ADD COLUMN provider VARCHAR(20)"))
        if not column_exists('transaction', 'external_id'):
            db.session.execute(text("ALTER TABLE 'transaction' ADD COLUMN external_id VARCHAR(120)"))
        if not column_exists('group', 'archived'):
            db.session.execute(text("ALTER TABLE 'group' ADD COLUMN archived BOOLEAN DEFAULT 0"))
        if not column_exists('membership', 'auto_pay'):
            db.session.execute(text("ALTER TABLE 'membership' ADD COLUMN auto_pay BOOLEAN DEFAULT 1"))
        if not column_exists('user', 'failed_attempts'):
            db.session.execute(text("ALTER TABLE 'user' ADD COLUMN failed_attempts INTEGER DEFAULT 0"))
        if not column_exists('user', 'lock_until'):
            db.session.execute(text("ALTER TABLE 'user' ADD COLUMN lock_until DATETIME"))
        if not column_exists('user', 'is_blocked'):
            db.session.execute(text("ALTER TABLE 'user' ADD COLUMN is_blocked BOOLEAN DEFAULT 0"))
        if not column_exists('transaction', 'reason'):
            db.session.execute(text("ALTER TABLE 'transaction' ADD COLUMN reason TEXT"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    admin_email = 'admin@mytakaful.com'
    try:
        existing_admin = User.query.filter_by(email=admin_email, role='admin').first()
    except Exception:
        db.drop_all()
        db.create_all()
        try:
            if not column_exists('transaction', 'provider'):
                db.session.execute(text("ALTER TABLE 'transaction' ADD COLUMN provider VARCHAR(20)"))
            if not column_exists('transaction', 'external_id'):
                db.session.execute(text("ALTER TABLE 'transaction' ADD COLUMN external_id VARCHAR(120)"))
            if not column_exists('group', 'archived'):
                db.session.execute(text("ALTER TABLE 'group' ADD COLUMN archived BOOLEAN DEFAULT 0"))
            if not column_exists('membership', 'auto_pay'):
                db.session.execute(text("ALTER TABLE 'membership' ADD COLUMN auto_pay BOOLEAN DEFAULT 1"))
            if not column_exists('user', 'failed_attempts'):
                db.session.execute(text("ALTER TABLE 'user' ADD COLUMN failed_attempts INTEGER DEFAULT 0"))
            if not column_exists('user', 'lock_until'):
                db.session.execute(text("ALTER TABLE 'user' ADD COLUMN lock_until DATETIME"))
            if not column_exists('user', 'is_blocked'):
                db.session.execute(text("ALTER TABLE 'user' ADD COLUMN is_blocked BOOLEAN DEFAULT 0"))
            if not column_exists('transaction', 'reason'):
                db.session.execute(text("ALTER TABLE 'transaction' ADD COLUMN reason TEXT"))
            db.session.commit()
        except Exception:
            db.session.rollback()
        existing_admin = None
    if not existing_admin:
        admin_user = User(name='admin', email=admin_email, password_hash=generate_password_hash('admin123'), role='admin')
        db.session.add(admin_user)
        db.session.commit()

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    def generate_monthly_contributions():
        with app.app_context():
            groups = Group.query.filter_by(archived=False).all()
            for gobj in groups:
                members = Membership.query.filter_by(group_id=gobj.id, auto_pay=True).all()
                for m in members:
                    last = Transaction.query.filter_by(group_id=gobj.id, user_id=m.user_id, type='cotisation').order_by(Transaction.date.desc()).first()
                    due = True
                    if last:
                        delta = (datetime.utcnow() - last.date).days
                        due = delta >= 30
                    if due:
                        t = Transaction(group_id=gobj.id, user_id=m.user_id, amount=gobj.monthly_contribution, type='cotisation', status='pending', provider=None)
                        db.session.add(t)
                        db.session.commit()
                        notify_user(m.user_id, 'contribution_due', f"Cotisation de {gobj.monthly_contribution} MAD due pour {gobj.name}", group_id=gobj.id)
    scheduler.add_job(generate_monthly_contributions, 'interval', minutes=5, id='monthly_contrib')
    scheduler.start()
except Exception:
    pass

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
