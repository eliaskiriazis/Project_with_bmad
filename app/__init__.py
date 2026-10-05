import click
from flask import Flask, redirect, request, session, url_for
from flask_login import current_user
from sqlalchemy import inspect, text

from app.extensions import csrf, db, login_manager
from app.models import User
from app.auth import auth_bp
from app.listings import listings_bp
from app.orders import orders_bp
from app.messaging import messaging_bp
from app.notifications import notifications_bp
from app.admin import admin_bp
from app.payments import payments_bp
from app.webhooks import webhooks_bp
from app.i18n import get_translation


def _upgrade_sqlite_schema():
    additions = {
        'users': {'country_code': 'VARCHAR(2)'},
        'listings': {'photo_paths': "TEXT DEFAULT ''"},
        'orders': {
            'fulfillment_method': 'VARCHAR(20)',
            'shipping_details': 'TEXT',
        },
    }
    inspector = inspect(db.engine)
    for table, columns in additions.items():
        existing = {column['name'] for column in inspector.get_columns(table)}
        for name, definition in columns.items():
            if name not in existing:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
    db.session.commit()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('config.DevConfig')
    if test_config:
        app.config.from_object(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.context_processor
    def inject_translations():
        return {'tr': get_translation}

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(User, int(user_id))
        return user if user and not user.is_suspended else None

    app.register_blueprint(auth_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(messaging_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(webhooks_bp)

    @app.before_request
    def set_language():
        if 'lang' in request.args:
            if request.args['lang'] in ('en', 'el'):
                session['lang'] = request.args['lang']
        elif 'lang' not in session:
            session['lang'] = app.config.get('DEFAULT_LANGUAGE', 'en')

    @app.route('/')
    def home():
        from app.listings import listing_search_query
        return listing_search_query()

    @app.route('/set-language/<lang>')
    def set_language_route(lang):
        if lang in ('en', 'el'):
            session['lang'] = lang
        return redirect(url_for('home'))

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/dashboard')
    def dashboard():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        from app.orders import get_dashboard_data
        return get_dashboard_data(current_user.id)

    with app.app_context():
        db.create_all()
        if db.engine.dialect.name == 'sqlite':
            _upgrade_sqlite_schema()

    @app.cli.command('promote-admin')
    @click.argument('email')
    def promote_admin(email):
        """Grant administrator access to an existing user."""
        user = User.query.filter_by(email=email.strip().lower()).first()
        if user is None:
            raise click.ClickException('No account exists for that email.')
        user.is_admin = True
        db.session.commit()
        print(f'Administrator access granted to {user.email}.')

    return app
