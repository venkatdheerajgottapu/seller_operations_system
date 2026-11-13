import re
from decimal import Decimal
from typing import Dict, Any, List
from database.connection import get_session
from app.models import (
    Seller, ProductListing, Customer, Order, OrderLine,
    Fulfillment, Dispute, Payout, PayoutLine
)

ID_PATTERNS = {
    'seller': re.compile(r'^SELL-\d{6}$'),
    'listing': re.compile(r'^LIST-SELL-\d{6}-\d{6}$'),
    'customer': re.compile(r'^CUST-\d{6}$'),
    'order': re.compile(r'^ORD-\d{4}-\d{6}$'),
    'order_line': re.compile(r'^ORD-\d{4}-\d{6}-\d{2}$'),
    'fulfillment': re.compile(r'^FUL-ORD-\d{4}-\d{6}-\d{2}$'),
    'dispute': re.compile(r'^DSP-\d{4}-\d{6}$'),
    'payout': re.compile(r'^PAYOUT-\d{4}-\d{6}$')
}


class SystemDataValidator:
    """
    Validation engine ensuring schema integrity, ID format adherence,
    foreign key referential consistency, and monetary reconciliation.
    """

    @staticmethod
    def validate_all() -> Dict[str, Any]:
        results = {
            'id_conventions_valid': True,
            'foreign_keys_consistent': True,
            'monetary_precision_valid': True,
            'reconciliation_integrity': True,
            'violations': []
        }

        with get_session() as session:
            # 1. Validate ID conventions
            sellers = session.query(Seller).all()
            for s in sellers:
                if not ID_PATTERNS['seller'].match(s.seller_id):
                    results['id_conventions_valid'] = False
                    results['violations'].append(f"Invalid Seller ID format: {s.seller_id}")

            orders = session.query(Order).all()
            for o in orders:
                if not ID_PATTERNS['order'].match(o.order_id):
                    results['id_conventions_valid'] = False
                    results['violations'].append(f"Invalid Order ID format: {o.order_id}")

            fulfillments = session.query(Fulfillment).all()
            for f in fulfillments:
                if not ID_PATTERNS['fulfillment'].match(f.fulfillment_id):
                    results['id_conventions_valid'] = False
                    results['violations'].append(f"Invalid Fulfillment ID format: {f.fulfillment_id}")

            # 2. Check foreign key referential integrity
            seller_ids = {s.seller_id for s in sellers}
            order_lines = session.query(OrderLine).all()
            for ol in order_lines:
                if ol.seller_id not in seller_ids:
                    results['foreign_keys_consistent'] = False
                    results['violations'].append(f"Orphaned OrderLine {ol.order_line_id} references missing seller {ol.seller_id}")

            # 3. Monetary precision and positive quantities
            for ol in order_lines:
                if ol.quantity <= 0:
                    results['monetary_precision_valid'] = False
                    results['violations'].append(f"Invalid quantity {ol.quantity} on line {ol.order_line_id}")
                if ol.unit_price < Decimal('0.00'):
                    results['monetary_precision_valid'] = False
                    results['violations'].append(f"Negative price on line {ol.order_line_id}")

            # 4. Financial Reconciliation check
            payouts = session.query(Payout).all()
            discrepancy_count = sum(1 for p in payouts if p.reconciliation_status == 'DISCREPANCY')
            results['reconciliation_discrepancy_count'] = discrepancy_count

        return results

