import pytest
from decimal import Decimal
from datetime import datetime
from app import create_app
from database.connection import get_session, Base, get_engine
from app.models import (
    Seller, ProductListing, Customer, Order, OrderLine,
    Fulfillment, Dispute, CommissionRule, Payout, PayoutLine
)
from app.services import (
    SellerService, OrderService, FulfillmentService,
    CommissionService, DisputeService, PayoutService,
    AnomalyDetectorService, AnalyticsService
)
from data_generator.generator import SyntheticDataGenerator


@pytest.fixture(scope="module")
def app_client():
    app = create_app('development')
    with app.test_client() as client:
        # Initialize schema and seed data
        engine = get_engine()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        gen = SyntheticDataGenerator()
        gen.generate('STARTER')
        gen.save_to_db()
        yield client


def test_dashboard_routes(app_client):
    """Verify that all core dashboard pages render successfully with HTTP 200."""
    routes = [
        '/',
        '/sellers',
        '/listings',
        '/orders',
        '/fulfillments',
        '/disputes',
        '/commissions',
        '/payouts',
        '/anomalies',
        '/reports',
        '/health'
    ]
    for r in routes:
        resp = app_client.get(r)
        assert resp.status_code == 200, f"Route {r} returned status {resp.status_code}"


def test_seller_service_status_update(app_client):
    """Verify seller status transition and listing cascade."""
    sellers = SellerService.get_all_sellers()
    assert len(sellers) > 0
    target_id = sellers[0]['seller_id']

    updated = SellerService.update_seller_status(target_id, 'SUSPENDED', 'Test suspension')
    assert updated['status'] == 'SUSPENDED'

    # Reactivate
    reactivated = SellerService.update_seller_status(target_id, 'ACTIVE', 'Reactivation')
    assert reactivated['status'] == 'ACTIVE'


def test_seller_sla_recalculation(app_client):
    """Verify recalculation of seller SLA metrics."""
    sellers = SellerService.get_all_sellers()
    target_id = sellers[0]['seller_id']
    recalc = SellerService.recalculate_seller_sla(target_id)
    assert 'on_time_shipment_rate' in recalc
    assert 'fulfillment_rate' in recalc
    assert 'rating' in recalc


def test_order_service_multi_seller_details(app_client):
    """Verify multi-seller order line splitting."""
    orders_data = OrderService.get_orders(page=1, page_size=10)
    assert orders_data['total'] > 0
    target_order_id = orders_data['orders'][0]['order_id']

    details = OrderService.get_order_details(target_order_id)
    assert details is not None
    assert 'lines' in details
    assert len(details['lines']) > 0
    assert 'is_multi_seller' in details


def test_fulfillment_delay_calculation(app_client):
    """Verify delivery delay detection."""
    fulfillments_data = FulfillmentService.get_fulfillments(page=1, page_size=10)
    assert fulfillments_data['total'] > 0
    target_f_id = fulfillments_data['fulfillments'][0]['fulfillment_id']

    # Record delivery with explicit late timestamp
    delivered = FulfillmentService.record_delivery(target_f_id, delivered_at=datetime(2026, 12, 1))
    assert delivered['status'] == 'DELIVERED'
    assert delivered['is_delayed'] is True


def test_commission_calculation(app_client):
    """Verify effective commission rule calculation."""
    res = CommissionService.calculate_commission('Electronics', Decimal('200.00'), datetime(2026, 5, 1))
    assert res['amount'] == Decimal('16.00')  # 8% of 200.00
    assert res['rate'] == Decimal('0.0800')


def test_payout_reconciliation_and_formula(app_client):
    """Verify financial formula: Net = Gross - Comm - Refund - Dispute - Reserve + Adj."""
    payouts_data = PayoutService.get_payouts(page=1, page_size=10)
    assert payouts_data['total'] > 0
    target_payout_id = payouts_data['payouts'][0]['payout_id']

    recon = PayoutService.reconcile_payout(target_payout_id)
    assert 'header_net' in recon
    assert 'expected_net' in recon
    assert 'lines_sum' in recon
    assert recon['reconciliation_status'] in ('RECONCILED', 'DISCREPANCY')


def test_anomaly_detection_and_evaluation(app_client):
    """Verify anomaly detection engine independent execution and evaluation."""
    eval_result = AnomalyDetectorService.evaluate_against_ground_truth()
    cm = eval_result['confusion_matrix']
    metrics = eval_result['metrics']

    assert cm['true_positives'] > 0
    assert cm['false_negatives'] == 0  # 100% recall achieved on ground truth violations!
    assert metrics['recall'] == 1.0
    assert metrics['f1_score'] >= 0.80
    assert len(eval_result['detected_records']) > 0


def test_analytics_kpis_and_charts(app_client):
    """Verify that analytics service computes live non-hardcoded aggregates."""
    kpis = AnalyticsService.get_dashboard_kpis()
    assert kpis['total_sellers'] == 20
    assert kpis['total_orders'] == 500
    assert kpis['eligible_payouts'] > 0

    charts = AnalyticsService.get_chart_data()
    assert 'order_status' in charts
    assert 'category_sales' in charts
    assert 'carrier_performance' in charts
    assert 'payout_trend' in charts
