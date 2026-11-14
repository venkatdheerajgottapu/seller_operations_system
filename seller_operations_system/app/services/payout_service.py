from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import func
from database.connection import get_session
from app.models import Payout, PayoutLine, Seller, OrderLine, Fulfillment, Dispute, PayoutEvent


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

    @staticmethod
    def calculate_seller_payout_eligibility(
        seller_id: str,
        as_of_date: Optional[datetime] = None,
        hold_days: int = 14
    ) -> Dict[str, Any]:
        """
        Calculate unbilled order lines eligible for payout:
        - Order line must be DELIVERED.
        - Delivery date + hold_days must be <= as_of_date.
        - Must NOT already be paid out in any SALE payout line.
        - Deducts unbilled REFUND lines for returned orders.
        - Deducts unbilled resolved customer-favor DISPUTES.
        - Calculates reserve hold and eligible reserve releases.
        """
        target_date = as_of_date or datetime.utcnow()
        with get_session() as session:
            seller = session.query(Seller).filter(Seller.seller_id == seller_id).first()
            if not seller:
                raise ValueError(f"Seller {seller_id} not found")

            # 1. Subquery for already settled order line IDs
            settled_sales_subquery = (
                session.query(PayoutLine.order_line_id)
                .filter(PayoutLine.line_type == 'SALE', PayoutLine.order_line_id.isnot(None))
            )

            # 2. Query delivered order lines eligible by delivery date + hold period
            cutoff_date = target_date - timedelta(days=hold_days)
            eligible_lines = (
                session.query(OrderLine)
                .join(Fulfillment, OrderLine.order_line_id == Fulfillment.order_line_id)
                .filter(
                    OrderLine.seller_id == seller_id,
                    OrderLine.status == 'DELIVERED',
                    Fulfillment.status == 'DELIVERED',
                    Fulfillment.delivered_at <= cutoff_date,
                    ~OrderLine.order_line_id.in_(settled_sales_subquery)
                )
                .all()
            )

            # 3. Query unbilled refunds (returned lines)
            settled_refunds_subquery = (
                session.query(PayoutLine.order_line_id)
                .filter(PayoutLine.line_type == 'REFUND', PayoutLine.order_line_id.isnot(None))
            )
            refund_lines = (
                session.query(OrderLine)
                .filter(
                    OrderLine.seller_id == seller_id,
                    OrderLine.status == 'RETURNED',
                    ~OrderLine.order_line_id.in_(settled_refunds_subquery)
                )
                .all()
            )

            # 4. Query unbilled customer-favor disputes
            settled_disputes_subquery = (
                session.query(PayoutLine.dispute_id)
                .filter(PayoutLine.line_type == 'DISPUTE', PayoutLine.dispute_id.isnot(None))
            )
            pending_disputes = (
                session.query(Dispute)
                .filter(
                    Dispute.seller_id == seller_id,
                    Dispute.status == 'RESOLVED_CUSTOMER_FAVOR',
                    ~Dispute.dispute_id.in_(settled_disputes_subquery)
                )
                .all()
            )

            gross_amount = sum((l.line_total for l in eligible_lines), Decimal('0.00'))
            commission_deduction = sum((l.commission_amount for l in eligible_lines), Decimal('0.00'))
            refund_deduction = sum((l.line_total for l in refund_lines), Decimal('0.00'))
            dispute_deduction = sum((d.deduction_amount for d in pending_disputes), Decimal('0.00'))

            reserve_rate = seller.reserve_rate or Decimal('0.1000')
            reserve_hold_amount = (gross_amount * reserve_rate).quantize(Decimal('0.01'))

            # Check eligible reserve releases from past payouts (>60 days old)
            release_cutoff = target_date - timedelta(days=60)
            past_held_payouts = (
                session.query(Payout)
                .filter(
                    Payout.seller_id == seller_id,
                    Payout.payout_date <= release_cutoff,
                    Payout.status == 'PAID',
                    Payout.reserve_hold_amount > Decimal('0.00')
                )
                .all()
            )
            already_released_sum = (
                session.query(func.coalesce(func.sum(PayoutLine.amount), Decimal('0.00')))
                .join(Payout, PayoutLine.payout_id == Payout.payout_id)
                .filter(
                    Payout.seller_id == seller_id,
                    PayoutLine.line_type == 'RESERVE_RELEASE'
                )
                .scalar() or Decimal('0.00')
            )
            total_past_holds = sum((p.reserve_hold_amount for p in past_held_payouts), Decimal('0.00'))
            eligible_reserve_release = max(Decimal('0.00'), total_past_holds - already_released_sum)
            adjustments = eligible_reserve_release

            net_payout = (
                gross_amount - commission_deduction - refund_deduction
                - dispute_deduction - reserve_hold_amount + adjustments
            )

            return {
                'seller_id': seller_id,
                'as_of_date': target_date.isoformat(),
                'eligible_order_line_count': len(eligible_lines),
                'refund_line_count': len(refund_lines),
                'dispute_count': len(pending_disputes),
                'gross_amount': float(gross_amount),
                'commission_deduction': float(commission_deduction),
                'refund_deduction': float(refund_deduction),
                'dispute_deduction': float(dispute_deduction),
                'reserve_hold_amount': float(reserve_hold_amount),
                'adjustments': float(adjustments),
                'eligible_net_payout': float(net_payout),
                'eligible_line_ids': [l.order_line_id for l in eligible_lines],
                'refund_line_ids': [l.order_line_id for l in refund_lines],
                'dispute_ids': [d.dispute_id for d in pending_disputes],
                'eligible_reserve_release': float(eligible_reserve_release)
            }

    @staticmethod
    def generate_payout_batch(
        seller_id: str,
        as_of_date: Optional[datetime] = None,
        hold_days: int = 14,
        release_reserves: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Dynamically generate and persist a new payout settlement batch for a seller.
        """
        target_date = as_of_date or datetime.utcnow()
        with get_session() as session:
            eligibility = PayoutService.calculate_seller_payout_eligibility(
                seller_id, target_date, hold_days
            )
            if eligibility['eligible_order_line_count'] == 0 and eligibility['refund_line_count'] == 0:
                return None

            seller = session.query(Seller).filter(Seller.seller_id == seller_id).first()
            payout_count = session.query(Payout).count() + 1
            payout_id = f"PAYOUT-2026-{payout_count:06d}"
            batch_ref = f"BATCH-MANUAL-2026-{payout_count:04d}"

            gross = Decimal(str(eligibility['gross_amount']))
            commission = Decimal(str(eligibility['commission_deduction']))
            refunds = Decimal(str(eligibility['refund_deduction']))
            disputes = Decimal(str(eligibility['dispute_deduction']))
            reserve_hold = Decimal(str(eligibility['reserve_hold_amount']))
            adjustments = Decimal(str(eligibility['adjustments'])) if release_reserves else Decimal('0.00')

            net_payout = gross - commission - refunds - disputes - reserve_hold + adjustments

            payout = Payout(
                payout_id=payout_id,
                seller_id=seller_id,
                batch_reference=batch_ref,
                payout_date=target_date,
                status='SCHEDULED',
                gross_amount=gross,
                commission_deduction=commission,
                refund_deduction=refunds,
                dispute_deduction=disputes,
                reserve_hold_amount=reserve_hold,
                adjustments=adjustments,
                net_payout_amount=net_payout,
                reconciliation_status='RECONCILED',
                created_at=target_date,
                updated_at=target_date
            )
            session.add(payout)
            session.flush()

            line_idx = 1
            lines = session.query(OrderLine).filter(OrderLine.order_line_id.in_(eligibility['eligible_line_ids'])).all()
            for l in lines:
                session.add(PayoutLine(
                    payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                    payout_id=payout_id,
                    order_line_id=l.order_line_id,
                    line_type='SALE',
                    amount=l.line_total,
                    description=f"Gross sale credit for line {l.order_line_id}"
                ))
                line_idx += 1
                session.add(PayoutLine(
                    payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                    payout_id=payout_id,
                    order_line_id=l.order_line_id,
                    line_type='COMMISSION',
                    amount=-l.commission_amount,
                    description=f"Marketplace commission fee on line {l.order_line_id}"
                ))
                line_idx += 1

            ref_lines = session.query(OrderLine).filter(OrderLine.order_line_id.in_(eligibility['refund_line_ids'])).all()
            for rl in ref_lines:
                session.add(PayoutLine(
                    payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                    payout_id=payout_id,
                    order_line_id=rl.order_line_id,
                    line_type='REFUND',
                    amount=-rl.line_total,
                    description=f"Customer refund debit for returned line {rl.order_line_id}"
                ))
                line_idx += 1

            if reserve_hold > Decimal('0.00'):
                session.add(PayoutLine(
                    payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                    payout_id=payout_id,
                    line_type='RESERVE_HOLD',
                    amount=-reserve_hold,
                    description=f"Rolling reserve hold ({(Decimal(str(seller.reserve_rate or 0.1)) * 100):.1f}%)"
                ))
                line_idx += 1

            if release_reserves and adjustments > Decimal('0.00'):
                session.add(PayoutLine(
                    payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                    payout_id=payout_id,
                    line_type='RESERVE_RELEASE',
                    amount=adjustments,
                    description="Rolling reserve release after hold period"
                ))
                line_idx += 1

            disp_records = session.query(Dispute).filter(Dispute.dispute_id.in_(eligibility['dispute_ids'])).all()
            for d in disp_records:
                session.add(PayoutLine(
                    payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                    payout_id=payout_id,
                    order_line_id=d.order_line_id,
                    dispute_id=d.dispute_id,
                    line_type='DISPUTE',
                    amount=-d.deduction_amount,
                    description=f"Chargeback debit for dispute {d.dispute_id}"
                ))
                line_idx += 1

            session.add(PayoutEvent(
                payout_id=payout_id,
                previous_status='CREATED',
                new_status='SCHEDULED',
                note=f"Manual batch payout generated for seller {seller_id}",
                event_timestamp=target_date
            ))

            session.commit()
            return PayoutService.get_payout_details(payout_id)

