from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.connection import Base

ORDER_STATUSES = (
    'PLACED', 'PROCESSING', 'PARTIALLY_SHIPPED',
    'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED'
)
PAYMENT_STATUSES = ('PAID', 'PENDING', 'FAILED', 'REFUNDED')
LINE_STATUSES = ('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED')


class Order(Base):
    __tablename__ = 'orders'

    order_id = Column(String(32), primary_key=True)  # ORD-2026-000001
    customer_id = Column(String(32), ForeignKey('customers.customer_id'), nullable=False, index=True)
    order_date = Column(DateTime, nullable=False, index=True)
    order_status = Column(Enum(*ORDER_STATUSES, name='order_status_enum'), default='PLACED', nullable=False, index=True)
    payment_status = Column(Enum(*PAYMENT_STATUSES, name='payment_status_enum'), default='PAID', nullable=False)
    
    total_gross_amount = Column(Numeric(12, 2), nullable=False)
    shipping_fee = Column(Numeric(10, 2), default=0.00, nullable=False)
    tax_amount = Column(Numeric(10, 2), default=0.00, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    customer = relationship('Customer', back_populates='orders')
    order_lines = relationship('OrderLine', back_populates='order', cascade='all, delete-orphan')
    fulfillments = relationship('Fulfillment', back_populates='order')
    disputes = relationship('Dispute', back_populates='order')
    status_events = relationship('OrderStatusEvent', back_populates='order', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_order_date_status', 'order_date', 'order_status'),
    )

    def to_dict(self):
        return {
            'order_id': self.order_id,
            'customer_id': self.customer_id,
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'total_gross_amount': float(self.total_gross_amount) if self.total_gross_amount is not None else 0.0,
            'shipping_fee': float(self.shipping_fee) if self.shipping_fee is not None else 0.0,
            'tax_amount': float(self.tax_amount) if self.tax_amount is not None else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OrderLine(Base):
    __tablename__ = 'order_lines'

    order_line_id = Column(String(48), primary_key=True)  # ORD-2026-000001-01
    order_id = Column(String(32), ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False, index=True)
    listing_id = Column(String(48), ForeignKey('product_listings.listing_id'), nullable=False, index=True)
    seller_id = Column(String(32), ForeignKey('sellers.seller_id'), nullable=False, index=True)

    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)
    
    commission_rate = Column(Numeric(5, 4), default=0.1000, nullable=False)
    commission_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    
    status = Column(Enum(*LINE_STATUSES, name='line_status_enum'), default='PENDING', nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship('Order', back_populates='order_lines')
    listing = relationship('ProductListing', back_populates='order_lines')
    seller = relationship('Seller', back_populates='order_lines')
    fulfillment = relationship('Fulfillment', back_populates='order_line', uselist=False, cascade='all, delete-orphan')
    review = relationship('CustomerReview', back_populates='order_line', uselist=False)
    disputes = relationship('Dispute', back_populates='order_line')
    payout_lines = relationship('PayoutLine', back_populates='order_line')

    __table_args__ = (
        Index('idx_order_line_seller_status', 'seller_id', 'status'),
    )

    def to_dict(self):
        return {
            'order_line_id': self.order_line_id,
            'order_id': self.order_id,
            'listing_id': self.listing_id,
            'seller_id': self.seller_id,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price is not None else 0.0,
            'line_total': float(self.line_total) if self.line_total is not None else 0.0,
            'commission_rate': float(self.commission_rate) if self.commission_rate is not None else 0.0,
            'commission_amount': float(self.commission_amount) if self.commission_amount is not None else 0.0,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
