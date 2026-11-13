import pytest
from sqlalchemy import inspect
from database.connection import get_engine, get_session
from app.models import (
    Base, Seller, ProductListing, Customer, Order, OrderLine,
    Fulfillment, CustomerReview, Dispute, CommissionRule, Payout,
    PayoutLine, SellerStatusEvent, ListingStatusEvent, OrderStatusEvent,
    FulfillmentEvent, PayoutEvent, AnomalyRecord
)


def test_table_count_and_registration():
    """Verify all 17 tables are registered and exist in the schema."""
    engine = get_engine()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    
    expected_tables = {
        'sellers', 'product_listings', 'customers', 'orders', 'order_lines',
        'fulfillments', 'customer_reviews', 'disputes', 'commission_rules',
        'payouts', 'payout_lines', 'seller_status_events', 'listing_status_events',
        'order_status_events', 'fulfillment_events', 'payout_events', 'anomalies'
    }
    
    missing = expected_tables - table_names
    assert len(missing) == 0, f"Missing tables in database: {missing}"
    assert len(table_names.intersection(expected_tables)) == 17


def test_primary_keys_across_all_tables():
    """Verify every table has a defined primary key."""
    engine = get_engine()
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        pk = inspector.get_pk_constraint(table_name)
        assert pk is not None, f"Table {table_name} missing primary key constraint"
        assert len(pk['constrained_columns']) > 0, f"Table {table_name} has empty primary key"


def test_foreign_key_definitions():
    """Verify foreign key constraints are properly defined with valid target tables."""
    engine = get_engine()
    inspector = inspect(engine)
    
    fk_expectations = {
        'product_listings': {'sellers'},
        'orders': {'customers'},
        'order_lines': {'orders', 'product_listings', 'sellers'},
        'fulfillments': {'order_lines', 'orders', 'sellers'},
        'customer_reviews': {'order_lines', 'sellers', 'product_listings', 'customers'},
        'disputes': {'orders', 'order_lines', 'sellers', 'customers'},
        'payouts': {'sellers'},
        'payout_lines': {'payouts', 'order_lines', 'disputes'},
        'seller_status_events': {'sellers'},
        'listing_status_events': {'product_listings'},
        'order_status_events': {'orders'},
        'fulfillment_events': {'fulfillments'},
        'payout_events': {'payouts'}
    }
    
    for table, expected_targets in fk_expectations.items():
        fks = inspector.get_foreign_keys(table)
        target_tables = {fk['referred_table'] for fk in fks}
        for target in expected_targets:
            assert target in target_tables, f"Table '{table}' missing foreign key to '{target}'"


def test_indexes_present():
    """Verify performance and lookup indexes exist on key foreign keys and status columns."""
    engine = get_engine()
    inspector = inspect(engine)
    
    for table in ['sellers', 'product_listings', 'orders', 'fulfillments', 'payouts']:
        indexes = inspector.get_indexes(table)
        assert len(indexes) > 0, f"Table {table} has no database indexes"


# ---------------------------------------------------------------------------
# Automated Database Integrity Tests on Isolated Test Database
# ---------------------------------------------------------------------------
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, StatementError


