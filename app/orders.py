from datetime import datetime, timedelta
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, update

from app.extensions import db
from app.models import Listing, Order, User
from app.payments import calculate_platform_commission
from app.notifications import create_notification, send_email
from app.pricing import MAX_CHECKOUT_AMOUNT_CENTS

orders_bp = Blueprint('orders', __name__)


def get_dashboard_data(user_id):
    bought = Order.query.filter_by(buyer_id=user_id).order_by(Order.created_at.desc()).all()
    sold = Order.query.filter_by(seller_id=user_id).order_by(Order.created_at.desc()).all()
    return render_template('dashboard.html', bought=bought, sold=sold)


def reserve_listing(listing_id, buyer_id=None, guest_email=None, fulfillment_method=None):
    listing = db.session.get(Listing, listing_id)
    if not listing or not listing.is_active or listing.is_hidden:
        return None, 'Listing unavailable.'
    if listing.seller_id == buyer_id:
        return None, 'You cannot purchase your own listing.'
    allowed_methods = {
        'pickup': {'pickup'},
        'shipping': {'shipping'},
        'shipping_or_pickup': {'shipping', 'pickup'},
    }
    if fulfillment_method not in allowed_methods.get(listing.fulfillment, set()):
        return None, 'Choose an available delivery method.'
    now = datetime.utcnow()
    total_cents = listing.price_cents + (
        listing.shipping_fee_cents if fulfillment_method == 'shipping' else 0
    )
    if total_cents > MAX_CHECKOUT_AMOUNT_CENTS:
        return None, 'Checkout total exceeds the maximum supported amount.'
    reserved_until = now + timedelta(minutes=35)
    reservation = db.session.execute(
        update(Listing)
        .where(
            Listing.id == listing_id,
            Listing.is_active.is_(True),
            Listing.is_hidden.is_(False),
            or_(Listing.reserved_until.is_(None), Listing.reserved_until <= now),
        )
        .values(reserved_until=reserved_until)
        .execution_options(synchronize_session=False)
    )
    if reservation.rowcount != 1:
        db.session.rollback()
        return None, 'This listing is already reserved or unavailable.'
    order = Order(
        listing_id=listing.id,
        buyer_id=buyer_id,
        seller_id=listing.seller_id,
        guest_email=guest_email,
        total_cents=total_cents,
        shipping_fee_cents=(
            listing.shipping_fee_cents if fulfillment_method == 'shipping' else 0
        ),
        fulfillment_method=fulfillment_method,
        status='reserved',
        reserved_until=reserved_until,
    )
    db.session.add(order)
    db.session.commit()
    return order, None


@orders_bp.route('/checkout/<int:listing_id>', methods=['GET', 'POST'])
def checkout(listing_id):
    listing = db.session.get(Listing, listing_id)
    if not listing:
        return redirect(url_for('home'))
    if request.method == 'POST':
        if not listing.is_active or listing.is_hidden:
            flash('Listing unavailable.', 'error')
            return redirect(url_for('home'))
        if current_user.is_authenticated:
            if current_user.is_suspended:
                flash('Suspended accounts cannot place orders.', 'error')
                return redirect(url_for('home'))
            buyer_id = current_user.id
            guest_email = None
        else:
            buyer_id = None
            guest_email = (request.form.get('guest_email') or '').strip().lower()
            if (
                len(guest_email) > 150
                or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', guest_email)
            ):
                flash('A valid guest email is required.', 'error')
                return render_template('checkout.html', listing=listing)
        if listing.seller_id == buyer_id:
            flash('You cannot purchase your own listing.', 'error')
            return redirect(url_for('listings.listing_detail', listing_id=listing.id))
        seller = listing.seller
        if not seller or seller.is_suspended or not seller.seller_onboarded or not seller.stripe_connect_account_id:
            flash('Seller onboarding is incomplete. Checkout is blocked.', 'error')
            return render_template('checkout.html', listing=listing)
        try:
            calculate_platform_commission(listing.price_cents)
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('checkout.html', listing=listing)
        fulfillment_method = request.form.get('fulfillment_method')
        order, error = reserve_listing(
            listing.id, buyer_id, guest_email, fulfillment_method
        )
        if error:
            flash(error, 'error')
            return render_template('checkout.html', listing=listing)
        from app.payments import create_checkout_session
        session_result, session_error = create_checkout_session(order)
        if session_error:
            order.status = 'cancelled'
            if listing.reserved_until == order.reserved_until:
                listing.reserved_until = None
            db.session.commit()
            flash(session_error, 'error')
            return render_template('checkout.html', listing=listing)
        order.checkout_session_id = session_result['id']
        order.commission_cents = calculate_platform_commission(listing.price_cents)
        db.session.add(order)
        db.session.commit()
        return redirect(session_result['url'], code=303)
    return render_template('checkout.html', listing=listing)


@orders_bp.route('/orders/<int:order_id>')
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        return redirect(url_for('home'))
    auth_ok = current_user.is_authenticated and current_user.id in {
        order.buyer_id, order.seller_id
    }
    if not auth_ok:
        flash('Not authorized to view this order.', 'error')
        return redirect(url_for('home'))
    return render_template('order_detail.html', order=order)


@orders_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
def update_order_status(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        return redirect(url_for('home'))
    if current_user.id not in {order.buyer_id, order.seller_id}:
        flash('You are not authorized to update this order.', 'error')
        return redirect(url_for('home'))
    status = request.form.get('status')
    if current_user.id == order.seller_id:
        allowed_status = (
            'shipped' if order.fulfillment_method == 'shipping' else 'ready_for_pickup'
        )
        if order.status != 'paid' or status != allowed_status:
            flash('Only a paid order can be marked ready for fulfillment.', 'error')
            return redirect(url_for('orders.order_detail', order_id=order.id))
    elif order.buyer_id == current_user.id:
        if order.status not in {'shipped', 'ready_for_pickup'} or status != 'completed':
            flash('Only fulfilled orders can be marked completed by the buyer.', 'error')
            return redirect(url_for('orders.order_detail', order_id=order.id))
    else:
        flash('You are not authorized to update this order.', 'error')
        return redirect(url_for('home'))
    order.status = status
    db.session.add(order)
    other_party_id = order.buyer_id if current_user.id == order.seller_id else order.seller_id
    if other_party_id:
        create_notification(
            other_party_id, 'Order updated', f'Order #{order.id} is now {status}.'
        )
    db.session.commit()
    other_party = db.session.get(User, other_party_id) if other_party_id else None
    if other_party:
        send_email(
            other_party.email,
            f'Order #{order.id} updated',
            f'Order #{order.id} is now {status}. Sign in to view the update.',
        )
    elif order.guest_email:
        send_email(
            order.guest_email,
            f'Order #{order.id} updated',
            f'Order #{order.id} is now {status}. Guest buyers cannot use in-app messaging.',
        )
    flash('Order status updated.', 'success')
    return redirect(url_for('orders.order_detail', order_id=order.id))
