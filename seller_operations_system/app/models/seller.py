from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, Enum, Index
from sqlalchemy.orm import relationship
from database.connection import Base

SELLER_STATUSES = ('ACTIVE', 'SUSPENDED', 'UNDER_REVIEW', 'TERMINATED')


class Seller(Base):
    __tablename__ = 'sellers'

    seller_id = Column(String(32), primary_key=True)  # SELL-000001
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    status = Column(Enum(*SELLER_STATUSES, name='seller_status_enum', validate_strings=True, create_constraint=True), default='ACTIVE', nullable=False, index=True)
    
    # Service Level Agreement (SLA) & Quality Metrics
    rating = Column(Numeric(3, 2), default=5.00, nullable=False)
    on_time_shipment_rate = Column(Numeric(5, 2), default=100.00, nullable=False)
    fulfillment_rate = Column(Numeric(5, 2), default=100.00, nullable=False)
    cancellation_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    return_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    dispute_rate = Column(Numeric(5, 2), default=0.00, nullable=False)
    
    # Financial reserve requirement (e.g. 10% reserve hold)
    reserve_rate = Column(Numeric(5, 4), default=0.1000, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    listings = relationship('ProductListing', back_populates='seller', cascade='all, delete-orphan')
    order_lines = relationship('OrderLine', back_populates='seller')
    fulfillments = relationship('Fulfillment', back_populates='seller')
    reviews = relationship('CustomerReview', back_populates='seller')
    disputes = relationship('Dispute', back_populates='seller')
    payouts = relationship('Payout', back_populates='seller')
    status_events = relationship('SellerStatusEvent', back_populates='seller', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_seller_status_rating', 'status', 'rating'),
    )

    def to_dict(self):
        return {
            'seller_id': self.seller_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'status': self.status,
            'rating': float(self.rating) if self.rating is not None else 0.0,
            'on_time_shipment_rate': float(self.on_time_shipment_rate) if self.on_time_shipment_rate is not None else 0.0,
            'fulfillment_rate': float(self.fulfillment_rate) if self.fulfillment_rate is not None else 0.0,
            'cancellation_rate': float(self.cancellation_rate) if self.cancellation_rate is not None else 0.0,
            'return_rate': float(self.return_rate) if self.return_rate is not None else 0.0,
            'dispute_rate': float(self.dispute_rate) if self.dispute_rate is not None else 0.0,
            'reserve_rate': float(self.reserve_rate) if self.reserve_rate is not None else 0.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

