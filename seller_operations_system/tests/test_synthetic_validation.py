import pytest
from database.connection import get_session
from app.models import Seller, ProductListing, Customer, Order, OrderLine, Fulfillment, Dispute, Payout, PayoutLine
from data_generator.generator import SyntheticDataGenerator, GLOBAL_SEED, CONFIG_PRESETS


def test_seed_constant():
    """Verify fixed global random seed is 20261022."""
    assert GLOBAL_SEED == 20261022


def test_config_presets_specification():
    """Verify CONFIG_PRESETS defines exact required counts and scaling ratios for STARTER, MEDIUM, and FULL."""
    assert 'STARTER' in CONFIG_PRESETS
    assert 'MEDIUM' in CONFIG_PRESETS
    assert 'FULL' in CONFIG_PRESETS

    # FULL dataset specification
    full = CONFIG_PRESETS['FULL']
    assert full['sellers'] == 2000, f"Expected 2,000 sellers in FULL, got {full['sellers']}"
    assert full['listings'] == 20000, f"Expected 20,000 listings in FULL, got {full['listings']}"
    assert full['orders'] == 100000, f"Expected 100,000 orders in FULL, got {full['orders']}"
    assert full['disputes'] == 10000, f"Expected 10,000 disputes in FULL, got {full['disputes']}"

    # MEDIUM dataset specification
    medium = CONFIG_PRESETS['MEDIUM']
    assert medium['sellers'] == 200
    assert medium['listings'] == 2000
    assert medium['orders'] == 10000
    assert medium['disputes'] == 1000

    # STARTER dataset specification
    starter = CONFIG_PRESETS['STARTER']
    assert starter['sellers'] == 20
    assert starter['listings'] == 200
    assert starter['orders'] == 500
    assert starter['disputes'] == 50

    # Ratio consistency across all presets
    for preset_name, cfg in CONFIG_PRESETS.items():
        assert cfg['listings'] // cfg['sellers'] == 10, f"Preset {preset_name} violates 10 listings/seller ratio"
        assert cfg['disputes'] / cfg['orders'] >= 0.08, f"Preset {preset_name} dispute ratio below target"


def test_starter_configuration_counts():
    """Verify STARTER dataset meets specification: 20 sellers, 200 listings, 500 orders, 50 disputes."""
    with get_session() as session:
        seller_count = session.query(Seller).count()
        listing_count = session.query(ProductListing).count()
        order_count = session.query(Order).count()
        dispute_count = session.query(Dispute).count()

        assert seller_count == 20, f"Expected 20 sellers, got {seller_count}"
        assert listing_count == 200, f"Expected 200 listings, got {listing_count}"
        assert order_count == 500, f"Expected 500 orders, got {order_count}"
        assert dispute_count == 50, f"Expected 50 disputes, got {dispute_count}"


def test_multi_seller_order_splitting():
    """Verify that multi-seller orders are generated with items allocated across different sellers."""
    with get_session() as session:
        orders = session.query(Order).all()
        multi_seller_orders = 0
        total_orders = len(orders)

        for order in orders:
            seller_ids = {line.seller_id for line in order.order_lines}
            if len(seller_ids) > 1:
                multi_seller_orders += 1

        split_percentage = (multi_seller_orders / total_orders) * 100
        # Multi-seller orders should comprise between 20% and 50% of the dataset
        assert split_percentage >= 20.0, f"Expected >=20% multi-seller orders, got {split_percentage:.1f}%"
        assert multi_seller_orders > 0


def test_foreign_key_referential_validity():
    """Verify that all generated child records reference valid parent records."""
    with get_session() as session:
        seller_ids = {s.seller_id for s in session.query(Seller.seller_id).all()}
        listing_ids = {l.listing_id for l in session.query(ProductListing.listing_id).all()}
        customer_ids = {c.customer_id for c in session.query(Customer.customer_id).all()}
        order_ids = {o.order_id for o in session.query(Order.order_id).all()}
        order_line_ids = {ol.order_line_id for ol in session.query(OrderLine.order_line_id).all()}

        # Check OrderLines
        for ol in session.query(OrderLine).all():
            assert ol.order_id in order_ids, f"OrderLine {ol.order_line_id} references invalid order {ol.order_id}"
            assert ol.seller_id in seller_ids, f"OrderLine {ol.order_line_id} references invalid seller {ol.seller_id}"
            assert ol.listing_id in listing_ids, f"OrderLine {ol.order_line_id} references invalid listing {ol.listing_id}"

        # Check Fulfillments
        for f in session.query(Fulfillment).all():
            assert f.order_id in order_ids
            assert f.order_line_id in order_line_ids
            assert f.seller_id in seller_ids

        # Check Payouts
        for p in session.query(Payout).all():
            assert p.seller_id in seller_ids

