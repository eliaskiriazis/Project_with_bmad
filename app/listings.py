import os
import uuid
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.demo_listings import (
    find_demo_listing,
    normalize_fulfillment_filter,
    search_demo_listings,
)
from app.models import Listing, Report
from app.pricing import MAX_CHECKOUT_AMOUNT_CENTS

listings_bp = Blueprint('listings', __name__)


def _allowed_photo(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in {'.jpg', '.jpeg', '.png', '.webp'}


def _valid_photo_content(file_storage):
    header = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    return (
        header.startswith(b'\xff\xd8\xff')
        or header.startswith(b'\x89PNG\r\n\x1a\n')
        or (header.startswith(b'RIFF') and header[8:12] == b'WEBP')
    )


def _save_photos(files):
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    validated = []
    files = [item for item in (files or []) if item and item.filename]
    if not files:
        raise ValueError('At least one guitar photo is required.')
    if len(files) > 8:
        raise ValueError('A listing may include at most eight photos.')
    for file_storage in files:
        if not _allowed_photo(file_storage.filename):
            raise ValueError('Unsupported file type')
        raw = file_storage.stream.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError('Image too large')
        file_storage.stream.seek(0)
        if not _valid_photo_content(file_storage):
            raise ValueError('Photo content does not match a supported image type.')
        filename = secure_filename(file_storage.filename)
        safe_name = f'{uuid.uuid4().hex}_{filename}'
        validated.append((file_storage, safe_name))
    saved = []
    try:
        for file_storage, safe_name in validated:
            file_storage.save(os.path.join(upload_dir, safe_name))
            saved.append(safe_name)
    except OSError:
        for saved_name in saved:
            os.remove(os.path.join(upload_dir, saved_name))
        raise ValueError('Photo upload failed. Please retry the listing.')
    return saved


def _amount_to_cents(value, *, required=False):
    if not value:
        if required:
            raise ValueError
        return 0
    amount = Decimal(value)
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError
    amount_cents = int(amount * 100)
    if amount_cents > MAX_CHECKOUT_AMOUNT_CENTS:
        raise ValueError
    return amount_cents


@listings_bp.route('/sell', methods=['GET', 'POST'])
@login_required
def sell_listing():
    if current_user.is_suspended:
        flash('Suspended accounts cannot publish listings.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        description = (request.form.get('description') or '').strip()
        brand = (request.form.get('brand') or '').strip()
        model = (request.form.get('model') or '').strip()
        condition = (request.form.get('condition') or '').strip()
        is_electric_guitar = request.form.get('electric_guitar') == 'yes'
        price = request.form.get('price')
        shipping = request.form.get('shipping_fee')
        fulfillment = request.form.get('fulfillment') or 'pickup'
        try:
            price_cents = _amount_to_cents(price, required=True)
            shipping_cents = _amount_to_cents(shipping)
        except (ValueError, InvalidOperation):
            flash('Please enter valid EUR amounts.', 'error')
            return render_template('listing_form.html')
        allowed_conditions = {'Excellent', 'Very Good', 'Good', 'Fair'}
        allowed_fulfillment = {'pickup', 'shipping', 'shipping_or_pickup'}
        if (
            not is_electric_guitar
            or not all([title, description, brand, model])
            or len(title) > 180 or len(description) > 5000
            or len(brand) > 80 or len(model) > 100
            or condition not in allowed_conditions
            or fulfillment not in allowed_fulfillment
            or price_cents <= 0
            or (fulfillment != 'pickup' and shipping_cents <= 0)
            or (fulfillment == 'pickup' and shipping_cents != 0)
        ):
            flash('Missing required guitar details.', 'error')
            return render_template('listing_form.html')
        if price_cents + shipping_cents > MAX_CHECKOUT_AMOUNT_CENTS:
            flash('Item and shipping exceed the maximum checkout amount.', 'error')
            return render_template('listing_form.html')
        try:
            photo_paths = _save_photos(request.files.getlist('photos'))
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('listing_form.html')
        listing = Listing(
            seller_id=current_user.id,
            title=title,
            description=description,
            brand=brand,
            model=model,
            condition=condition,
            price_cents=price_cents,
            shipping_fee_cents=shipping_cents,
            fulfillment=fulfillment,
            photo_paths='|'.join(photo_paths),
        )
        db.session.add(listing)
        db.session.commit()
        flash('Listing published.', 'success')
        return redirect(url_for('listings.listing_detail', listing_id=listing.id))
    return render_template('listing_form.html')


@listings_bp.route('/listings/<int:listing_id>')
def listing_detail(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        abort(404)
    if listing.is_hidden:
        if not current_user.is_authenticated or (
            not current_user.is_admin and current_user.id != listing.seller_id
        ):
            abort(404)
    return render_template('listing_detail.html', listing=listing)


@listings_bp.route('/demo-listings/<slug>')
def demo_listing_detail(slug):
    listing = find_demo_listing(slug)
    if listing is None:
        abort(404)
    return render_template('listing_detail.html', listing=listing)


@listings_bp.route('/search')
def listing_search_query():
    keyword = request.args.get('keyword', '')
    brand = request.args.get('brand', '')
    condition = request.args.get('condition', '')
    fulfillment = request.args.get('fulfillment', '')
    fulfillment_filter = normalize_fulfillment_filter(fulfillment)
    max_price = request.args.get('max_price', '')
    query = Listing.query.filter_by(is_active=True, is_hidden=False)
    if keyword:
        like = f'%{keyword}%'
        query = query.filter((Listing.title.ilike(like)) | (Listing.description.ilike(like)) | (Listing.model.ilike(like)))
    if brand:
        query = query.filter(Listing.brand.ilike(f'%{brand}%'))
    if condition:
        query = query.filter(Listing.condition.ilike(f'%{condition}%'))
    if fulfillment_filter:
        query = query.filter(Listing.fulfillment.ilike(f'%{fulfillment_filter}%'))
    if max_price:
        try:
            max_price_cents = _amount_to_cents(max_price)
            query = query.filter(Listing.price_cents <= max_price_cents)
        except (ValueError, InvalidOperation):
            flash('Enter a valid maximum price.', 'error')
            return render_template(
                'home.html', listings=[], demo_listings=[], keyword=keyword, brand=brand,
                condition=condition, fulfillment=fulfillment, max_price=max_price,
            ), 400
    listings = query.order_by(Listing.created_at.desc()).all()
    demo_listings = search_demo_listings(
        keyword=keyword,
        brand=brand,
        condition=condition,
        fulfillment=fulfillment_filter,
        max_price=max_price_cents if max_price else None,
    )
    return render_template(
        'home.html', listings=listings, demo_listings=demo_listings, keyword=keyword,
        brand=brand, condition=condition, fulfillment=fulfillment, max_price=max_price,
    )


@listings_bp.route('/listings/<int:listing_id>/report', methods=['POST'])
@login_required
def report_listing(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        return redirect(url_for('home'))
    reason = (request.form.get('reason') or '').strip()
    if not reason or len(reason) > 2000:
        flash('Report reasons must contain 1–2000 characters.', 'error')
        return redirect(url_for('listings.listing_detail', listing_id=listing.id))
    existing_report = Report.query.filter_by(
        listing_id=listing.id, reporter_id=current_user.id, status='queued'
    ).first()
    if existing_report:
        flash('You already submitted a report for this listing.', 'error')
        return redirect(url_for('listings.listing_detail', listing_id=listing.id))
    report = Report(listing_id=listing.id, reporter_id=current_user.id, reason=reason)
    db.session.add(report)
    db.session.commit()
    flash('Listing report received by moderators.', 'success')
    return redirect(url_for('listings.listing_detail', listing_id=listing.id))