@pytest.fixture
def test_db_session():
    """
    Dedicated in-memory test database with full schema and foreign keys enabled.
    Completely isolated from development and production databases.
    """
    engine = create_engine('sqlite:///:memory:')

    @event.listens_for(engine, 'connect')
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_successful_record_creation(test_db_session):
    """Verify end-to-end successful record creation across all entities."""
    s = test_db_session
    now = datetime.now(timezone.utc)

    # 1. Seller
    seller = Seller(
        seller_id='SELL-TEST-000001',
        name='Alpha Tech',
        email='alpha@test.com',
        phone='1234567890',
        status='ACTIVE'
    )
    s.add(seller)

    # 2. Listing
    listing = ProductListing(
        listing_id='LIST-SELL-TEST-000001-000001',
        seller_id='SELL-TEST-000001',
        sku='SKU-ALPHA-001',
        title='Mechanical Keyboard',
        category='Electronics',
        price=Decimal('89.99'),
        stock_quantity=50,
        status='ACTIVE'
    )
    s.add(listing)

    # 3. Customer
    customer = Customer(
        customer_id='CUST-TEST-000001',
        name='Alice Smith',
        email='alice@example.com',
        phone='555-1234',
        shipping_address='100 Main St',
        city='Springfield',
        state='IL',
        postal_code='62701'
    )
    s.add(customer)

    # 4. Commission Rule
    rule = CommissionRule(
        rule_id='RULE-TEST-000001',
        category='Electronics',
        base_rate=Decimal('0.0800'),
        min_commission=Decimal('0.50'),
        max_commission=Decimal('150.00'),
        effective_from=now,
        is_active=True
    )
    s.add(rule)
    s.commit()

    # 5. Order & OrderLine
    order = Order(
        order_id='ORD-2026-TEST01',
        customer_id='CUST-TEST-000001',
        order_date=now,
        order_status='DELIVERED',
        payment_status='PAID',
        total_gross_amount=Decimal('89.99')
    )
    s.add(order)
    s.commit()

    line = OrderLine(
        order_line_id='ORD-2026-TEST01-01',
        order_id='ORD-2026-TEST01',
        listing_id='LIST-SELL-TEST-000001-000001',
        seller_id='SELL-TEST-000001',
        quantity=1,
        unit_price=Decimal('89.99'),
        line_total=Decimal('89.99'),
        commission_rate=Decimal('0.0800'),
        commission_amount=Decimal('7.20'),
        status='DELIVERED'
    )
    s.add(line)
    s.commit()

    # 6. Fulfillment
    fulfillment = Fulfillment(
        fulfillment_id='FUL-ORD-2026-TEST01-01',
        order_line_id='ORD-2026-TEST01-01',
        order_id='ORD-2026-TEST01',
        seller_id='SELL-TEST-000001',
        tracking_number='TRK-TEST-000001',
        carrier='FEDEX',
        status='DELIVERED',
        shipped_at=now,
        delivered_at=now
    )
    s.add(fulfillment)

    # 7. Customer Review
    review = CustomerReview(
        review_id='REV-TEST-000001',
        order_line_id='ORD-2026-TEST01-01',
        seller_id='SELL-TEST-000001',
        listing_id='LIST-SELL-TEST-000001-000001',
        customer_id='CUST-TEST-000001',
        rating=5,
        comment='Excellent product!'
    )
    s.add(review)

    # 8. Dispute
    dispute = Dispute(
        dispute_id='DSP-TEST-000001',
        order_id='ORD-2026-TEST01',
        order_line_id='ORD-2026-TEST01-01',
        seller_id='SELL-TEST-000001',
        customer_id='CUST-TEST-000001',
        dispute_type='ITEM_NOT_RECEIVED',
        status='OPEN',
        claim_amount=Decimal('89.99'),
        deduction_amount=Decimal('0.00')
    )
    s.add(dispute)

    # 9. Payout & PayoutLine
    payout = Payout(
        payout_id='PAYOUT-TEST-000001',
        seller_id='SELL-TEST-000001',
        batch_reference='BATCH-2026-W01',
        payout_date=now,
        status='SCHEDULED',
        gross_amount=Decimal('89.99'),
        commission_deduction=Decimal('7.20'),
        refund_deduction=Decimal('0.00'),
        dispute_deduction=Decimal('0.00'),
        reserve_hold_amount=Decimal('9.00'),
        adjustments=Decimal('0.00'),
        net_payout_amount=Decimal('73.79'),
        reconciliation_status='RECONCILED'
    )
    s.add(payout)
    s.commit()

    payout_line = PayoutLine(
        payout_line_id='PAYLINE-TEST-000001-01',
        payout_id='PAYOUT-TEST-000001',
        order_line_id='ORD-2026-TEST01-01',
        line_type='SALE',
        amount=Decimal('89.99'),
        description='Sale line item'
    )
    s.add(payout_line)

    # 10. Status Events
    s.add(SellerStatusEvent(seller_id='SELL-TEST-000001', previous_status='NEW', new_status='ACTIVE', reason='Verified'))
    s.add(ListingStatusEvent(listing_id='LIST-SELL-TEST-000001-000001', previous_status='DRAFT', new_status='ACTIVE'))
    s.add(OrderStatusEvent(order_id='ORD-2026-TEST01', previous_status='PLACED', new_status='DELIVERED'))
    s.add(FulfillmentEvent(fulfillment_id='FUL-ORD-2026-TEST01-01', event_type='DELIVERED'))
    s.add(PayoutEvent(payout_id='PAYOUT-TEST-000001', previous_status='CREATED', new_status='SCHEDULED'))

    # 11. Anomaly Record
    s.add(AnomalyRecord(
        scenario_id=1,
        scenario_name='Test Anomaly',
        entity_type='PAYOUT',
        entity_id='PAYOUT-TEST-000001',
        detected_by='DETECTOR_ENGINE',
        is_ground_truth=False,
        severity='LOW',
        description='Test description'
    ))
    s.commit()

    # Assert persistence
    assert s.query(Seller).filter_by(seller_id='SELL-TEST-000001').count() == 1
    assert s.query(ProductListing).filter_by(listing_id='LIST-SELL-TEST-000001-000001').count() == 1
    assert s.query(Customer).filter_by(customer_id='CUST-TEST-000001').count() == 1
    assert s.query(Order).filter_by(order_id='ORD-2026-TEST01').count() == 1
    assert s.query(OrderLine).filter_by(order_line_id='ORD-2026-TEST01-01').count() == 1
    assert s.query(Fulfillment).filter_by(fulfillment_id='FUL-ORD-2026-TEST01-01').count() == 1
    assert s.query(CustomerReview).filter_by(review_id='REV-TEST-000001').count() == 1
    assert s.query(Dispute).filter_by(dispute_id='DSP-TEST-000001').count() == 1
    assert s.query(CommissionRule).filter_by(rule_id='RULE-TEST-000001').count() == 1
    assert s.query(Payout).filter_by(payout_id='PAYOUT-TEST-000001').count() == 1
    assert s.query(PayoutLine).filter_by(payout_line_id='PAYLINE-TEST-000001-01').count() == 1
    assert s.query(AnomalyRecord).count() == 1


