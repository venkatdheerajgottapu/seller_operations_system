from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from database.connection import Base


class Customer(Base):
    __tablename__ = 'customers'

    customer_id = Column(String(32), primary_key=True)  # CUST-000001
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    shipping_address = Column(String(255), nullable=False)
    city = Column(String(80), nullable=False)
    state = Column(String(80), nullable=False)
    postal_code = Column(String(20), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    orders = relationship('Order', back_populates='customer')
    reviews = relationship('CustomerReview', back_populates='customer')
    disputes = relationship('Dispute', back_populates='customer')

    def to_dict(self):
        return {
            'customer_id': self.customer_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'shipping_address': self.shipping_address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

