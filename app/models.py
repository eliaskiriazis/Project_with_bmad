from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    stripe_connect_account_id = db.Column(db.String(255), nullable=True)
    seller_onboarded = db.Column(db.Boolean, default=False)
    country_code = db.Column(db.String(2), nullable=True)
    is_suspended = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listings = db.relationship('Listing', backref='seller', lazy=True)
    orders_bought = db.relationship('Order', foreign_keys='Order.buyer_id', backref='buyer', lazy=True)
    orders_sold = db.relationship('Order', foreign_keys='Order.seller_id', backref='seller_order', lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy=True)

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, value):
        self.password_hash = generate_password_hash(value)

    def verify_password(self, value):
        return check_password_hash(self.password_hash, value)

    def __repr__(self):
        return f'<User {self.email}>'


class Listing(db.Model):
    __tablename__ = 'listings'

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    brand = db.Column(db.String(80), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.String(40), nullable=False)
    price_cents = db.Column(db.Integer, nullable=False)
    shipping_fee_cents = db.Column(db.Integer, default=0)
    fulfillment = db.Column(db.String(200), nullable=False)
    photo_paths = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    is_hidden = db.Column(db.Boolean, default=False)
    reserved_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='listing', lazy=True)
    reports = db.relationship('Report', backref='listing', lazy=True)

    @property
    def price_eur(self):
        return self.price_cents / 100

    @property
    def shipping_fee_eur(self):
        return self.shipping_fee_cents / 100

    @property
    def photo_list(self):
        return [path for path in (self.photo_paths or '').split('|') if path]


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    guest_email = db.Column(db.String(150), nullable=True)
    status = db.Column(db.String(40), default='reserved')
    total_cents = db.Column(db.Integer, nullable=False)
    shipping_fee_cents = db.Column(db.Integer, default=0)
    fulfillment_method = db.Column(db.String(20), nullable=True)
    commission_cents = db.Column(db.Integer, default=0)
    checkout_session_id = db.Column(db.String(255), nullable=True)
    payment_event_id = db.Column(db.String(255), nullable=True, unique=True)
    shipping_details = db.Column(db.Text, nullable=True)
    reserved_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship('Message', backref='order', lazy=True)


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), default='queued')
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
