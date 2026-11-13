from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index
from database.connection import Base


class AnomalyRecord(Base):
    __tablename__ = 'anomalies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    scenario_id = Column(Integer, nullable=False, index=True)  # 1 to 5
    scenario_name = Column(String(120), nullable=False)
    entity_type = Column(String(64), nullable=False, index=True)  # 'PAYOUT', 'COMMISSION', etc.
    entity_id = Column(String(64), nullable=False, index=True)
    detected_by = Column(String(32), nullable=False, default='DETECTOR_ENGINE', index=True)  # 'GROUND_TRUTH' or 'DETECTOR_ENGINE'
    is_ground_truth = Column(Boolean, default=False, nullable=False, index=True)
    severity = Column(String(20), default='HIGH', nullable=False)
    description = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_anomaly_entity', 'entity_type', 'entity_id'),
        Index('idx_anomaly_scenario_truth', 'scenario_id', 'is_ground_truth'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'detected_by': self.detected_by,
            'is_ground_truth': self.is_ground_truth,
            'severity': self.severity,
            'description': self.description,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

