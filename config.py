import os
import secrets

from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///marketplace.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 42 * 1024 * 1024
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    PLATFORM_COMMISSION_PERCENT = os.getenv('PLATFORM_COMMISSION_PERCENT', '')
    BASE_URL = os.getenv('BASE_URL', 'http://127.0.0.1:5000')
    DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'en')
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_FROM = os.getenv('SMTP_FROM', '')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevConfig(Config):
    DEBUG = False

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'tests', 'uploads')
    SECRET_KEY = 'test-only-secret'
