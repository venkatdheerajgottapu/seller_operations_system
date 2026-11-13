from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy import func
from database.connection import get_session
from app.models import (
    Seller, ProductListing, OrderLine, Fulfillment,
    CustomerReview, Dispute, SellerStatusEvent
)


class SellerService:
    """Business operations and SLA metric calculations for sellers."""

    @staticmethod
    def get_all_sellers(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_session() as session:
            query = session.query(Seller)
            if status_filter:
                query = query.filter(Seller.status == status_filter)
            sellers = query.order_by(Seller.seller_id.asc()).all()
            return [s.to_dict() for s in sellers]

    @staticmethod
    def get_seller_by_id(seller_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as session:
            seller = session.query(Seller).filter(Seller.seller_id == seller_id).first()
            return seller.to_dict() if seller else None

    @staticmethod
    def update_seller_status(seller_id: str, new_status: str, reason: str = "Administrative review") -> Dict[str, Any]:
        with get_session() as session:
            seller = session.query(Seller).filter(Seller.seller_id == seller_id).first()
            if not seller:
                raise ValueError(f"Seller {seller_id} not found")
            
            old_status = seller.status
            if old_status == new_status:
                return seller.to_dict()

            seller.status = new_status
            seller.updated_at = datetime.utcnow()

            # If seller is suspended, delist/inactivate active listings
            if new_status == 'SUSPENDED':
                session.query(ProductListing).filter(
                    ProductListing.seller_id == seller_id,
                    ProductListing.status == 'ACTIVE'
                ).update({'status': 'INACTIVE'})

            # Log status event
            event = SellerStatusEvent(
                seller_id=seller_id,
                previous_status=old_status,
                new_status=new_status,
                reason=reason,
                event_timestamp=datetime.utcnow()
            )
            session.add(event)
            session.commit()
            return seller.to_dict()

    @staticmethod
    def recalculate_seller_sla(seller_id: str) -> Dict[str, Any]:
        """
        Recalculate all SLA quality metrics based on historical performance.
        - On-time shipment rate
        - Fulfillment rate
        - Cancellation rate
        - Return rate
        - Dispute rate
        - Average rating
        """
        with get_session() as session:
            seller = session.query(Seller).filter(Seller.seller_id == seller_id).first()
            if not seller:
                raise ValueError(f"Seller {seller_id} not found")

            # 1. Total order lines supplied
            total_lines = session.query(func.count(OrderLine.order_line_id)).filter(
                OrderLine.seller_id == seller_id
            ).scalar() or 0

            if total_lines == 0:
                return seller.to_dict()

            # 2. Delivered & Cancelled counts
            delivered_count = session.query(func.count(OrderLine.order_line_id)).filter(
                OrderLine.seller_id == seller_id,
                OrderLine.status == 'DELIVERED'
            ).scalar() or 0

            cancelled_count = session.query(func.count(OrderLine.order_line_id)).filter(
                OrderLine.seller_id == seller_id,
                OrderLine.status == 'CANCELLED'
            ).scalar() or 0

            # 3. Fulfillments on-time vs delayed
            total_fulfillments = session.query(func.count(Fulfillment.fulfillment_id)).filter(
                Fulfillment.seller_id == seller_id,
                Fulfillment.status == 'DELIVERED'
            ).scalar() or 0

            delayed_fulfillments = session.query(func.count(Fulfillment.fulfillment_id)).filter(
                Fulfillment.seller_id == seller_id,
                Fulfillment.status == 'DELIVERED',
                Fulfillment.is_delayed.is_(True)
            ).scalar() or 0

            on_time_count = max(0, total_fulfillments - delayed_fulfillments)
            on_time_rate = Decimal(str(round((on_time_count / total_fulfillments) * 100, 2))) if total_fulfillments > 0 else Decimal('100.00')

            # 4. Return count
            returned_count = session.query(func.count(OrderLine.order_line_id)).filter(
                OrderLine.seller_id == seller_id,
                OrderLine.status == 'RETURNED'
            ).scalar() or 0
            return_rate = Decimal(str(round((returned_count / total_lines) * 100, 2)))

            # 5. Dispute count
            dispute_count = session.query(func.count(Dispute.dispute_id)).filter(
                Dispute.seller_id == seller_id
            ).scalar() or 0
            dispute_rate = Decimal(str(round((dispute_count / total_lines) * 100, 2)))

            # 6. Average customer review rating
            avg_rating = session.query(func.avg(CustomerReview.rating)).filter(
                CustomerReview.seller_id == seller_id
            ).scalar() or 5.0
            avg_rating = Decimal(str(round(float(avg_rating), 2)))

            # 7. Fulfillment and cancellation rates
            fulfillment_rate = Decimal(str(round((delivered_count / total_lines) * 100, 2)))
            cancellation_rate = Decimal(str(round((cancelled_count / total_lines) * 100, 2)))

            # Persist recalculated metrics
            seller.on_time_shipment_rate = on_time_rate
            seller.fulfillment_rate = fulfillment_rate
            seller.cancellation_rate = cancellation_rate
            seller.return_rate = return_rate
            seller.dispute_rate = dispute_rate
            seller.rating = avg_rating
            seller.updated_at = datetime.utcnow()
            session.commit()

            return seller.to_dict()

