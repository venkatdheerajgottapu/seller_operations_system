from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.connection import Base

FULFILLMENT_STATUSES = (
    'AWAITING_PICKUP', 'IN_TRANSIT', 'OUT_FOR_DELIVERY',
    'DELIVERED', 'DELAYED', 'RETURNED', 'FAILED'
)


class Fulfillment(Base):
    __tablename__ = 'fulfillments'

    fulfillment_id = Column(String(48), primary_key=True)  # FUL-<order-line-id>
    order_line_id = Column(String(48), ForeignKey('order_lines.order_line_id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    order_id = Column(String(32), ForeignKey('orders.order_id'), nullable=False, index=True)
    seller_id = Column(String(32), ForeignKey('sellers.seller_id'), nullable=False, index=True)
    
    tracking_number = Column(String(80), unique=True, nullable=False, index=True)
    carrier = Column(String(64), nullable=False)
    status = Column(Enum(*FULFILLMENT_STATUSES, name='fulfillment_status_enum', validate_strings=True, create_constraint=True), default='AWAITING_PICKUP', nullable=False, index=True)
    
    shipped_at = Column(DateTime, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    
    is_delayed = Column(Boolean, default=False, nullable=False, index=True)
    delay_days = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order_line = relationship('OrderLine', back_populates='fulfillment')
    order = relationship('Order', back_populates='fulfillments')
    seller = relationship('Seller', back_populates='fulfillments')
    events = relationship('FulfillmentEvent', back_populates='fulfillment', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_fulfillment_seller_status', 'seller_id', 'status'),
    )

    def to_dict(self):
        return {
            'fulfillment_id': self.fulfillment_id,
            'order_line_id': self.order_line_id,
            'order_id': self.order_id,
            'seller_id': self.seller_id,
            'tracking_number': self.tracking_number,
            'carrier': self.carrier,
            'status': self.status,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'estimated_delivery': self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'is_delayed': self.is_delayed,
            'delay_days': self.delay_days,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

