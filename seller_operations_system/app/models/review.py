from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.connection import Base


class CustomerReview(Base):
    __tablename__ = 'customer_reviews'

    review_id = Column(String(32), primary_key=True)  # REV-2026-000001
    order_line_id = Column(String(48), ForeignKey('order_lines.order_line_id'), unique=True, nullable=False, index=True)
    seller_id = Column(String(32), ForeignKey('sellers.seller_id'), nullable=False, index=True)
    listing_id = Column(String(48), ForeignKey('product_listings.listing_id'), nullable=False, index=True)
    customer_id = Column(String(32), ForeignKey('customers.customer_id'), nullable=False, index=True)
    
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order_line = relationship('OrderLine', back_populates='review')
    seller = relationship('Seller', back_populates='reviews')
    listing = relationship('ProductListing', back_populates='reviews')
    customer = relationship('Customer', back_populates='reviews')

    __table_args__ = (
        Index('idx_review_seller_rating', 'seller_id', 'rating'),
    )

    def to_dict(self):
        return {
            'review_id': self.review_id,
            'order_line_id': self.order_line_id,
            'seller_id': self.seller_id,
            'listing_id': self.listing_id,
            'customer_id': self.customer_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

