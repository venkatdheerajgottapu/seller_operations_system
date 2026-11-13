import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_from_directory, current_app
from werkzeug.utils import secure_filename
from app.config import BASE_DIR
from app.services import (
    SellerService, OrderService, FulfillmentService,
    CommissionService, DisputeService, PayoutService,
    AnomalyDetectorService, AnalyticsService
)
from database.connection import get_session
from app.models import ProductListing, CommissionRule, PayoutLine
from data_generator.generator import SyntheticDataGenerator
from data_generator.exporter import export_dataset

dashboard_bp = Blueprint('dashboard', __name__)
EXPORTS_DIR = BASE_DIR / 'exports'


# -------------------------------------------------------------------------
# 1. Overview Dashboard
# -------------------------------------------------------------------------
@dashboard_bp.route('/')
def overview():
    kpis = AnalyticsService.get_dashboard_kpis()
    charts = AnalyticsService.get_chart_data()
    return render_template('overview.html', kpis=kpis, charts=charts)


# -------------------------------------------------------------------------
# 2. Seller Management
# -------------------------------------------------------------------------
@dashboard_bp.route('/sellers')
def sellers():
    status_filter = request.args.get('status')
    all_sellers = SellerService.get_all_sellers(status_filter)
    return render_template('sellers.html', sellers=all_sellers, current_status=status_filter)


@dashboard_bp.route('/sellers/<seller_id>/status', methods=['POST'])
def update_seller_status(seller_id):
    new_status = request.form.get('status')
    reason = request.form.get('reason', 'Administrative action from dashboard')
    if new_status:
        SellerService.update_seller_status(seller_id, new_status, reason)
    return redirect(url_for('dashboard.sellers'))


@dashboard_bp.route('/sellers/<seller_id>/recalculate-sla', methods=['POST'])
def recalculate_seller_sla(seller_id):
    SellerService.recalculate_seller_sla(seller_id)
    return redirect(url_for('dashboard.sellers'))


# -------------------------------------------------------------------------
# 3. Product Listings
# -------------------------------------------------------------------------
@dashboard_bp.route('/listings')
def listings():
    category = request.args.get('category')
    status = request.args.get('status')
    with get_session() as session:
        query = session.query(ProductListing)
        if category:
            query = query.filter(ProductListing.category == category)
        if status:
            query = query.filter(ProductListing.status == status)
        
        all_listings = query.order_by(ProductListing.created_at.desc()).limit(200).all()
        categories = [c[0] for c in session.query(ProductListing.category).distinct().all()]
        return render_template(
            'listings.html',
            listings=[l.to_dict() for l in all_listings],
            categories=categories,
            selected_cat=category,
            selected_status=status
        )


# -------------------------------------------------------------------------
# 4. Order Management
# -------------------------------------------------------------------------
@dashboard_bp.route('/orders')
def orders():
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    orders_data = OrderService.get_orders(status_filter=status, page=page, page_size=40)
    return render_template('orders.html', data=orders_data, selected_status=status)


@dashboard_bp.route('/orders/<order_id>')
def order_detail(order_id):
    order = OrderService.get_order_details(order_id)
    if not order:
        return "Order not found", 404
    return render_template('order_detail.html', order=order)


# -------------------------------------------------------------------------
# 5. Fulfillment Monitoring
# -------------------------------------------------------------------------
@dashboard_bp.route('/fulfillments')
def fulfillments():
    status = request.args.get('status')
    delayed_only = request.args.get('delayed') == '1'
    page = int(request.args.get('page', 1))
    data = FulfillmentService.get_fulfillments(status_filter=status, delayed_only=delayed_only, page=page, page_size=40)
    return render_template('fulfillments.html', data=data, selected_status=status, delayed_only=delayed_only)


# -------------------------------------------------------------------------
# 6. Dispute Management
# -------------------------------------------------------------------------
@dashboard_bp.route('/disputes')
def disputes():
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    data = DisputeService.get_disputes(status_filter=status, page=page, page_size=40)
    return render_template('disputes.html', data=data, selected_status=status)


@dashboard_bp.route('/disputes/<dispute_id>/resolve', methods=['POST'])
def resolve_dispute(dispute_id):
    resolution = request.form.get('resolution')
    if resolution:
        DisputeService.resolve_dispute(dispute_id, resolution)
    return redirect(url_for('dashboard.disputes'))


