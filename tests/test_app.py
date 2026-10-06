from datetime import datetime, timedelta
from io import BytesIO
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app import create_app
from app.extensions import db
from app.models import Listing, Notification, Order, Report, User
from config import DevConfig


@pytest.fixture
def client():
    app = create_app(test_config='config.TestConfig')
    app.config.update(
        PLATFORM_COMMISSION_PERCENT='12',
        STRIPE_SECRET_KEY='sk_test_unit_test',
        STRIPE_WEBHOOK_SECRET='whsec_unit_test',
        BASE_URL='https://marketplace.example.test',
    )
    with app.test_client() as test_client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            seller = User(
                email='seller@example.com',
                first_name='Seller',
                last_name='User',
                stripe_connect_account_id='acct_seller',
                seller_onboarded=True,
            )
            seller.password = 'secret1234'
            admin = User(
                email='admin@example.com', first_name='Admin', last_name='User',
                is_admin=True,
            )
            admin.password = 'secret1234'
            db.session.add_all([seller, admin])
            db.session.flush()
            listing = Listing(
                seller_id=seller.id,
                title='Ibanez RG',
                description='Great condition',
                brand='Ibanez',
                model='RG550',
                condition='Excellent',
                price_cents=150000,
                shipping_fee_cents=1500,
                fulfillment='shipping_or_pickup',
            )
            db.session.add(listing)
            db.session.commit()
        yield test_client
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _login(client, email='seller@example.com'):
    with client.application.app_context():
        user_id = User.query.filter_by(email=email).first().id
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
    return user_id


def _create_order(client, *, guest=True, session_id='cs_test_123'):
    with client.application.app_context():
        seller = User.query.filter_by(email='seller@example.com').first()
        listing = Listing.query.first()
        order = Order(
            listing_id=listing.id,
            buyer_id=None,
            seller_id=seller.id,
            guest_email='guest@example.com' if guest else None,
            total_cents=151500,
            shipping_fee_cents=1500,
            fulfillment_method='shipping',
            commission_cents=18000,
            checkout_session_id=session_id,
            status='reserved',
            reserved_until=datetime.utcnow() + timedelta(minutes=20),
        )
        listing.reserved_until = order.reserved_until
        db.session.add(order)
        db.session.commit()
        return order.id


def _session_event(order_id, *, event_id='evt_test_1', amount=151500, paid='paid'):
    return {
        'id': event_id,
        'type': 'checkout.session.completed',
        'livemode': False,
        'account': 'acct_seller',
        'data': {'object': {
            'id': 'cs_test_123',
            'payment_status': paid,
            'amount_total': amount,
            'currency': 'eur',
            'client_reference_id': str(order_id),
            'metadata': {'order_id': str(order_id)},
            'shipping_details': {
                'name': 'Guest Buyer',
                'address': {'line1': '1 Main Street', 'country': 'GR'},
            },
        }},
    }