def test_invalid_foreign_key_insertion(test_db_session):
    """Verify that foreign key constraints strictly reject non-existent parent records."""
    s = test_db_session
    now = datetime.now(timezone.utc)

    # 1. ProductListing with non-existent seller
    with pytest.raises(IntegrityError):
        s.add(ProductListing(
            listing_id='LIST-INVALID-01',
            seller_id='NON-EXISTENT-SELLER',
            sku='SKU-INV',
            title='Invalid Item',
            category='Apparel',
            price=Decimal('10.00'),
            stock_quantity=1
        ))
        s.commit()
    s.rollback()

    # 2. Order with non-existent customer
    with pytest.raises(IntegrityError):
        s.add(Order(
            order_id='ORD-INVALID-01',
            customer_id='NON-EXISTENT-CUST',
            order_date=now,
            total_gross_amount=Decimal('100.00')
        ))
        s.commit()
    s.rollback()

    # 3. Payout with non-existent seller
    with pytest.raises(IntegrityError):
        s.add(Payout(
            payout_id='PAYOUT-INVALID-01',
            seller_id='NON-EXISTENT-SELLER',
            batch_reference='BATCH-INV',
            payout_date=now,
            gross_amount=Decimal('100.00'),
            net_payout_amount=Decimal('80.00')
        ))
        s.commit()
    s.rollback()

    # 4. PayoutLine with non-existent payout
    with pytest.raises(IntegrityError):
        s.add(PayoutLine(
            payout_line_id='PAYLINE-INVALID-01',
            payout_id='NON-EXISTENT-PAYOUT',
            line_type='SALE',
            amount=Decimal('100.00')
        ))
        s.commit()
    s.rollback()


def test_duplicate_primary_keys(test_db_session):
    """Verify that inserting duplicate primary keys raises an IntegrityError."""
    s = test_db_session
    s.add(Seller(seller_id='SELL-DUP-01', name='First Seller', email='first@test.com'))
    s.commit()

    with pytest.raises(IntegrityError):
        s.add(Seller(seller_id='SELL-DUP-01', name='Second Seller', email='second@test.com'))
        s.commit()
    s.rollback()


