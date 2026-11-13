from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from database.connection import Base


class SellerStatusEvent(Base):
    __tablename__ = 'seller_status_events'

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(String(32), ForeignKey('sellers.seller_id', ondelete='CASCADE'), nullable=False, index=True)
    previous_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    reason = Column(String(255), nullable=True)
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    seller = relationship('Seller', back_populates='status_events')


class ListingStatusEvent(Base):
    __tablename__ = 'listing_status_events'

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(String(48), ForeignKey('product_listings.listing_id', ondelete='CASCADE'), nullable=False, index=True)
    previous_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    reason = Column(String(255), nullable=True)
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    listing = relationship('ProductListing', back_populates='status_events')


class OrderStatusEvent(Base):
    __tablename__ = 'order_status_events'

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(32), ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False, index=True)
    previous_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    reason = Column(String(255), nullable=True)
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    order = relationship('Order', back_populates='status_events')


class FulfillmentEvent(Base):
    __tablename__ = 'fulfillment_events'

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    fulfillment_id = Column(String(48), ForeignKey('fulfillments.fulfillment_id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)  # e.g. LABEL_CREATED, IN_TRANSIT, DELIVERED
    location = Column(String(120), nullable=True)
    notes = Column(String(255), nullable=True)
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    fulfillment = relationship('Fulfillment', back_populates='events')


class PayoutEvent(Base):
    __tablename__ = 'payout_events'

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    payout_id = Column(String(32), ForeignKey('payouts.payout_id', ondelete='CASCADE'), nullable=False, index=True)
    previous_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    note = Column(String(255), nullable=True)
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    payout = relationship('Payout', back_populates='status_events')

