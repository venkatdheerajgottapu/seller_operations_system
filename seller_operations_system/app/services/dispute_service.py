from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from database.connection import get_session
from app.models import Dispute, OrderLine


class DisputeService:
    """Dispute tracking, chargeback deductions, and resolution workflow."""

    @staticmethod
    def get_disputes(
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        with get_session() as session:
            query = session.query(Dispute)
            if status_filter:
                query = query.filter(Dispute.status == status_filter)

            total_count = query.count()
            disputes = (
                query.order_by(Dispute.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return {
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'disputes': [d.to_dict() for d in disputes]
            }

    @staticmethod
    def resolve_dispute(dispute_id: str, resolution: str) -> Dict[str, Any]:
        """
        Resolve dispute (e.g. RESOLVED_CUSTOMER_FAVOR, RESOLVED_SELLER_FAVOR).
        If in customer favor, deduct claim amount.
        """
        with get_session() as session:
            dispute = session.query(Dispute).filter(Dispute.dispute_id == dispute_id).first()
            if not dispute:
                raise ValueError(f"Dispute {dispute_id} not found")

            dispute.status = resolution
            dispute.resolution_date = datetime.utcnow()
            dispute.updated_at = datetime.utcnow()

            if resolution in ('RESOLVED_CUSTOMER_FAVOR', 'CHARGEBACK_LOST'):
                dispute.deduction_amount = dispute.claim_amount
            else:
                dispute.deduction_amount = Decimal('0.00')

            session.commit()
            return dispute.to_dict()