def test_duplicate_unique_values(test_db_session):
    """Verify unique constraints on emails, tracking numbers, and 1:1 foreign keys."""
    s = test_db_session
    now = datetime.now(timezone.utc)

    # 1. Duplicate Seller Email
    s.add(Seller(seller_id='SELL-U1', name='Seller 1', email='unique@test.com'))
    s.commit()

    with pytest.raises(IntegrityError):
        s.add(Seller(seller_id='SELL-U2', name='Seller 2', email='unique@test.com'))
        s.commit()
    s.rollback()

    # 2. Duplicate Customer Email
    s.add(Customer(
        customer_id='CUST-U1', name='Cust 1', email='cust@test.com',
        shipping_address='Addr 1', city='City', state='ST', postal_code='12345'
    ))
    s.commit()

    with pytest.raises(IntegrityError):
        s.add(Customer(
            customer_id='CUST-U2', name='Cust 2', email='cust@test.com',
            shipping_address='Addr 2', city='City', state='ST', postal_code='12345'
        ))
        s.commit()
    s.rollback()

    # Setup base entities for tracking number and 1:1 test
    listing = ProductListing(
        listing_id='LIST-U1', seller_id='SELL-U1', sku='SKU-U1',
        title='Title', category='Books', price=Decimal('15.00')
    )
    s.add(listing)
    order = Order(order_id='ORD-U1', customer_id='CUST-U1', order_date=now, total_gross_amount=Decimal('30.00'))
    s.add(order)
    line1 = OrderLine(
        order_line_id='OL-U1-01', order_id='ORD-U1', listing_id='LIST-U1', seller_id='SELL-U1',
        quantity=1, unit_price=Decimal('15.00'), line_total=Decimal('15.00')
    )
    line2 = OrderLine(
        order_line_id='OL-U1-02', order_id='ORD-U1', listing_id='LIST-U1', seller_id='SELL-U1',
        quantity=1, unit_price=Decimal('15.00'), line_total=Decimal('15.00')
    )
    s.add_all([line1, line2])
    s.commit()

    # 3. Duplicate Fulfillment Tracking Number
    s.add(Fulfillment(
        fulfillment_id='FUL-U1', order_line_id='OL-U1-01', order_id='ORD-U1',
        seller_id='SELL-U1', tracking_number='TRK-UNIQUE-123', carrier='UPS'
    ))
    s.commit()

    with pytest.raises(IntegrityError):
        s.add(Fulfillment(
            fulfillment_id='FUL-U2', order_line_id='OL-U1-02', order_id='ORD-U1',
            seller_id='SELL-U1', tracking_number='TRK-UNIQUE-123', carrier='UPS'
        ))
        s.commit()
    s.rollback()

    # 4. Duplicate Fulfillment order_line_id (1-to-1 violation)
    with pytest.raises(IntegrityError):
        s.add(Fulfillment(
            fulfillment_id='FUL-U3', order_line_id='OL-U1-01', order_id='ORD-U1',
            seller_id='SELL-U1', tracking_number='TRK-DIFF-999', carrier='UPS'
        ))
        s.commit()
    s.rollback()


def test_missing_required_values(test_db_session):
    """Verify that columns marked nullable=False strictly reject null values."""
    s = test_db_session
    now = datetime.now(timezone.utc)

    # 1. Seller missing name
    with pytest.raises(IntegrityError):
        s.add(Seller(seller_id='SELL-NULL-1', name=None, email='null_name@test.com'))
        s.commit()
    s.rollback()

    # 2. ProductListing missing price
    s.add(Seller(seller_id='SELL-REQ', name='Req Seller', email='req@test.com'))
    s.commit()

    with pytest.raises(IntegrityError):
        s.add(ProductListing(
            listing_id='LIST-NULL-PRICE', seller_id='SELL-REQ', sku='SKU-P',
            title='No Price', category='Tech', price=None
        ))
        s.commit()
    s.rollback()

    # 3. Order missing total_gross_amount
    s.add(Customer(
        customer_id='CUST-REQ', name='Req Cust', email='req_c@test.com',
        shipping_address='Addr', city='C', state='S', postal_code='12345'
    ))
    s.commit()

    with pytest.raises(IntegrityError):
        s.add(Order(order_id='ORD-NULL-AMT', customer_id='CUST-REQ', order_date=now, total_gross_amount=None))
        s.commit()
    s.rollback()


