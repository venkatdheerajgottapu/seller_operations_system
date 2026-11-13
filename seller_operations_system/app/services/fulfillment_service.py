from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from database.connection import get_session
from app.models import Fulfillment, FulfillmentEvent, OrderLine, Order


class FulfillmentService:
    """Shipment dispatch, delivery tracking, and shipping delay monitoring."""

    @staticmethod
    def get_fulfillments(
        status_filter: Optional[str] = None,
        delayed_only: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        with get_session() as session:
            query = session.query(Fulfillment)
            if status_filter:
                query = query.filter(Fulfillment.status == status_filter)
            if delayed_only:
                query = query.filter(Fulfillment.is_delayed.is_(True))

            total_count = query.count()
            fulfillments = (
                query.order_by(Fulfillment.shipped_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return {
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'fulfillments': [f.to_dict() for f in fulfillments]
            }

    @staticmethod
    def record_delivery(fulfillment_id: str, delivered_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Record package delivery and compute delay metrics."""
        delivered_at = delivered_at or datetime.utcnow()
        with get_session() as session:
            f = session.query(Fulfillment).filter(Fulfillment.fulfillment_id == fulfillment_id).first()
            if not f:
                raise ValueError(f"Fulfillment {fulfillment_id} not found")

            f.status = 'DELIVERED'
            f.delivered_at = delivered_at
            
            # Check if delivered after estimated delivery
            if f.estimated_delivery and delivered_at > f.estimated_delivery:
                f.is_delayed = True
                f.delay_days = (delivered_at.date() - f.estimated_delivery.date()).days
            else:
                f.is_delayed = False
                f.delay_days = 0

            # Update corresponding order line
            session.query(OrderLine).filter(OrderLine.order_line_id == f.order_line_id).update({'status': 'DELIVERED'})

            # Add event
            event = FulfillmentEvent(
                fulfillment_id=fulfillment_id,
                event_type='DELIVERED',
                location='Customer Doorstep',
                notes=f"Signature confirmed. Delayed: {f.is_delayed} ({f.delay_days} days)",
                event_timestamp=delivered_at
            )
            session.add(event)
            session.commit()
            return f.to_dict()

