from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Listing, Report, User

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('home'))
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('admin.html', reports=reports)


@admin_bp.route('/admin/reports/<int:report_id>/hide', methods=['POST'])
@login_required
def hide_listing(report_id):
    if not current_user.is_admin:
        flash('Only admins can hide listings.', 'error')
        return redirect(url_for('home'))
    report = db.session.get(Report, report_id)
    if report is None:
        abort(404)
    listing = db.session.get(Listing, report.listing_id)
    listing.is_hidden = True
    report.status = 'resolved'
    db.session.add(report)
    db.session.add(listing)
    db.session.commit()
    flash('Listing hidden.', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/reports/<int:report_id>/suspend', methods=['POST'])
@login_required
def suspend_seller(report_id):
    if not current_user.is_admin:
        flash('Only admins can suspend sellers.', 'error')
        return redirect(url_for('home'))
    report = db.session.get(Report, report_id)
    if report is None:
        abort(404)
    seller = db.session.get(User, report.listing.seller_id)
    seller.is_suspended = True
    for listing in seller.listings:
        listing.is_active = False
        listing.is_hidden = True
    report.status = 'resolved'
    db.session.add(report)
    db.session.add(seller)
    db.session.add_all(seller.listings)
    db.session.commit()
    flash('Seller suspended.', 'success')
    return redirect(url_for('admin.admin_dashboard'))
