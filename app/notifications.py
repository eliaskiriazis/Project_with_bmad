import smtplib
from email.message import EmailMessage

from flask import Blueprint, current_app, render_template
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Notification

notifications_bp = Blueprint('notifications', __name__)


def create_notification(user_id, title, body):
    notification = Notification(user_id=user_id, title=title, body=body)
    db.session.add(notification)
    return notification


def send_email(recipient, subject, body):
    host = current_app.config.get('SMTP_HOST')
    sender = current_app.config.get('SMTP_FROM')
    if not host or not sender:
        current_app.logger.warning(
            'Email not sent because SMTP_HOST or SMTP_FROM is not configured.'
        )
        return False
    message = EmailMessage()
    message['From'] = sender
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(host, current_app.config['SMTP_PORT'], timeout=10) as server:
            server.starttls()
            username = current_app.config.get('SMTP_USERNAME')
            if username:
                server.login(username, current_app.config.get('SMTP_PASSWORD', ''))
            server.send_message(message)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        current_app.logger.error('Email delivery failed: %s', exc)
        return False


@notifications_bp.route('/notifications')
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', items=items)
