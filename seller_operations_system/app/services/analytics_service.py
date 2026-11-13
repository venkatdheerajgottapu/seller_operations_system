from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy import func, case
from database.connection import get_session
from app.models import (
    Seller, ProductListing, Order, OrderLine, Fulfillment,
    Dispute, CommissionRule, Payout, AnomalyRecord
)


class AnalyticsService:
    """Dashboard KPIs, marketplace aggregations, and Chart.js analytics."""

    @staticmethod
    def get_dashboard_kpis() -> Dict[str, Any]:
        with get_session() as session:
            # Seller counts
            total_sellers = session.query(func.count(Seller.seller_id)).scalar() or 0
            active_sellers = session.query(func.count(Seller.seller_id)).filter(Seller.status == 'ACTIVE').scalar() or 0
            suspended_sellers = session.query(func.count(Seller.seller_id)).filter(Seller.status == 'SUSPENDED').scalar() or 0

            # Order counts
            total_orders = session.query(func.count(Order.order_id)).scalar() or 0
            delivered_orders = session.query(func.count(Order.order_id)).filter(Order.order_status == 'DELIVERED').scalar() or 0
            
            # Delayed orders
            delayed_orders = session.query(func.count(Fulfillment.fulfillment_id)).filter(
                Fulfillment.is_delayed.is_(True)
            ).scalar() or 0

            # Dispute counts
            open_disputes = session.query(func.count(Dispute.dispute_id)).filter(
                Dispute.status.in_(['OPEN', 'UNDER_INVESTIGATION'])
            ).scalar() or 0

            # Financial totals
            total_commissions = session.query(func.coalesce(func.sum(Payout.commission_deduction), Decimal('0.00'))).scalar() or Decimal('0.00')
            eligible_payouts = session.query(func.coalesce(func.sum(Payout.net_payout_amount), Decimal('0.00'))).filter(
                Payout.status == 'PAID'
            ).scalar() or Decimal('0.00')
            payouts_on_hold = session.query(func.coalesce(func.sum(Payout.reserve_hold_amount), Decimal('0.00'))).scalar() or Decimal('0.00')

            # Anomaly counts
            detected_anomalies = session.query(func.count(AnomalyRecord.id)).filter(
                AnomalyRecord.detected_by == 'DETECTOR_ENGINE'
            ).scalar() or 0

            return {
                'total_sellers': total_sellers,
                'active_sellers': active_sellers,
                'suspended_sellers': suspended_sellers,
                'total_orders': total_orders,
                'delivered_orders': delivered_orders,
                'delayed_orders': delayed_orders,
                'open_disputes': open_disputes,
                'total_commissions': float(total_commissions),
                'eligible_payouts': float(eligible_payouts),
                'payouts_on_hold': float(payouts_on_hold),
                'detected_anomalies': detected_anomalies
            }

    @staticmethod
    def get_chart_data() -> Dict[str, Any]:
        """Aggregate data for Chart.js visual charts."""
        with get_session() as session:
            # 1. Orders by Status
            status_counts = (
                session.query(Order.order_status, func.count(Order.order_id))
                .group_by(Order.order_status)
                .all()
            )
            order_status_labels = [s[0] for s in status_counts]
            order_status_values = [s[1] for s in status_counts]

            # 2. Sales by Category
            cat_sales = (
                session.query(ProductListing.category, func.sum(OrderLine.line_total))
                .join(OrderLine, ProductListing.listing_id == OrderLine.listing_id)
                .group_by(ProductListing.category)
                .all()
            )
            cat_labels = [c[0] for c in cat_sales]
            cat_values = [float(c[1] or 0.0) for c in cat_sales]

            # 3. Carrier Delay Distribution
            carrier_delays = (
                session.query(
                    Fulfillment.carrier,
                    func.count(Fulfillment.fulfillment_id),
                    func.sum(case((Fulfillment.is_delayed.is_(True), 1), else_=0))
                )
                .group_by(Fulfillment.carrier)
                .all()
            )
            carrier_names = [cd[0] for cd in carrier_delays]
            carrier_totals = [cd[1] for cd in carrier_delays]
            carrier_delay_counts = [int(cd[2] or 0) for cd in carrier_delays]

            # 4. Monthly Payout Trend
            month_col = func.strftime('%Y-%m', Payout.payout_date) if 'sqlite' in str(session.bind.url) else func.date_format(Payout.payout_date, '%Y-%m')
            payouts = (
                session.query(
                    month_col.label('month'),
                    func.sum(Payout.gross_amount),
                    func.sum(Payout.net_payout_amount)
                )
                .group_by('month')
                .order_by('month')
                .all()
            )
            payout_months = [p[0] for p in payouts]
            payout_gross = [float(p[1] or 0.0) for p in payouts]
            payout_net = [float(p[2] or 0.0) for p in payouts]

            return {
                'order_status': {
                    'labels': order_status_labels,
                    'data': order_status_values
                },
                'category_sales': {
                    'labels': cat_labels,
                    'data': cat_values
                },
                'carrier_performance': {
                    'labels': carrier_names,
                    'totals': carrier_totals,
                    'delays': carrier_delay_counts
                },
                'payout_trend': {
                    'months': payout_months,
                    'gross': payout_gross,
                    'net': payout_net
                }
            }
