from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Set, Tuple
from sqlalchemy import func
from database.connection import get_session
from app.models import (
    Seller, ProductListing, OrderLine, Fulfillment,
    Dispute, Payout, PayoutLine, AnomalyRecord
)


class AnomalyDetectorService:
    """
    Independent Rule-Based Anomaly Detection Engine.
    Evaluates business rule invariants against runtime database records.
    NEVER reads the ground_truth records during detection!
    """

    @staticmethod
    def run_detection_scan() -> List[Dict[str, Any]]:
        """
        Run all 5 business anomaly rules and persist detected violations.
        """
        detected_anomalies: List[AnomalyRecord] = []

        with get_session() as session:
            # Clear previous runtime detection records (leave ground_truth intact)
            session.query(AnomalyRecord).filter(
                AnomalyRecord.detected_by == 'DETECTOR_ENGINE'
            ).delete()
            session.flush()

            # -------------------------------------------------------------
            # RULE 1: Payout before delivery or reserve release
            # Invariant: A payout marked as PAID must only include order lines
            # whose fulfillment status is 'DELIVERED'.
            # -------------------------------------------------------------
            undelivered_paid = (
                session.query(Payout.payout_id, Fulfillment.order_line_id, Fulfillment.status)
                .join(PayoutLine, Payout.payout_id == PayoutLine.payout_id)
                .join(Fulfillment, PayoutLine.order_line_id == Fulfillment.order_line_id)
                .filter(
                    Payout.status == 'PAID',
                    PayoutLine.line_type == 'SALE',
                    Fulfillment.status != 'DELIVERED'
                )
                .all()
            )

            for payout_id, order_line_id, status in undelivered_paid:
                rec = AnomalyRecord(
                    scenario_id=1,
                    scenario_name="Payout Before Delivery or Hold Release",
                    entity_type="PAYOUT",
                    entity_id=payout_id,
                    detected_by="DETECTOR_ENGINE",
                    is_ground_truth=False,
                    severity="CRITICAL",
                    description=f"Payout {payout_id} is PAID but line {order_line_id} is in status '{status}'",
                    details=f"payout_id={payout_id}, order_line_id={order_line_id}, status={status}"
                )
                detected_anomalies.append(rec)
                session.add(rec)

            # -------------------------------------------------------------
            # RULE 2: Commission applied twice
            # Invariant: Each order line should have at most ONE commission deduction.
            # -------------------------------------------------------------
            dup_commissions = (
                session.query(PayoutLine.order_line_id, func.count(PayoutLine.payout_line_id))
                .filter(
                    PayoutLine.line_type == 'COMMISSION',
                    PayoutLine.order_line_id.isnot(None)
                )
                .group_by(PayoutLine.order_line_id)
                .having(func.count(PayoutLine.payout_line_id) > 1)
                .all()
            )

            for order_line_id, count in dup_commissions:
                rec = AnomalyRecord(
                    scenario_id=2,
                    scenario_name="Duplicate Commission Applied",
                    entity_type="COMMISSION",
                    entity_id=order_line_id,
                    detected_by="DETECTOR_ENGINE",
                    is_ground_truth=False,
                    severity="HIGH",
                    description=f"Order line {order_line_id} has {count} commission deduction entries in payout lines",
                    details=f"order_line_id={order_line_id}, duplicate_count={count}"
                )
                detected_anomalies.append(rec)
                session.add(rec)

            # -------------------------------------------------------------
            # RULE 3: Suspended seller continues listing
            # Invariant: A seller in 'SUSPENDED' status must not have any 'ACTIVE' listings.
            # -------------------------------------------------------------
            suspended_with_active = (
                session.query(ProductListing, Seller)
                .join(Seller, ProductListing.seller_id == Seller.seller_id)
                .filter(
                    Seller.status == 'SUSPENDED',
                    ProductListing.status == 'ACTIVE'
                )
                .all()
            )

            seen_sellers = set()
            for listing, seller in suspended_with_active:
                if seller.seller_id not in seen_sellers:
                    seen_sellers.add(seller.seller_id)
                    rec = AnomalyRecord(
                        scenario_id=3,
                        scenario_name="Suspended Seller Continues Listing",
                        entity_type="SELLER",
                        entity_id=seller.seller_id,
                        detected_by="DETECTOR_ENGINE",
                        is_ground_truth=False,
                        severity="HIGH",
                        description=f"Suspended seller {seller.seller_id} still has active listing {listing.listing_id}",
                        details=f"seller_id={seller.seller_id}, listing_id={listing.listing_id}, status={listing.status}"
                    )
                    detected_anomalies.append(rec)
                    session.add(rec)

            # -------------------------------------------------------------
            # RULE 4: Dispute not deducted from payout
            # Invariant: If an order line was paid out and had a resolved customer-favor dispute,
            # there MUST be a corresponding DISPUTE deduction in the payout lines.
            # -------------------------------------------------------------
            settled_sales = dict(
                session.query(PayoutLine.order_line_id, PayoutLine.payout_id)
                .filter(PayoutLine.line_type == 'SALE', PayoutLine.order_line_id.isnot(None))
                .all()
            )
            deducted_dispute_ids = set(
                r[0] for r in session.query(PayoutLine.dispute_id)
                .filter(PayoutLine.line_type == 'DISPUTE', PayoutLine.dispute_id.isnot(None))
                .all()
            )
            customer_favor_disputes = session.query(Dispute).filter(
                Dispute.status == 'RESOLVED_CUSTOMER_FAVOR'
            ).all()

            for d in customer_favor_disputes:
                payout_id = settled_sales.get(d.order_line_id)
                if payout_id and d.dispute_id not in deducted_dispute_ids:
                    rec = AnomalyRecord(
                        scenario_id=4,
                        scenario_name="Dispute Not Deducted From Payout",
                        entity_type="DISPUTE",
                        entity_id=d.dispute_id,
                        detected_by="DETECTOR_ENGINE",
                        is_ground_truth=False,
                        severity="HIGH",
                        description=f"Dispute {d.dispute_id} resolved in customer favor (${d.claim_amount}) was not deducted from payout {payout_id}",
                        details=f"dispute_id={d.dispute_id}, claim_amount={d.claim_amount}, payout_id={payout_id}"
                    )
                    detected_anomalies.append(rec)
                    session.add(rec)

            # -------------------------------------------------------------
            # RULE 5: Payout total does not match payout lines (Financial discrepancy)
            # Invariant: sum(lines.amount) == header.net_payout_amount
            # -------------------------------------------------------------
            line_sums = dict(
                session.query(
                    PayoutLine.payout_id,
                    func.coalesce(func.sum(PayoutLine.amount), Decimal('0.00'))
                )
                .group_by(PayoutLine.payout_id)
                .all()
            )

            all_payouts = session.query(Payout).all()
            for p in all_payouts:
                line_sum = line_sums.get(p.payout_id, Decimal('0.00'))
                header_net = p.net_payout_amount
                diff = abs(line_sum - header_net)

                if diff > Decimal('0.01'):
                    p.reconciliation_status = 'DISCREPANCY'
                    rec = AnomalyRecord(
                        scenario_id=5,
                        scenario_name="Payout Total Discrepancy",
                        entity_type="RECONCILIATION",
                        entity_id=p.payout_id,
                        detected_by="DETECTOR_ENGINE",
                        is_ground_truth=False,
                        severity="CRITICAL",
                        description=f"Payout {p.payout_id} header net ({header_net}) does not match lines sum ({line_sum}) by {diff}",
                        details=f"header_net={header_net}, lines_sum={line_sum}, variance={diff}"
                    )
                    detected_anomalies.append(rec)
                    session.add(rec)
                else:
                    p.reconciliation_status = 'RECONCILED'

            session.commit()

        return [a.to_dict() for a in detected_anomalies]

    @staticmethod
    def evaluate_against_ground_truth() -> Dict[str, Any]:
        """
        Compare rule-detected anomalies against independent ground-truth records.
        Computes True Positives, False Positives, False Negatives, True Negatives,
        Precision, Recall, and F1-Score.
        """
        with get_session() as session:
            # 1. Fetch Ground Truth set: (scenario_id, entity_type, entity_id)
            gt_records = session.query(AnomalyRecord).filter(
                AnomalyRecord.detected_by == 'GROUND_TRUTH'
            ).all()

            # 2. Fetch Detected set: (scenario_id, entity_type, entity_id)
            det_records = session.query(AnomalyRecord).filter(
                AnomalyRecord.detected_by == 'DETECTOR_ENGINE'
            ).all()

            # If no detections yet, run scan automatically
            if not det_records:
                AnomalyDetectorService.run_detection_scan()
                det_records = session.query(AnomalyRecord).filter(
                    AnomalyRecord.detected_by == 'DETECTOR_ENGINE'
                ).all()

            gt_set: Set[Tuple[int, str, str]] = {
                (r.scenario_id, r.entity_type, r.entity_id) for r in gt_records
            }
            det_set: Set[Tuple[int, str, str]] = {
                (r.scenario_id, r.entity_type, r.entity_id) for r in det_records
            }

            # Set calculations
            tp_set = gt_set.intersection(det_set)
            fp_set = det_set.difference(gt_set)
            fn_set = gt_set.difference(det_set)

            tp = len(tp_set)
            fp = len(fp_set)
            fn = len(fn_set)

            # Estimate True Negatives from total transaction space (entities inspected - positives)
            total_sellers = session.query(Seller).count()
            total_orders = session.query(OrderLine).count()
            total_payouts = session.query(Payout).count()
            total_disputes = session.query(Dispute).count()
            total_population = total_sellers + total_orders + total_payouts + total_disputes
            tn = max(0, total_population - (tp + fp + fn))

            precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
            recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

            # Breakdown per scenario
            scenarios_breakdown = {}
            for scenario_id in range(1, 6):
                s_gt = {x for x in gt_set if x[0] == scenario_id}
                s_det = {x for x in det_set if x[0] == scenario_id}
                s_tp = len(s_gt.intersection(s_det))
                s_fp = len(s_det.difference(s_gt))
                s_fn = len(s_gt.difference(s_det))
                s_prec = (s_tp / (s_tp + s_fp)) if (s_tp + s_fp) > 0 else 1.0
                s_rec = (s_tp / (s_tp + s_fn)) if (s_tp + s_fn) > 0 else 1.0
                s_f1 = (2 * s_prec * s_rec / (s_prec + s_rec)) if (s_prec + s_rec) > 0 else 0.0
                
                scenarios_breakdown[f"Scenario_{scenario_id}"] = {
                    'ground_truth_count': len(s_gt),
                    'detected_count': len(s_det),
                    'true_positives': s_tp,
                    'false_positives': s_fp,
                    'false_negatives': s_fn,
                    'precision': round(s_prec, 4),
                    'recall': round(s_rec, 4),
                    'f1_score': round(s_f1, 4)
                }

            return {
                'confusion_matrix': {
                    'true_positives': tp,
                    'false_positives': fp,
                    'false_negatives': fn,
                    'true_negatives': tn
                },
                'metrics': {
                    'precision': round(precision, 4),
                    'recall': round(recall, 4),
                    'f1_score': round(f1, 4),
                    'accuracy': round((tp + tn) / total_population, 4) if total_population > 0 else 1.0
                },
                'scenarios': scenarios_breakdown,
                'detected_records': [r.to_dict() for r in det_records],
                'ground_truth_records': [r.to_dict() for r in gt_records]
            }
