from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.connection import Base

DISPUTE_TYPES = (
    'ITEM_NOT_RECEIVED', 'DAMAGED_ITEM', 'WRONG_ITEM',
    'UNAUTHORIZED_CHARGE', 'DEFECTIVE_PRODUCT'
)
DISPUTE_STATUSES = (
    'OPEN', 'UNDER_INVESTIGATION', 'RESOLVED_SELLER_FAVOR',
    'RESOLVED_CUSTOMER_FAVOR', 'CHARGEBACK_LOST', 'CANCELLED'
)


class Dispute(Base):
    __tablename__ = 'disputes'

    dispute_id = Column(String(32), primary_key=True)  # DSP-2026-000001
    order_id = Column(String(32), ForeignKey('orders.order_id'), nullable=False, index=True)
    order_line_id = Column(String(48), ForeignKey('order_lines.order_line_id'), nullable=False, index=True)
    seller_id = Column(String(32), ForeignKey('sellers.seller_id'), nullable=False, index=True)
    customer_id = Column(String(32), ForeignKey('customers.customer_id'), nullable=False, index=True)

    dispute_type = Column(Enum(*DISPUTE_TYPES, name='dispute_type_enum', validate_strings=True, create_constraint=True), nullable=False)
    status = Column(Enum(*DISPUTE_STATUSES, name='dispute_status_enum', validate_strings=True, create_constraint=True), default='OPEN', nullable=False, index=True)
    
    claim_amount = Column(Numeric(12, 2), nullable=False)
    deduction_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    
    resolution_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship('Order', back_populates='disputes')
    order_line = relationship('OrderLine', back_populates='disputes')
    seller = relationship('Seller', back_populates='disputes')
    customer = relationship('Customer', back_populates='disputes')
    payout_lines = relationship('PayoutLine', back_populates='dispute')

    __table_args__ = (
        Index('idx_dispute_seller_status', 'seller_id', 'status'),
    )

    def to_dict(self):
        return {
            'dispute_id': self.dispute_id,
            'order_id': self.order_id,
            'order_line_id': self.order_line_id,
            'seller_id': self.seller_id,
            'customer_id': self.customer_id,
            'dispute_type': self.dispute_type,
            'status': self.status,
            'claim_amount': float(self.claim_amount) if self.claim_amount is not None else 0.0,
            'deduction_amount': float(self.deduction_amount) if self.deduction_amount is not None else 0.0,
            'resolution_date': self.resolution_date.isoformat() if self.resolution_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

