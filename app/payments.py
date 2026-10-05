import re
import time
from decimal import Decimal, InvalidOperation

import stripe
from flask import Blueprint, current_app, flash, redirect, request, url_for
from flask_login import current_user, login_required
from stripe import StripeError

from app.extensions import db
from app.models import User

payments_bp = Blueprint('payments', __name__)
EU_COUNTRIES = {
    'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR',
    'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK',
    'SI', 'ES', 'SE',
}


def _stripe_test_key():
    key = current_app.config.get('STRIPE_SECRET_KEY') or ''
    if not key.startswith('sk_test_'):
        raise ValueError('Stripe test-mode credentials are not configured.')
    stripe.api_key = key
    return key


def calculate_platform_commission(price_cents):
    configured_rate = current_app.config.get('PLATFORM_COMMISSION_PERCENT')
    try:
        rate = Decimal(str(configured_rate))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError('A valid commission percentage is required before checkout.')
    if not rate.is_finite() or not 0 < rate <= 100:
        raise ValueError('A valid commission percentage is required before checkout.')
    return int((Decimal(price_cents) * rate / 100).quantize(Decimal('1')))


def create_checkout_session(order):
    try:
        _stripe_test_key()
        seller = db.session.get(User, order.seller_id)
        if not seller or not seller.seller_onboarded or not seller.stripe_connect_account_id:
            return None, 'Seller onboarding is incomplete. Checkout is blocked.'
        fee = calculate_platform_commission(order.total_cents - order.shipping_fee_cents)
        line_items = [{
            'price_data': {
                'currency': 'eur',
                'product_data': {'name': order.listing.title},
                'unit_amount': order.listing.price_cents,
            },
            'quantity': 1,
        }]
        if order.shipping_fee_cents:
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'Shipping'},
                    'unit_amount': order.shipping_fee_cents,
                },
                'quantity': 1,
            })
        params = {
            'mode': 'payment',
            'line_items': line_items,
            'success_url': f"{current_app.config['BASE_URL']}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            'cancel_url': f"{current_app.config['BASE_URL']}/checkout/cancel",
            'client_reference_id': str(order.id),
            'metadata': {'order_id': str(order.id)},
            'payment_intent_data': {'application_fee_amount': fee},
            'expires_at': int(time.time() + 30 * 60),
        }
        if order.guest_email:
            params['customer_email'] = order.guest_email
        if order.fulfillment_method == 'shipping':
            params['shipping_address_collection'] = {
                'allowed_countries': sorted(EU_COUNTRIES),
            }
        checkout = stripe.checkout.Session.create(
            **params, stripe_account=seller.stripe_connect_account_id
        )
        if not checkout.get('id') or not checkout.get('url'):
            return None, 'Stripe did not return a checkout session.'
        return checkout, None
    except (StripeError, ValueError) as exc:
        current_app.logger.error('Unable to create Stripe checkout: %s', exc)
        return None, 'Checkout could not be started. Please try again.'


@payments_bp.route('/seller/connect', methods=['POST'])
@login_required
def start_connect_onboarding():
    if current_user.is_suspended:
        flash('Suspended accounts cannot sell.', 'error')
        return redirect(url_for('dashboard'))
    country = (request.form.get('country_code') or '').strip().upper()
    if not re.fullmatch(r'[A-Z]{2}', country) or country not in EU_COUNTRIES:
        flash('Choose a valid two-letter EU country code.', 'error')
        return redirect(url_for('dashboard'))
    try:
        _stripe_test_key()
        if current_user.stripe_connect_account_id:
            account_id = current_user.stripe_connect_account_id
        else:
            account = stripe.Account.create(
                type='express',
                country=country,
                email=current_user.email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
            )
            account_id = account.id
            current_user.stripe_connect_account_id = account_id
            current_user.country_code = country
            db.session.commit()
        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=f"{current_app.config['BASE_URL']}/dashboard",
            return_url=f"{current_app.config['BASE_URL']}/dashboard",
            type='account_onboarding',
        )
        return redirect(link.url)
    except (StripeError, ValueError) as exc:
        current_app.logger.error('Unable to start Stripe Connect onboarding: %s', exc)
        flash('Seller payment setup is unavailable. Please try again.', 'error')
        return redirect(url_for('dashboard'))


@payments_bp.route('/checkout/success')
def checkout_success():
    flash('Payment is being confirmed. Order status updates after Stripe verifies payment.', 'success')
    return redirect(url_for('home'))


@payments_bp.route('/checkout/cancel')
def checkout_cancel():
    flash('Checkout was cancelled. The listing reservation will expire automatically.', 'error')
    return redirect(url_for('home'))
