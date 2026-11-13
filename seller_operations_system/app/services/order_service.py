from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from database.connection import get_session
from app.models import Order, OrderLine, ProductListing, OrderStatusEvent


class OrderService:
    """Order operations, multi-seller splitting, and order lifecycle tracking."""

    @staticmethod
    def get_orders(
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        with get_session() as session:
            query = session.query(Order)
            if status_filter:
                query = query.filter(Order.order_status == status_filter)
            
            total_count = query.count()
            orders = (
                query.order_by(Order.order_date.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
            return {
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'orders': [o.to_dict() for o in orders]
            }

    @staticmethod
    def get_order_details(order_id: str) -> Optional[Dict[str, Any]]:
        with get_session() as session:
            order = session.query(Order).filter(Order.order_id == order_id).first()
            if not order:
                return None
            
            lines = session.query(OrderLine).filter(OrderLine.order_id == order_id).all()
            events = session.query(OrderStatusEvent).filter(OrderStatusEvent.order_id == order_id).order_by(OrderStatusEvent.event_timestamp.asc()).all()

            data = order.to_dict()
            data['lines'] = [l.to_dict() for l in lines]
            data['events'] = [{
                'event_id': e.event_id,
                'previous_status': e.previous_status,
                'new_status': e.new_status,
                'reason': e.reason,
                'timestamp': e.event_timestamp.isoformat()
            } for e in events]
            
            # Multi-seller check: count distinct sellers in line items
            distinct_sellers = {l.seller_id for l in lines}
            data['is_multi_seller'] = len(distinct_sellers) > 1
            data['seller_count'] = len(distinct_sellers)
            data['seller_ids'] = list(distinct_sellers)
            return data

    @staticmethod
    def update_order_status(order_id: str, new_status: str, reason: str = "Marketplace status update") -> Dict[str, Any]:
        with get_session() as session:
            order = session.query(Order).filter(Order.order_id == order_id).first()
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            old_status = order.order_status
            order.order_status = new_status
            order.updated_at = datetime.utcnow()

            # Cascade line item status
            session.query(OrderLine).filter(OrderLine.order_id == order_id).update({'status': new_status})

            event = OrderStatusEvent(
                order_id=order_id,
                previous_status=old_status,
                new_status=new_status,
                reason=reason,
                event_timestamp=datetime.utcnow()
            )
            session.add(event)
            session.commit()
            return order.to_dict()

