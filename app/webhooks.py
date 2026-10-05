import json
import stripe
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request
from stripe import SignatureVerificationError, StripeError

from app.extensions import csrf, db
from app.models import Listing, Notification, Order, User
from app.notifications import create_notification, send_email
from app.payments import _stripe_test_key

webhooks_bp = Blueprint('webhooks', __name__)


@webhooks_bp.route('/webhooks/stripe', methods=['POST'])
@csrf.exempt
def stripe_webhook():
    secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
    if not secret:
        return jsonify({'error': 'Webhook verification is not configured'}), 503
    try:
        _stripe_test_key()
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 503
    try:
        event = stripe.Webhook.construct_event(
            request.get_data(), request.headers.get('Stripe-Signature', ''), secret
        )
    except (ValueError, SignatureVerificationError) as exc:
        current_app.logger.warning('Rejected invalid Stripe webhook: %s', exc)
        return jsonify({'error': 'Invalid webhook signature or payload'}), 400
    except StripeError as exc:
        current_app.logger.error('Stripe webhook verification failed: %s', exc)
        return jsonify({'error': 'Payment provider verification failed'}), 503

    if event.get('livemode') is not False:
        return jsonify({'error': 'Live-mode events are not accepted'}), 400
    event_id = event.get('id')
    event_type = event.get('type')
    data = event.get('data', {}).get('object', {})
    if not event_id or not event_type:
        return jsonify({'error': 'Incomplete Stripe event'}), 400

    if event_type == 'account.updated':
        account = User.query.filter_by(
            stripe_connect_account_id=data.get('id')
        ).first()
        if account:
            account.seller_onboarded = bool(
                data.get('details_submitted')
                and data.get('charges_enabled')
                and data.get('payouts_enabled')
            )
            db.session.commit()
        return jsonify({'status': 'account updated'}), 200

    if event_type not in {
        'checkout.session.completed',
        'checkout.session.async_payment_succeeded',
        'checkout.session.async_payment_failed',
        'checkout.session.expired',
    }:
        return jsonify({'status': 'ignored'}), 200

    session_id = data.get('id')
    if not session_id:
        return jsonify({'error': 'Checkout event has no session id'}), 400
    order = Order.query.filter_by(checkout_session_id=session_id).first()
    if not order:
        return jsonify({'error': 'No order matches this checkout session'}), 404
    seller = db.session.get(User, order.seller_id)
    if not seller or event.get('account') != seller.stripe_connect_account_id:
        return jsonify({'error': 'Checkout event account does not match seller'}), 400

    if event_type in {'checkout.session.expired', 'checkout.session.async_payment_failed'}:
        if order.status == 'reserved':
            order.status = 'cancelled'
            if order.listing.reserved_until == order.reserved_until:
                order.listing.reserved_until = None
            if event_type == 'checkout.session.async_payment_failed' and order.buyer_id:
                create_notification(
                    order.buyer_id,
                    'Payment failed',
                    f'Payment failed for order #{order.id}.',
                )
            db.session.commit()
            if event_type == 'checkout.session.async_payment_failed':
                buyer_email = order.guest_email or (order.buyer.email if order.buyer else None)
                if buyer_email:
                    send_email(
                        buyer_email,
                        f'Payment failed for order #{order.id}',
                        f'Payment failed for order #{order.id}. You may try checkout again.',
                    )
        return jsonify({'status': 'reservation released'}), 200

    if data.get('payment_status') != 'paid':
        return jsonify({'error': 'Checkout session is not paid'}), 400
    metadata = data.get('metadata') or {}
    if (
        data.get('currency') != 'eur'
        or data.get('amount_total') != order.total_cents
        or data.get('client_reference_id') != str(order.id)
        or metadata.get('order_id') != str(order.id)
    ):
        return jsonify({'error': 'Checkout details do not match the order'}), 400
    if order.fulfillment_method == 'shipping' and not data.get('shipping_details'):
        return jsonify({'error': 'Required shipping address is missing'}), 400
    if order.payment_event_id == event_id or order.status == 'paid':
        return jsonify({'status': 'already processed'}), 200
    if order.status != 'reserved' or (
        order.reserved_until is None
        or order.reserved_until <= datetime.utcnow()
    ):
        current_app.logger.critical(
            'Paid Stripe session %s for order %s arrived after its reservation expired; '
            'manual payment reconciliation is required.',
            session_id, order.id,
        )
        return jsonify({'error': 'Order reservation is no longer valid'}), 409

    order.status = 'paid'
    order.payment_event_id = event_id
    if data.get('shipping_details'):
        order.shipping_details = json.dumps(data['shipping_details'])
    order.listing.is_active = False
    order.listing.reserved_until = None
    recipients = {order.seller_id}
    if order.buyer_id:
        recipients.add(order.buyer_id)
    for user_id in recipients:
        create_notification(
            user_id, 'Order paid', f'Order #{order.id} has been paid.'
        )
    db.session.commit()

    subject = f'Guitar Marketplace order #{order.id} paid'
    common_body = (
        f'Order #{order.id} has been paid. '
        f'Total: EUR {order.total_cents / 100:.2f}.'
    )
    if order.guest_email:
        send_email(
            order.guest_email, subject,
            common_body + ' Order updates will be sent by email; guest buyers cannot use in-app messaging.',
        )
    else:
        send_email(
            order.buyer.email, subject,
            common_body + ' Sign in to view order details and fulfillment updates.',
        )
    send_email(
        seller.email, subject,
        common_body + ' Sign in to view order details and fulfillment updates.',
    )
    return jsonify({'status': 'paid'}), 200