def test_invalid_enum_constraints(test_db_session):
    """Verify that invalid enum strings are strictly rejected across models."""
    s = test_db_session
    now = datetime.now(timezone.utc)

    # Base valid seller
    s.add(Seller(seller_id='SELL-ENUM', name='Enum Seller', email='enum@test.com', status='ACTIVE'))
    s.commit()

    # 1. Invalid Seller status
    with pytest.raises((StatementError, LookupError, IntegrityError)):
        s.add(Seller(seller_id='SELL-BAD-ENUM', name='Bad', email='bad@test.com', status='NOT_A_VALID_STATUS'))
        s.commit()
    s.rollback()

    # 2. Invalid Listing status
    with pytest.raises((StatementError, LookupError, IntegrityError)):
        s.add(ProductListing(
            listing_id='LIST-BAD-ENUM', seller_id='SELL-ENUM', sku='SKU-E',
            title='Bad Status', category='Tools', price=Decimal('10.00'), status='FLYING'
        ))
        s.commit()
    s.rollback()

    # 3. Invalid Payout status
    with pytest.raises((StatementError, LookupError, IntegrityError)):
        s.add(Payout(
            payout_id='PAYOUT-BAD-ENUM', seller_id='SELL-ENUM', batch_reference='B1',
            payout_date=now, status='INVALID_PAYOUT_STATUS',
            gross_amount=Decimal('100.00'), net_payout_amount=Decimal('80.00')
        ))
        s.commit()
    s.rollback()

    # 4. Invalid PayoutLine line_type
    payout = Payout(
        payout_id='PAYOUT-VALID', seller_id='SELL-ENUM', batch_reference='B1',
        payout_date=now, status='SCHEDULED',
        gross_amount=Decimal('100.00'), net_payout_amount=Decimal('80.00')
    )
    s.add(payout)
    s.commit()

    with pytest.raises((StatementError, LookupError, IntegrityError)):
        s.add(PayoutLine(
            payout_line_id='PL-BAD-ENUM', payout_id='PAYOUT-VALID',
            line_type='ILLEGAL_TYPE', amount=Decimal('50.00')
        ))
        s.commit()
    s.rollback()


def test_relationship_consistency(test_db_session):
    """Verify multi-seller order relationship navigation and bidirectional consistency."""
    s = test_db_session
    now = datetime.now(timezone.utc)

    # Multi-seller scenario: 2 sellers, 1 customer, 1 order with 2 lines
    seller_a = Seller(seller_id='SELL-MA', name='Seller Alpha', email='alpha@multi.com')
    seller_b = Seller(seller_id='SELL-MB', name='Seller Beta', email='beta@multi.com')
    cust = Customer(
        customer_id='CUST-M1', name='Multi Buyer', email='buyer@multi.com',
        shipping_address='100 Multi Way', city='Dallas', state='TX', postal_code='75001'
    )
    s.add_all([seller_a, seller_b, cust])
    s.commit()

    list_a = ProductListing(listing_id='LIST-MA', seller_id='SELL-MA', sku='SKU-A', title='Item A', category='Art', price=Decimal('40.00'))
    list_b = ProductListing(listing_id='LIST-MB', seller_id='SELL-MB', sku='SKU-B', title='Item B', category='Books', price=Decimal('60.00'))
    s.add_all([list_a, list_b])
    s.commit()

    order = Order(order_id='ORD-M1', customer_id='CUST-M1', order_date=now, total_gross_amount=Decimal('100.00'))
    s.add(order)
    s.commit()

    line_a = OrderLine(
        order_line_id='OL-M1-01', order_id='ORD-M1', listing_id='LIST-MA', seller_id='SELL-MA',
        quantity=1, unit_price=Decimal('40.00'), line_total=Decimal('40.00')
    )
    line_b = OrderLine(
        order_line_id='OL-M1-02', order_id='ORD-M1', listing_id='LIST-MB', seller_id='SELL-MB',
        quantity=1, unit_price=Decimal('60.00'), line_total=Decimal('60.00')
    )
    s.add_all([line_a, line_b])
    s.commit()

    ful_a = Fulfillment(
        fulfillment_id='FUL-MA-01', order_line_id='OL-M1-01', order_id='ORD-M1',
        seller_id='SELL-MA', tracking_number='TRK-A-123', carrier='FEDEX'
    )
    ful_b = Fulfillment(
        fulfillment_id='FUL-MB-02', order_line_id='OL-M1-02', order_id='ORD-M1',
        seller_id='SELL-MB', tracking_number='TRK-B-456', carrier='UPS'
    )
    s.add_all([ful_a, ful_b])
    s.commit()

    # 1. Order to lines
    reloaded_order = s.query(Order).filter_by(order_id='ORD-M1').first()
    assert len(reloaded_order.order_lines) == 2
    assert reloaded_order.customer.customer_id == 'CUST-M1'

    # 2. Customer to orders
    reloaded_cust = s.query(Customer).filter_by(customer_id='CUST-M1').first()
    assert len(reloaded_cust.orders) == 1
    assert reloaded_cust.orders[0].order_id == 'ORD-M1'

    # 3. Seller to order lines
    reloaded_sa = s.query(Seller).filter_by(seller_id='SELL-MA').first()
    reloaded_sb = s.query(Seller).filter_by(seller_id='SELL-MB').first()
    assert len(reloaded_sa.order_lines) == 1
    assert reloaded_sa.order_lines[0].order_line_id == 'OL-M1-01'
    assert len(reloaded_sb.order_lines) == 1
    assert reloaded_sb.order_lines[0].order_line_id == 'OL-M1-02'

    # 4. OrderLine to Fulfillment (1:1)
    reloaded_line_a = s.query(OrderLine).filter_by(order_line_id='OL-M1-01').first()
    assert reloaded_line_a.fulfillment is not None
    assert reloaded_line_a.fulfillment.fulfillment_id == 'FUL-MA-01'
    assert reloaded_line_a.fulfillment.order_line.order_line_id == 'OL-M1-01'


