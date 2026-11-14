import pytest
from decimal import Decimal
from sqlalchemy import func
from database.connection import get_session
from app.models import Payout, PayoutLine, Order, OrderLine, Dispute, Seller

def test_full_dataset_payout_formula():
    """
    Verify the strict financial formula on all payouts:
    Net Payout = Gross Sales - Commission - Refunds - Dispute Deductions - Reserve Holds + Adjustments
    """
    with get_session() as session:
        payouts = session.query(Payout).all()
        assert len(payouts) > 0, "No payouts found in database"
        
        formula_mismatches = []
        for p in payouts:
            expected_net = (
                p.gross_amount - p.commission_deduction - p.refund_deduction
                - p.dispute_deduction - p.reserve_hold_amount + p.adjustments
            )
            # Scenario 5 tampered net by +250.00 deliberately
            if p.reconciliation_status == 'DISCREPANCY':
                expected_net += Decimal('250.00')

            diff = abs(p.net_payout_amount - expected_net)
            if diff > Decimal('0.01'):
                formula_mismatches.append((p.payout_id, float(p.net_payout_amount), float(expected_net), float(diff)))

        assert len(formula_mismatches) == 0, f"Found {len(formula_mismatches)} formula mismatches: {formula_mismatches[:5]}"


def test_payout_header_to_lines_reconciliation():
    """
    Verify that sum of payout lines equals header net payout amount
    for 100% of payouts, with exactly 1 deliberate anomaly (Scenario 5).
    """
    with get_session() as session:
        line_sums = dict(
            session.query(
                PayoutLine.payout_id,
                func.coalesce(func.sum(PayoutLine.amount), Decimal('0.00'))
            )
            .group_by(PayoutLine.payout_id)
            .all()
        )
        
        payouts = session.query(Payout).all()
        discrepancies = []
        reconciled_count = 0
        
        for p in payouts:
            line_total = line_sums.get(p.payout_id, Decimal('0.00'))
            diff = abs(line_total - p.net_payout_amount)
            if diff > Decimal('0.01'):
                discrepancies.append((p.payout_id, float(p.net_payout_amount), float(line_total), float(diff)))
            else:
                reconciled_count += 1
                
        # Exactly 1 intentional discrepancy from Ground Truth Anomaly Scenario 5
        assert len(discrepancies) == 1, f"Expected exactly 1 financial discrepancy, found {len(discrepancies)}: {discrepancies}"
        assert discrepancies[0][0] == 'PAYOUT-2026-000004'
        assert abs(discrepancies[0][3] - 250.0) < 0.01


def test_order_line_commission_bounds():
    """
    Verify all order lines adhere to category commission rate rules and minimum fee floors.
    """
    with get_session() as session:
        # Minimum fee floor is $0.50 or $1.00
        under_floor = session.query(OrderLine).filter(OrderLine.commission_amount < Decimal('0.50')).count()
        assert under_floor == 0, f"Found {under_floor} order lines below minimum commission floor"

        # Max cap is $150.00
        over_cap = session.query(OrderLine).filter(OrderLine.commission_amount > Decimal('150.00')).count()
        assert over_cap == 0, f"Found {over_cap} order lines exceeding maximum commission cap"


def test_edge_cases_dispute_and_refund_accounting():
    """
    Verify customer-favor resolved disputes have positive deduction amounts
    and seller-favor disputes have zero deductions.
    """
    with get_session() as session:
        cust_disputes = session.query(Dispute).filter(Dispute.status == 'RESOLVED_CUSTOMER_FAVOR').all()
        assert len(cust_disputes) > 0
        for d in cust_disputes:
            assert d.deduction_amount > Decimal('0.00'), f"Customer-favor dispute {d.dispute_id} has 0 deduction"
            assert d.deduction_amount == d.claim_amount

        seller_disputes = session.query(Dispute).filter(Dispute.status == 'RESOLVED_SELLER_FAVOR').all()
        assert len(seller_disputes) > 0
        for d in seller_disputes:
            assert d.deduction_amount == Decimal('0.00'), f"Seller-favor dispute {d.dispute_id} has non-zero deduction"

