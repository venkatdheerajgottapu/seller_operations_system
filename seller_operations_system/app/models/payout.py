from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.connection import Base

PAYOUT_STATUSES = ('SCHEDULED', 'PROCESSING', 'HELD', 'PAID', 'FAILED', 'CANCELLED')
RECONCILIATION_STATUSES = ('RECONCILED', 'DISCREPANCY', 'UNRECONCILED')
PAYOUT_LINE_TYPES = (
    'SALE', 'COMMISSION', 'REFUND', 'DISPUTE',
    'RESERVE_HOLD', 'RESERVE_RELEASE', 'ADJUSTMENT'
)


class Payout(Base):
    __tablename__ = 'payouts'

    payout_id = Column(String(32), primary_key=True)  # PAYOUT-2026-000001
    seller_id = Column(String(32), ForeignKey('sellers.seller_id'), nullable=False, index=True)
    batch_reference = Column(String(64), nullable=False, index=True)
    payout_date = Column(DateTime, nullable=False, index=True)
    status = Column(Enum(*PAYOUT_STATUSES, name='payout_status_enum'), default='SCHEDULED', nullable=False, index=True)

    # Financial Breakdown
    gross_amount = Column(Numeric(12, 2), nullable=False)
    commission_deduction = Column(Numeric(12, 2), default=0.00, nullable=False)
    refund_deduction = Column(Numeric(12, 2), default=0.00, nullable=False)
    dispute_deduction = Column(Numeric(12, 2), default=0.00, nullable=False)
    reserve_hold_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    adjustments = Column(Numeric(12, 2), default=0.00, nullable=False)
    
    # Financial Formula: Net = Gross - Comm - Refund - Dispute - Reserve + Adjustments
    net_payout_amount = Column(Numeric(12, 2), nullable=False)
    
    # Audit & Reconciliation
    reconciliation_status = Column(
        Enum(*RECONCILIATION_STATUSES, name='reconciliation_status_enum'),
        default='RECONCILED',
        nullable=False,
        index=True
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    seller = relationship('Seller', back_populates='payouts')
    lines = relationship('PayoutLine', back_populates='payout', cascade='all, delete-orphan')
    status_events = relationship('PayoutEvent', back_populates='payout', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_payout_seller_date', 'seller_id', 'payout_date'),
    )

    def to_dict(self):
        return {
            'payout_id': self.payout_id,
            'seller_id': self.seller_id,
            'batch_reference': self.batch_reference,
            'payout_date': self.payout_date.isoformat() if self.payout_date else None,
            'status': self.status,
            'gross_amount': float(self.gross_amount) if self.gross_amount is not None else 0.0,
            'commission_deduction': float(self.commission_deduction) if self.commission_deduction is not None else 0.0,
            'refund_deduction': float(self.refund_deduction) if self.refund_deduction is not None else 0.0,
            'dispute_deduction': float(self.dispute_deduction) if self.dispute_deduction is not None else 0.0,
            'reserve_hold_amount': float(self.reserve_hold_amount) if self.reserve_hold_amount is not None else 0.0,
            'adjustments': float(self.adjustments) if self.adjustments is not None else 0.0,
            'net_payout_amount': float(self.net_payout_amount) if self.net_payout_amount is not None else 0.0,
            'reconciliation_status': self.reconciliation_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PayoutLine(Base):
    __tablename__ = 'payout_lines'

    payout_line_id = Column(String(48), primary_key=True)  # PAYLINE-2026-000001-01
    payout_id = Column(String(32), ForeignKey('payouts.payout_id', ondelete='CASCADE'), nullable=False, index=True)
    order_line_id = Column(String(48), ForeignKey('order_lines.order_line_id'), nullable=True, index=True)
    dispute_id = Column(String(32), ForeignKey('disputes.dispute_id'), nullable=True, index=True)
    
    line_type = Column(Enum(*PAYOUT_LINE_TYPES, name='payout_line_type_enum'), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)  # Positive for additions, negative for deductions
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    payout = relationship('Payout', back_populates='lines')
    order_line = relationship('OrderLine', back_populates='payout_lines')
    dispute = relationship('Dispute', back_populates='payout_lines')

    def to_dict(self):
        return {
            'payout_line_id': self.payout_line_id,
            'payout_id': self.payout_id,
            'order_line_id': self.order_line_id,
            'dispute_id': self.dispute_id,
            'line_type': self.line_type,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
