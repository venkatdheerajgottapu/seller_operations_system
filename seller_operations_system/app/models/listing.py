from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.connection import Base

LISTING_STATUSES = ('ACTIVE', 'INACTIVE', 'DELISTED')


class ProductListing(Base):
    __tablename__ = 'product_listings'

    listing_id = Column(String(48), primary_key=True)  # LIST-SELL-000001-000001
    seller_id = Column(String(32), ForeignKey('sellers.seller_id', ondelete='CASCADE'), nullable=False, index=True)
    sku = Column(String(64), nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(String(80), nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    status = Column(Enum(*LISTING_STATUSES, name='listing_status_enum', validate_strings=True, create_constraint=True), default='ACTIVE', nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    seller = relationship('Seller', back_populates='listings')
    order_lines = relationship('OrderLine', back_populates='listing')
    reviews = relationship('CustomerReview', back_populates='listing')
    status_events = relationship('ListingStatusEvent', back_populates='listing', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_listing_seller_status', 'seller_id', 'status'),
        Index('idx_listing_category_price', 'category', 'price'),
    )

    def to_dict(self):
        return {
            'listing_id': self.listing_id,
            'seller_id': self.seller_id,
            'sku': self.sku,
            'title': self.title,
            'category': self.category,
            'price': float(self.price) if self.price is not None else 0.0,
            'stock_quantity': self.stock_quantity,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

