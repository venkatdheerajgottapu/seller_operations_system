from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from database.connection import get_session
from app.models import Payout, PayoutLine, Seller, OrderLine, PayoutEvent


class PayoutService:
    """
    Seller payout calculations, reserve holds, and strict financial reconciliation.
    Formula:
    Net payout = Gross sales - Commission - Refunds - Dispute deductions - Reserve holds + Adjustments
    """

    @staticmethod
    def get_payouts(
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        with get_session() as session:
            query = session.query(Payout)
            if status_filter:
                query = query.filter(Payout.status == status_filter)

            total_count = query.count()
            payouts = (
                query.order_by(Payout.payout_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return {
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'payouts': [p.to_dict() for p in payouts]
            }

    @staticmethod
    def get_payout_details(payout_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as session:
            payout = session.query(Payout).filter(Payout.payout_id == payout_id).first()
            if not payout:
                return None

            lines = session.query(PayoutLine).filter(PayoutLine.payout_id == payout_id).all()
            events = session.query(PayoutEvent).filter(PayoutEvent.payout_id == payout_id).all()

            data = payout.to_dict()
            data['lines'] = [l.to_dict() for l in lines]
            data['events'] = [{
                'event_id': e.event_id,
                'previous_status': e.previous_status,
                'new_status': e.new_status,
                'note': e.note,
                'timestamp': e.event_timestamp.isoformat()
            } for e in events]
            
            # Reconcile lines vs header
            sum_of_lines = sum(Decimal(str(l.amount)) for l in lines)
            header_net = Decimal(str(payout.net_payout_amount))
            discrepancy = sum_of_lines - header_net

            data['sum_of_lines'] = float(sum_of_lines)
            data['discrepancy'] = float(discrepancy)
            data['is_reconciled'] = (discrepancy == Decimal('0.00'))
            return data

    @staticmethod
    def reconcile_payout(payout_id: str) -> Dict[str, Any]:
        """
        Verify that the payout header net total reconciles with the sum of its payout lines.
        """
        with get_session() as session:
            payout = session.query(Payout).filter(Payout.payout_id == payout_id).first()
            if not payout:
                raise ValueError(f"Payout {payout_id} not found")

            lines = session.query(PayoutLine).filter(PayoutLine.payout_id == payout_id).all()
            line_sum = sum(l.amount for l in lines)
            header_net = payout.net_payout_amount

            # Check financial formula adherence
            expected_net = (
                payout.gross_amount
                - payout.commission_deduction
                - payout.refund_deduction
                - payout.dispute_deduction
                - payout.reserve_hold_amount
                + payout.adjustments
            )

            formula_match = (header_net == expected_net)
            line_match = (header_net == line_sum)

            if formula_match and line_match:
                payout.reconciliation_status = 'RECONCILED'
            else:
                payout.reconciliation_status = 'DISCREPANCY'

            session.commit()
            return {
                'payout_id': payout_id,
                'header_net': float(header_net),
                'expected_net': float(expected_net),
                'lines_sum': float(line_sum),
                'reconciliation_status': payout.reconciliation_status,
                'discrepancy_amount': float(line_sum - header_net)
            }