def test_record_deletion_and_cascade_behavior(test_db_session):
    """Verify cascade deletions and restriction rules."""
    s = test_db_session
    now = datetime.now(timezone.utc)

    # 1. Test Order deletion cascades to order lines and fulfillment
    seller = Seller(seller_id='SELL-CAS-1', name='Cascade Seller', email='cas@test.com')
    cust = Customer(
        customer_id='CUST-CAS-1', name='Cas Cust', email='cas_c@test.com',
        shipping_address='Addr', city='C', state='S', postal_code='12345'
    )
    s.add_all([seller, cust])
    s.commit()

    listing = ProductListing(listing_id='LIST-CAS-1', seller_id='SELL-CAS-1', sku='SKU-C', title='Cas Item', category='Home', price=Decimal('50.00'))
    s.add(listing)
    s.commit()

    order = Order(order_id='ORD-CAS-1', customer_id='CUST-CAS-1', order_date=now, total_gross_amount=Decimal('50.00'))
    s.add(order)
    s.commit()

    line = OrderLine(
        order_line_id='OL-CAS-1', order_id='ORD-CAS-1', listing_id='LIST-CAS-1', seller_id='SELL-CAS-1',
        quantity=1, unit_price=Decimal('50.00'), line_total=Decimal('50.00')
    )
    s.add(line)
    s.commit()

    ful = Fulfillment(
        fulfillment_id='FUL-CAS-1', order_line_id='OL-CAS-1', order_id='ORD-CAS-1',
        seller_id='SELL-CAS-1', tracking_number='TRK-CAS-1', carrier='USPS'
    )
    s.add(ful)
    s.commit()

    # Cascade delete order
    s.delete(order)
    s.commit()

    assert s.query(Order).filter_by(order_id='ORD-CAS-1').count() == 0
    assert s.query(OrderLine).filter_by(order_line_id='OL-CAS-1').count() == 0
    assert s.query(Fulfillment).filter_by(fulfillment_id='FUL-CAS-1').count() == 0

    # 2. Test Deleting Seller with active order lines is RESTRICTED
    seller2 = Seller(seller_id='SELL-RESTRICT', name='Restricted Seller', email='res@test.com')
    s.add(seller2)
    s.commit()

    listing2 = ProductListing(listing_id='LIST-RES-2', seller_id='SELL-RESTRICT', sku='SKU-R', title='R', category='H', price=Decimal('10.00'))
    order2 = Order(order_id='ORD-RES-2', customer_id='CUST-CAS-1', order_date=now, total_gross_amount=Decimal('10.00'))
    s.add_all([listing2, order2])
    s.commit()

    line2 = OrderLine(
        order_line_id='OL-RES-2', order_id='ORD-RES-2', listing_id='LIST-RES-2', seller_id='SELL-RESTRICT',
        quantity=1, unit_price=Decimal('10.00'), line_total=Decimal('10.00')
    )
    s.add(line2)
    s.commit()

    with pytest.raises(IntegrityError):
        s.delete(seller2)
        s.commit()
    s.rollback()


def test_database_transaction_rollback(test_db_session):
    """Verify transaction rollback prevents partial writes."""
    s = test_db_session
    s.add(Customer(
        customer_id='CUST-RB-1', name='Committed Cust', email='committed@test.com',
        shipping_address='Addr', city='C', state='S', postal_code='12345'
    ))
    s.commit()

    # Start dirty transaction and rollback
    s.add(Seller(seller_id='SELL-DIRTY', name='Uncommitted Seller', email='dirty@test.com'))
    s.rollback()

    assert s.query(Customer).filter_by(customer_id='CUST-RB-1').count() == 1
    assert s.query(Seller).filter_by(seller_id='SELL-DIRTY').count() == 0


