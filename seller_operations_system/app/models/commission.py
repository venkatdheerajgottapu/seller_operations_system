from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, Boolean, Index
from database.connection import Base


class CommissionRule(Base):
    __tablename__ = 'commission_rules'

    rule_id = Column(String(32), primary_key=True)  # RULE-2026-000001
    category = Column(String(80), nullable=False, index=True)
    base_rate = Column(Numeric(5, 4), nullable=False)  # e.g. 0.0800 (8%)
    min_commission = Column(Numeric(10, 2), default=0.50, nullable=False)
    max_commission = Column(Numeric(10, 2), nullable=True)
    
    effective_from = Column(DateTime, nullable=False, index=True)
    effective_to = Column(DateTime, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_commission_cat_dates', 'category', 'effective_from', 'effective_to'),
    )

    def to_dict(self):
        return {
            'rule_id': self.rule_id,
            'category': self.category,
            'base_rate': float(self.base_rate) if self.base_rate is not None else 0.0,
            'min_commission': float(self.min_commission) if self.min_commission is not None else 0.0,
            'max_commission': float(self.max_commission) if self.max_commission is not None else None,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'is_active': self.is_active
        }

