from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from urllib.parse import urlparse

from app.extensions import db
from app.models import User


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        first_name = (request.form.get('first_name') or '').strip()
        last_name = (request.form.get('last_name') or '').strip()
        password = request.form.get('password') or ''
        if (
            len(email) > 150 or '@' not in email or '.' not in email.rsplit('@', 1)[-1]
            or not first_name or len(first_name) > 80
            or not last_name or len(last_name) > 80 or len(password) < 8
        ):
            flash('Please provide valid registration details.', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')
        user = User(email=email, first_name=first_name, last_name=last_name)
        user.password = password
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registration successful.', 'success')
        return redirect(url_for('home'))
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if user and not user.is_suspended and user.verify_password(password):
            login_user(user)
            session['lang'] = session.get('lang', 'en')
            next_url = request.args.get('next', '')
            parsed = urlparse(next_url)
            if parsed.scheme or parsed.netloc:
                next_url = ''
            return redirect(next_url or url_for('home'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'success')
    return redirect(url_for('home'))