def test_existing_sqlite_schema_is_upgraded_without_losing_records(tmp_path):
    database = tmp_path / 'legacy.sqlite'
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, email VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL, first_name VARCHAR(80) NOT NULL,
            last_name VARCHAR(80) NOT NULL, is_admin BOOLEAN DEFAULT 0,
            stripe_connect_account_id VARCHAR(255), seller_onboarded BOOLEAN DEFAULT 0,
            is_suspended BOOLEAN DEFAULT 0, created_at DATETIME
        );
        CREATE TABLE listings (
            id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL, title VARCHAR(180) NOT NULL,
            description TEXT NOT NULL, brand VARCHAR(80) NOT NULL, model VARCHAR(100) NOT NULL,
            condition VARCHAR(40) NOT NULL, price_cents INTEGER NOT NULL,
            shipping_fee_cents INTEGER DEFAULT 0, fulfillment VARCHAR(200) NOT NULL,
            is_active BOOLEAN DEFAULT 1, is_hidden BOOLEAN DEFAULT 0,
            reserved_until DATETIME, created_at DATETIME
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY, listing_id INTEGER NOT NULL, buyer_id INTEGER,
            seller_id INTEGER NOT NULL, guest_email VARCHAR(150), status VARCHAR(40),
            total_cents INTEGER NOT NULL, shipping_fee_cents INTEGER DEFAULT 0,
            commission_cents INTEGER DEFAULT 0,
            checkout_session_id VARCHAR(255), payment_event_id VARCHAR(255),
            reserved_until DATETIME, created_at DATETIME, updated_at DATETIME
        );
        INSERT INTO users (id, email, password_hash, first_name, last_name)
        VALUES (1, 'legacy@example.com', 'hash', 'Legacy', 'Seller');
    """)
    connection.commit()
    connection.close()

    app = create_app(SimpleNamespace(
        TESTING=True,
        SECRET_KEY='migration-test-secret',
        SQLALCHEMY_DATABASE_URI=f'sqlite:///{database.as_posix()}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    ))
    with app.app_context():
        connection = sqlite3.connect(database)
        try:
            columns = {
                table: {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
                for table in ('users', 'listings', 'orders')
            }
            assert 'country_code' in columns['users']
            assert 'photo_paths' in columns['listings']
            assert {'fulfillment_method', 'shipping_details'} <= columns['orders']
            assert connection.execute(
                "SELECT email FROM users WHERE id=1"
            ).fetchone() == ('legacy@example.com',)
        finally:
            connection.close()


def test_public_search_and_greek_language(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Ibanez RG' in response.data
    assert client.get('/?lang=el').status_code == 200
    assert 'Αναζήτηση κιθαρών'.encode() in client.get('/').data
    filtered = client.get('/?brand=ibanez&condition=Excellent&max_price=2000&fulfillment=shipping')
    assert b'Ibanez RG' in filtered.data
    empty = client.get('/?lang=en&brand=not-a-real-brand')
    assert empty.status_code == 200
    assert b'No listings found.' in empty.data
    assert b'class="hero-visual"' in empty.data


def test_homepage_shows_six_browse_only_demo_guitars_in_both_languages(client):
    english = client.get('/')
    assert english.status_code == 200
    assert english.data.count(b'class="card demo-card"') == 6
    assert english.data.count(b'Demo only') == 6
    assert english.data.count(b'<img ') >= 6
    assert b'class="hero-visual"' in english.data
    assert b'guitar-detail-hero.jpg' in english.data
    assert b'thomann.com' not in english.data.lower()
    assert b'aria-label="Main navigation"' in english.data
    assert b'/demo-listings/ibanez-rg3250mz' in english.data
    assert b'/demo-listings/jackson-dinky' in english.data
    assert b'ATTRIBUTION.md' in english.data

    greek = client.get('/?lang=el')
    assert greek.status_code == 200
    assert greek.data.count('Μόνο για επίδειξη'.encode()) == 6
    assert 'Άριστη'.encode() in greek.data
    assert 'Κοντινή φωτογραφία ηλεκτρικής κιθάρας'.encode() in greek.data


def test_homepage_responsive_and_keyboard_focus_styles_are_available(client):
    stylesheet = client.get('/static/css/style.css')
    assert stylesheet.status_code == 200
    assert b'@media (max-width: 560px)' in stylesheet.data
    assert b'.home-page :focus-visible' in stylesheet.data
    assert b'.home-page .demo-card .card-image-link' in stylesheet.data
    assert b'object-fit: contain' in stylesheet.data
    assert b'@media (prefers-reduced-motion: reduce)' in stylesheet.data


def test_auth_pages_share_translated_premium_layout_and_preserve_forms(client):
    page_expectations = {
        '/login': {
            'en': (b'Login', (b'name="email"', b'name="password"')),
            'el': ('Σύνδεση'.encode(), (b'name="email"', b'name="password"')),
        },
        '/register': {
            'en': (b'Register', (
                b'name="first_name"', b'name="last_name"',
                b'name="email"', b'name="password"',
            )),
            'el': ('Εγγραφή'.encode(), (
                b'name="first_name"', b'name="last_name"',
                b'name="email"', b'name="password"',
            )),
        },
    }

    for path, languages in page_expectations.items():
        for language, (heading, fields) in languages.items():
            response = client.get(f'{path}?lang={language}')
            assert response.status_code == 200
            assert b'<body class="auth-page">' in response.data
            assert b'class="auth-layout"' in response.data
            assert b'class="auth-story-panel"' in response.data
            assert b'class="auth-form-panel"' in response.data
            assert heading in response.data
            story_title = (
                'Η αγορά των μουσικών'.encode()
                if language == 'el' else 'The players’ marketplace'.encode()
            )
            assert story_title in response.data
            assert all(field in response.data for field in fields)
            assert b'name="csrf_token"' in response.data

    stylesheet = client.get('/static/css/style.css')
    assert b'.auth-layout' in stylesheet.data
    assert b'.auth-form-panel :focus-visible' in stylesheet.data
    assert b'.auth-page' in stylesheet.data
    assert b'@media (max-width: 760px)' in stylesheet.data
    assert b'grid-template-columns: 1fr' in stylesheet.data
    assert b'@media (max-width: 640px)' in stylesheet.data
    assert b'@media (prefers-reduced-motion: reduce)' in stylesheet.data

    invalid_register = client.post('/register?lang=en', data={
        'first_name': '', 'last_name': 'User',
        'email': 'not-an-email', 'password': 'short',
    })
    assert invalid_register.status_code == 200
    assert b'Please provide valid registration details.' in invalid_register.data
    invalid_login = client.post(
        '/login?lang=en', data={'email': 'missing@example.com', 'password': 'wrong'},
    )
    assert invalid_login.status_code == 200
    assert b'Invalid email or password.' in invalid_login.data


def test_demo_listing_detail_is_browse_only_and_searchable(client):
    detail = client.get('/demo-listings/ibanez-rg3250mz')
    assert detail.status_code == 200
    assert b'Ibanez RG3250MZ Prestige' in detail.data
    assert b'Demo listing \xc2\xb7 Not for sale' in detail.data
    assert b'Checkout' not in detail.data
    assert b'/checkout/' not in detail.data
    greek_detail = client.get('/demo-listings/ibanez-rg3250mz?lang=el')
    assert 'Δοκιμαστική αγγελία · Δεν διατίθεται προς πώληση'.encode() in greek_detail.data
    assert 'Άριστη'.encode() in greek_detail.data
    credits = client.get('/static/images/demos/ATTRIBUTION.md')
    assert credits.status_code == 200
    assert b'CC BY 2.0' in credits.data
    assert b'CC BY-SA 4.0' in credits.data

    filtered = client.get('/?brand=ESP')
    assert filtered.status_code == 200
    assert filtered.data.count(b'class="card demo-card"') == 1
    assert b'ESP Iron Cross' in filtered.data
    assert b'Ibanez RG3250MZ Prestige' not in filtered.data

    fulfillment_filtered = client.get('/?fulfillment=Shipping%20or%20pickup')
    assert fulfillment_filtered.status_code == 200
    assert fulfillment_filtered.data.count(b'class="card demo-card"') == 3
    assert b'Ibanez RG' in fulfillment_filtered.data

    greek_fulfillment = client.get('/?fulfillment=Αποστολή%20ή%20παραλαβή')
    assert greek_fulfillment.status_code == 200
    assert greek_fulfillment.data.count(b'class="card demo-card"') == 3

    assert client.post('/checkout/demo/ibanez-rg3250mz').status_code == 404
    with client.application.app_context():
        assert Order.query.count() == 0


def test_registration_and_login_reject_open_redirect(client):
    response = client.post('/register', data={
        'first_name': 'Buyer', 'last_name': 'User',
        'email': 'buyer@example.com', 'password': 'supersecure',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Registration successful.' in response.data
    response = client.post(
        '/login?next=https://attacker.example',
        data={'email': 'buyer@example.com', 'password': 'supersecure'},
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')


def test_checkout_requires_real_test_credentials_and_config(client):
    client.application.config['STRIPE_SECRET_KEY'] = None
    response = client.post(
        '/checkout/1', data={
            'guest_email': 'guest@example.com', 'fulfillment_method': 'shipping',
        }, follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'Checkout could not be started' in response.data
    with client.application.app_context():
        assert Order.query.count() == 1
        assert Order.query.first().status == 'cancelled'


def test_checkout_creates_stripe_direct_charge_test_session(client):
    created = {}

    def create_session(**kwargs):
        created.update(kwargs)
        return {
            'id': 'cs_test_123',
            'url': 'https://checkout.stripe.com/c/pay/cs_test_123',
        }

    with patch('app.payments.stripe.checkout.Session.create', side_effect=create_session):
        response = client.post('/checkout/1', data={
            'guest_email': 'guest@example.com', 'fulfillment_method': 'shipping',
        })
    assert response.status_code == 303
    assert response.headers['Location'] == 'https://checkout.stripe.com/c/pay/cs_test_123'
    assert created['stripe_account'] == 'acct_seller'
    assert created['line_items'][0]['price_data']['unit_amount'] == 150000
    assert created['line_items'][1]['price_data']['unit_amount'] == 1500
    assert created['payment_intent_data']['application_fee_amount'] == 18000
    assert 'GR' in created['shipping_address_collection']['allowed_countries']
    with client.application.app_context():
        order = Order.query.first()
        assert order.status == 'reserved'
        assert order.total_cents == 151500
        assert order.fulfillment_method == 'shipping'


def test_checkout_rejects_invalid_commission_and_self_purchase(client):
    client.application.config['PLATFORM_COMMISSION_PERCENT'] = ''
    response = client.post('/checkout/1', data={
        'guest_email': 'guest@example.com', 'fulfillment_method': 'pickup',
    }, follow_redirects=True)
    assert b'valid commission percentage' in response.data.lower()
    with client.application.app_context():
        assert Order.query.count() == 0
    _login(client)
    response = client.post(
        '/checkout/1', data={'fulfillment_method': 'pickup'}, follow_redirects=True
    )
    assert b'own listing' in response.data.lower()


def test_second_checkout_cannot_reserve_listing(client):
    with patch(
        'app.payments.stripe.checkout.Session.create',
        return_value={'id': 'cs_test_123', 'url': 'https://checkout.stripe.test/session'},
    ):
        first = client.post('/checkout/1', data={
            'guest_email': 'buyer@example.com', 'fulfillment_method': 'pickup',
        }, follow_redirects=False)
    assert first.status_code == 303
    second = client.post('/checkout/1', data={
        'guest_email': 'other@example.com', 'fulfillment_method': 'shipping',
    }, follow_redirects=True)
    assert b'already reserved' in second.data.lower()
    with client.application.app_context():
        assert Order.query.count() == 1


def test_payment_webhook_requires_valid_signature(client):
    response = client.post('/webhooks/stripe', json={'type': 'checkout.session.completed'})
    assert response.status_code == 400
    with client.application.app_context():
        current_app = client.application
        current_app.config['STRIPE_WEBHOOK_SECRET'] = None
    response = client.post('/webhooks/stripe', data=b'{}')
    assert response.status_code == 503


def test_verified_payment_marks_order_once_and_notifies_parties(client):
    order_id = _create_order(client)
    event = _session_event(order_id)
    with patch('app.webhooks.stripe.Webhook.construct_event', return_value=event):
        response = client.post(
            '/webhooks/stripe', data=b'signed payload',
            headers={'Stripe-Signature': 't=0,v1=test'},
        )
        assert response.status_code == 200
        duplicate = client.post(
            '/webhooks/stripe', data=b'signed payload',
            headers={'Stripe-Signature': 't=0,v1=test'},
        )
    assert duplicate.get_json()['status'] == 'already processed'
    with client.application.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == 'paid'
        assert order.listing.is_active is False
        assert Notification.query.count() == 1


def test_webhook_rejects_unpaid_or_amount_mismatch(client):
    order_id = _create_order(client)
    for event in (
        _session_event(order_id, event_id='evt_unpaid', paid='unpaid'),
        _session_event(order_id, event_id='evt_amount', amount=1),
    ):
        with patch('app.webhooks.stripe.Webhook.construct_event', return_value=event):
            response = client.post(
                '/webhooks/stripe', data=b'signed payload',
                headers={'Stripe-Signature': 't=0,v1=test'},
            )
        assert response.status_code == 400
    with client.application.app_context():
        assert db.session.get(Order, order_id).status == 'reserved'


def test_expired_connect_checkout_releases_listing_reservation(client):
    order_id = _create_order(client)
    event = _session_event(order_id)
    event['id'] = 'evt_expired'
    event['type'] = 'checkout.session.expired'
    with patch('app.webhooks.stripe.Webhook.construct_event', return_value=event):
        response = client.post(
            '/webhooks/stripe', data=b'signed payload',
            headers={'Stripe-Signature': 't=0,v1=test'},
        )
    assert response.status_code == 200
    with client.application.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == 'cancelled'
        assert order.listing.reserved_until is None


def test_old_expired_checkout_does_not_release_new_reservation(client):
    order_id = _create_order(client)
    with client.application.app_context():
        old_order = db.session.get(Order, order_id)
        newer_reservation = old_order.reserved_until + timedelta(minutes=1)
        old_order.listing.reserved_until = newer_reservation
        db.session.commit()
    event = _session_event(order_id)
    event['id'] = 'evt_old_expired'
    event['type'] = 'checkout.session.expired'
    with patch('app.webhooks.stripe.Webhook.construct_event', return_value=event):
        response = client.post(
            '/webhooks/stripe', data=b'signed payload',
            headers={'Stripe-Signature': 't=0,v1=test'},
        )
    assert response.status_code == 200
    with client.application.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == 'cancelled'
        assert order.listing.reserved_until == newer_reservation


def test_async_payment_failure_releases_its_reservation(client):
    order_id = _create_order(client)
    event = _session_event(order_id)
    event['id'] = 'evt_async_failed'
    event['type'] = 'checkout.session.async_payment_failed'
    with (
        patch('app.webhooks.stripe.Webhook.construct_event', return_value=event),
        patch('app.webhooks.send_email') as send_email,
    ):
        response = client.post(
            '/webhooks/stripe', data=b'signed payload',
            headers={'Stripe-Signature': 't=0,v1=test'},
        )
    assert response.status_code == 200
    with client.application.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == 'cancelled'
        assert order.listing.reserved_until is None
        assert Notification.query.count() == 0
    send_email.assert_called_once_with(
        'guest@example.com',
        f'Payment failed for order #{order_id}',
        f'Payment failed for order #{order_id}. You may try checkout again.',
    )


def test_live_mode_payment_event_is_rejected(client):
    order_id = _create_order(client)
    event = _session_event(order_id)
    event['livemode'] = True
    with patch('app.webhooks.stripe.Webhook.construct_event', return_value=event):
        response = client.post(
            '/webhooks/stripe', data=b'signed payload',
            headers={'Stripe-Signature': 't=0,v1=test'},
        )
    assert response.status_code == 400
    with client.application.app_context():
        assert db.session.get(Order, order_id).status == 'reserved'


def test_connect_account_event_updates_seller_onboarding(client):
    event = {
        'id': 'evt_account_updated',
        'type': 'account.updated',
        'livemode': False,
        'data': {'object': {
            'id': 'acct_seller',
            'details_submitted': True,
            'charges_enabled': True,
            'payouts_enabled': True,
        }},
    }
    with client.application.app_context():
        seller = User.query.filter_by(email='seller@example.com').first()
        seller.seller_onboarded = False
        db.session.commit()
    with patch('app.webhooks.stripe.Webhook.construct_event', return_value=event):
        response = client.post(
            '/webhooks/stripe', data=b'signed payload',
            headers={'Stripe-Signature': 't=0,v1=test'},
        )
    assert response.status_code == 200
    with client.application.app_context():
        assert User.query.filter_by(email='seller@example.com').one().seller_onboarded


def test_guest_cannot_open_order_details(client):
    order_id = _create_order(client)
    response = client.get(f'/orders/{order_id}')
    assert response.status_code == 302
    assert f'/orders/{order_id}' not in response.headers['Location']


def test_authenticated_listing_report_and_admin_hide(client):
    reporter_id = _login(client, 'admin@example.com')
    response = client.post('/listings/1/report', data={'reason': 'Needs review'})
    assert response.status_code == 302
    response = client.post('/listings/1/report', data={'reason': 'Duplicate report'})
    assert response.status_code == 302
    response = client.post('/listings/1/report', data={'reason': 'x' * 2001})
    assert response.status_code == 302
    with client.application.app_context():
        report = Report.query.one()
        assert report.reporter_id == reporter_id
    response = client.post('/admin/reports/1/hide')
    assert response.status_code == 302
    with client.application.app_context():
        assert Listing.query.first().is_hidden is True


def test_admin_suspension_disables_seller_and_blocks_login(client):
    _login(client, 'admin@example.com')
    client.post('/listings/1/report', data={'reason': 'Needs review'})
    response = client.post('/admin/reports/1/suspend')
    assert response.status_code == 302
    with client.application.app_context():
        seller = User.query.filter_by(email='seller@example.com').one()
        assert seller.is_suspended is True
        assert all(not listing.is_active and listing.is_hidden for listing in seller.listings)
        assert Report.query.one().status == 'resolved'
    client.post('/logout')
    response = client.post('/login', data={
        'email': 'seller@example.com', 'password': 'secret1234',
    })
    assert response.status_code == 200
    assert b'Invalid email or password.' in response.data


def test_listing_rejects_amounts_above_supported_checkout_limit(client):
    _login(client)
    response = client.post('/sell', data={
        'title': 'Expensive guitar', 'brand': 'Fender', 'model': 'Custom',
        'condition': 'Good', 'description': 'Used', 'electric_guitar': 'yes',
        'price': '1000000.00', 'shipping_fee': '0', 'fulfillment': 'pickup',
    }, follow_redirects=True)
    assert b'Please enter valid EUR amounts.' in response.data
    with client.application.app_context():
        assert Listing.query.count() == 1


def test_listing_rejects_total_above_supported_checkout_limit(client):
    _login(client)
    response = client.post('/sell', data={
        'title': 'Expensive guitar', 'brand': 'Fender', 'model': 'Custom',
        'condition': 'Good', 'description': 'Used', 'electric_guitar': 'yes',
        'price': '999000.00', 'shipping_fee': '1000.00', 'fulfillment': 'shipping',
    }, follow_redirects=True)
    assert b'Item and shipping exceed the maximum checkout amount.' in response.data
    with client.application.app_context():
        assert Listing.query.count() == 1


def test_checkout_page_discloses_test_mode(client):
    response = client.get('/checkout/1')
    assert b'Test-mode checkout only' in response.data
    assert b'No real payments are processed' in response.data


def test_development_configuration_does_not_enable_debugger():
    assert DevConfig.DEBUG is False
    assert DevConfig.MAX_CONTENT_LENGTH >= 8 * 5 * 1024 * 1024 + 2 * 1024 * 1024


def test_listing_photos_required_for_publication(client):
    _login(client)
    response = client.post('/sell', data={
        'title': 'Guitar', 'brand': 'Fender', 'model': 'Strat',
        'condition': 'Good', 'description': 'Used', 'price': '100.00',
        'shipping_fee': '0', 'fulfillment': 'pickup', 'electric_guitar': 'yes',
    }, follow_redirects=True)
    assert b'photo is required' in response.data.lower()


def test_valid_listing_publishes_photo_and_appears_in_search(client, tmp_path):
    _login(client)
    client.application.config['UPLOAD_FOLDER'] = str(tmp_path)
    response = client.post('/sell', data={
        'title': 'Telecaster', 'brand': 'Fender', 'model': 'Player',
        'condition': 'Very Good', 'description': 'A bright sounding guitar',
        'electric_guitar': 'yes',
        'price': '699.99', 'shipping_fee': '12.50', 'fulfillment': 'shipping',
        'photos': (BytesIO(b'\xff\xd8\xff\x00fake-jpeg'), 'front.jpg'),
    }, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'Telecaster' in response.data
    result = client.get('/?keyword=Telecaster&max_price=700')
    assert b'Telecaster' in result.data
    with client.application.app_context():
        listing = Listing.query.filter_by(title='Telecaster').one()
        assert listing.price_cents == 69999
        assert listing.photo_list and (tmp_path / listing.photo_list[0]).exists()


def test_seller_connect_onboarding_uses_test_mode(client):
    from types import SimpleNamespace

    _login(client)
    with client.application.app_context():
        seller = User.query.filter_by(email='seller@example.com').first()
        seller.stripe_connect_account_id = None
        seller.seller_onboarded = False
        db.session.commit()
    with patch(
        'app.payments.stripe.Account.create',
        return_value=SimpleNamespace(id='acct_new'),
    ) as create_account, patch(
        'app.payments.stripe.AccountLink.create',
        return_value=SimpleNamespace(url='https://connect.stripe.test/onboard'),
    ) as create_link:
        response = client.post('/seller/connect', data={'country_code': 'DE'})
    assert response.status_code == 302
    assert response.headers['Location'] == 'https://connect.stripe.test/onboard'
    assert create_account.call_args.kwargs['country'] == 'DE'
    assert create_link.call_args.kwargs['account'] == 'acct_new'
    with patch('app.payments.stripe.Account.create') as create_account:
        response = client.post('/seller/connect', data={'country_code': 'US'})
    assert response.status_code == 302
    create_account.assert_not_called()


def test_order_status_transitions_and_participant_messaging(client):
    with client.application.app_context():
        buyer = User(email='buyer@example.com', first_name='Buyer', last_name='User')
        buyer.password = 'password1234'
        db.session.add(buyer)
        db.session.commit()
        buyer_id = buyer.id
    order_id = _create_order(client, guest=False)
    with client.application.app_context():
        order = db.session.get(Order, order_id)
        order.buyer_id = buyer_id
        order.status = 'paid'
        db.session.commit()
    _login(client)
    response = client.post(
        f'/orders/{order_id}/update-status',
        data={'status': 'shipped'}, follow_redirects=True,
    )
    assert response.status_code == 200
    with client.session_transaction() as session:
        session.clear()
    _login(client, 'buyer@example.com')
    response = client.post(
        f'/orders/{order_id}/message',
        data={'body': 'Thanks for the update.'}, follow_redirects=True,
    )
    assert response.status_code == 200
    response = client.post(
        f'/orders/{order_id}/update-status',
        data={'status': 'completed'}, follow_redirects=True,
    )
    assert response.status_code == 200
    with client.application.app_context():
        order = db.session.get(Order, order_id)
        assert order.status == 'completed'
        assert len(order.messages) == 1
        assert Notification.query.count() >= 2


def test_post_routes_require_csrf_but_signed_webhook_is_exempt(client):
    client.application.config['WTF_CSRF_ENABLED'] = True
    response = client.post('/register', data={
        'first_name': 'Buyer', 'last_name': 'User',
        'email': 'buyer@example.com', 'password': 'password1234',
    })
    assert response.status_code == 400
    order_id = _create_order(client)
    event = _session_event(order_id)
    with patch('app.webhooks.stripe.Webhook.construct_event', return_value=event):
        response = client.post(
            '/webhooks/stripe', data=b'signed payload',
            headers={'Stripe-Signature': 't=0,v1=test'},
        )
    assert response.status_code == 200
