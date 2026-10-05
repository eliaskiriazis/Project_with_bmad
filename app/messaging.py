from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Message, Order, User
from app.notifications import create_notification, send_email

messaging_bp = Blueprint('messaging', __name__)


@messaging_bp.route('/orders/<int:order_id>/message', methods=['POST'])
@login_required
def send_message(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        return redirect(url_for('home'))
    if current_user.id not in {order.buyer_id, order.seller_id}:
        flash('Only order participants can message.', 'error')
        return redirect(url_for('home'))
    body = (request.form.get('body') or '').strip()
    if not body or len(body) > 4000:
        flash('Messages must contain 1–4000 characters.', 'error')
        return redirect(url_for('orders.order_detail', order_id=order.id))
    recipient_id = order.seller_id if current_user.id == order.buyer_id else order.buyer_id
    if recipient_id is None:
        flash('Guest buyers cannot receive in-app messages.', 'error')
        return redirect(url_for('orders.order_detail', order_id=order.id))
    msg = Message(order_id=order.id, sender_id=current_user.id, recipient_id=recipient_id, body=body)
    recipient = db.session.get(User, recipient_id)
    db.session.add(msg)
    create_notification(recipient_id, 'New order message', f'New message for order #{order.id}.')
    db.session.commit()
    send_email(
        recipient.email,
        f'New message for order #{order.id}',
        f'{current_user.first_name} sent you a message. Sign in to read it.',
    )
    flash('Message sent.', 'success')
    return redirect(url_for('orders.order_detail', order_id=order.id))


@messaging_bp.route('/inbox')
@login_required
def inbox():
    messages = Message.query.filter(
        (Message.sender_id == current_user.id)
        | (Message.recipient_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()
    return render_template('inbox.html', incoming=messages)