# -------------------------------------------------------------------------
# 7. Commission Management
# -------------------------------------------------------------------------
@dashboard_bp.route('/commissions')
def commissions():
    with get_session() as session:
        rules = session.query(CommissionRule).all()
        # Find order lines with duplicate commissions if any
        dup_query = (
            session.query(PayoutLine.order_line_id)
            .filter(PayoutLine.line_type == 'COMMISSION', PayoutLine.order_line_id.isnot(None))
            .group_by(PayoutLine.order_line_id)
            .having(session.bind.dialect.name == 'sqlite' or True)
        )
        return render_template('commissions.html', rules=[r.to_dict() for r in rules])


# -------------------------------------------------------------------------
# 8. Payout Management
# -------------------------------------------------------------------------
@dashboard_bp.route('/payouts')
def payouts():
    status = request.args.get('status')
    page = int(request.args.get('page', 1))
    data = PayoutService.get_payouts(status_filter=status, page=page, page_size=40)
    return render_template('payouts.html', data=data, selected_status=status)


@dashboard_bp.route('/payouts/<payout_id>')
def payout_detail(payout_id):
    payout = PayoutService.get_payout_details(payout_id)
    if not payout:
        return "Payout not found", 404
    return render_template('payout_detail.html', payout=payout)


@dashboard_bp.route('/payouts/<payout_id>/reconcile', methods=['POST'])
def reconcile_payout_route(payout_id):
    PayoutService.reconcile_payout(payout_id)
    return redirect(url_for('dashboard.payout_detail', payout_id=payout_id))


# -------------------------------------------------------------------------
# 9. Anomaly Monitoring & Ground-Truth Benchmark
# -------------------------------------------------------------------------
@dashboard_bp.route('/anomalies')
def anomalies():
    eval_data = AnomalyDetectorService.evaluate_against_ground_truth()
    return render_template('anomalies.html', evaluation=eval_data)


@dashboard_bp.route('/anomalies/scan', methods=['POST'])
def run_anomaly_scan():
    AnomalyDetectorService.run_detection_scan()
    return redirect(url_for('dashboard.anomalies'))


# -------------------------------------------------------------------------
# 10. Reports & Exports
# -------------------------------------------------------------------------
@dashboard_bp.route('/reports')
def reports():
    exported_files = []
    if EXPORTS_DIR.exists():
        for f in os.listdir(EXPORTS_DIR):
            file_path = EXPORTS_DIR / f
            exported_files.append({
                'name': f,
                'size_kb': round(os.path.getsize(file_path) / 1024, 2),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            })
    return render_template('reports.html', files=exported_files)


@dashboard_bp.route('/exports/download/<filename>')
def download_export(filename):
    safe_name = secure_filename(filename)
    target_path = EXPORTS_DIR / safe_name
    if not target_path.is_file():
        return jsonify({'error': 'File not found or access denied', 'status_code': 404}), 404
    return send_from_directory(EXPORTS_DIR, safe_name, as_attachment=True)


@dashboard_bp.route('/reports/regenerate', methods=['POST'])
def regenerate_data():
    if current_app.config.get('ENV') == 'production' or not current_app.config.get('DEBUG'):
        flash('Data regeneration is disabled in production to protect existing operational records.', 'danger')
        return redirect(url_for('dashboard.reports'))

    preset = request.form.get('preset', 'STARTER')
    gen = SyntheticDataGenerator()
    gen.generate(preset)
    gen.save_to_db()
    export_dataset(gen, prefix=preset.lower())
    # Re-run anomaly detection
    AnomalyDetectorService.run_detection_scan()
    return redirect(url_for('dashboard.overview'))


# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------
@dashboard_bp.route('/api/kpis')
def api_kpis():
    return jsonify(AnalyticsService.get_dashboard_kpis())


@dashboard_bp.route('/api/charts')
def api_charts():
    return jsonify(AnalyticsService.get_chart_data())


@dashboard_bp.route('/api/anomalies/evaluation')
def api_anomaly_eval():
    return jsonify(AnomalyDetectorService.evaluate_against_ground_truth())
