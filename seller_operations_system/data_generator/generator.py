import random
from datetime import datetime, timedelta
from decimal import Decimal
from faker import Faker
from typing import Dict, Any, List

from database.connection import get_session
from app.models import (
    Seller, ProductListing, Customer, Order, OrderLine,
    Fulfillment, CustomerReview, Dispute, CommissionRule,
    Payout, PayoutLine, SellerStatusEvent, ListingStatusEvent,
    OrderStatusEvent, FulfillmentEvent, PayoutEvent, AnomalyRecord
)

GLOBAL_SEED = 20261022

CONFIG_PRESETS = {
    'STARTER': {'sellers': 20, 'listings': 200, 'orders': 500, 'disputes': 50},
    'MEDIUM': {'sellers': 200, 'listings': 2000, 'orders': 10000, 'disputes': 1000},
    'FULL': {'sellers': 2000, 'listings': 20000, 'orders': 100000, 'disputes': 10000}
}

CATEGORIES = [
    ('Electronics', Decimal('0.0800'), Decimal('1.00'), Decimal('150.00')),
    ('Apparel & Fashion', Decimal('0.1500'), Decimal('0.50'), Decimal('80.00')),
    ('Home & Kitchen', Decimal('0.1200'), Decimal('0.75'), Decimal('100.00')),
    ('Books & Media', Decimal('0.1000'), Decimal('0.50'), Decimal('50.00')),
    ('Beauty & Health', Decimal('0.1400'), Decimal('0.50'), Decimal('90.00')),
    ('Sports & Outdoors', Decimal('0.1100'), Decimal('0.75'), Decimal('120.00'))
]

CARRIERS = ['FedEx', 'UPS', 'DHL Express', 'BlueDart', 'USPS']


class SyntheticDataGenerator:
    """
    Deterministic synthetic data generator for the Seller Operations & Payout Intelligence System.
    Uses seed 20261022 across all runs.
    """

    def __init__(self, seed: int = GLOBAL_SEED):
        self.seed = seed
        random.seed(self.seed)
        self.fake = Faker()
        Faker.seed(self.seed)
        
        self.sellers: List[Seller] = []
        self.listings: List[ProductListing] = []
        self.customers: List[Customer] = []
        self.commission_rules: List[CommissionRule] = []
        self.orders: List[Order] = []
        self.order_lines: List[OrderLine] = []
        self.fulfillments: List[Fulfillment] = []
        self.reviews: List[CustomerReview] = []
        self.disputes: List[Dispute] = []
        self.payouts: List[Payout] = []
        self.payout_lines: List[PayoutLine] = []
        
        self.seller_events: List[SellerStatusEvent] = []
        self.listing_events: List[ListingStatusEvent] = []
        self.order_events: List[OrderStatusEvent] = []
        self.fulfillment_events: List[FulfillmentEvent] = []
        self.payout_events: List[PayoutEvent] = []
        self.ground_truth_anomalies: List[AnomalyRecord] = []

    def generate(self, preset: str = 'STARTER') -> Dict[str, Any]:
        """Generate entire synthetic dataset in strict dependency order."""
        config = CONFIG_PRESETS.get(preset.upper(), CONFIG_PRESETS['STARTER'])
        print(f"Generating synthetic dataset using preset '{preset}' (Seed: {self.seed})...")

        # 1. Commission Rules
        self._generate_commission_rules()
        
        # 2. Sellers
        self._generate_sellers(config['sellers'])
        
        # 3. Product Listings
        self._generate_listings(config['listings'])
        
        # 4. Customers
        self._generate_customers(max(config['sellers'] * 4, 100))
        
        # 5 & 6. Orders and Multi-Seller Order Lines
        self._generate_orders_and_lines(config['orders'])
        
        # 7 & 8. Fulfillments & Delivery Events
        self._generate_fulfillments_and_events()
        
        # 9. Customer Reviews
        self._generate_reviews()
        
        # 10. Disputes
        self._generate_disputes(config['disputes'])
        
        # 11 & 12. Payouts and Payout Lines
        self._generate_payouts_and_lines()
        
        # Inject the 5 Labelled Anomaly Scenarios
        self._inject_anomalies()

        return self.get_summary()

    def _generate_commission_rules(self):
        start_date = datetime(2026, 1, 1, 0, 0, 0)
        for i, (cat, rate, min_comm, max_comm) in enumerate(CATEGORIES, start=1):
            rule = CommissionRule(
                rule_id=f"RULE-2026-{i:06d}",
                category=cat,
                base_rate=rate,
                min_commission=min_comm,
                max_commission=max_comm,
                effective_from=start_date,
                effective_to=None,
                is_active=True
            )
            self.commission_rules.append(rule)

    def _generate_sellers(self, count: int):
        base_date = datetime(2026, 1, 15)
        for i in range(1, count + 1):
            seller_id = f"SELL-{i:06d}"
            created_at = base_date + timedelta(days=random.randint(0, 180))
            
            # Most sellers active; a few under review or suspended initially
            status = 'ACTIVE'
            if i % 15 == 0:
                status = 'SUSPENDED'
            elif i % 10 == 0:
                status = 'UNDER_REVIEW'

            seller = Seller(
                seller_id=seller_id,
                name=self.fake.company(),
                email=f"contact@{self.fake.domain_name()}",
                phone=self.fake.phone_number()[:30],
                status=status,
                rating=Decimal(str(round(random.uniform(4.0, 5.0), 2))),
                on_time_shipment_rate=Decimal(str(round(random.uniform(92.0, 99.5), 2))),
                fulfillment_rate=Decimal(str(round(random.uniform(95.0, 100.0), 2))),
                cancellation_rate=Decimal(str(round(random.uniform(0.1, 2.5), 2))),
                return_rate=Decimal(str(round(random.uniform(0.5, 4.0), 2))),
                dispute_rate=Decimal(str(round(random.uniform(0.1, 1.5), 2))),
                reserve_rate=Decimal('0.1000'),  # 10% rolling reserve hold
                created_at=created_at,
                updated_at=created_at
            )
            self.sellers.append(seller)
            
            # Event history
            self.seller_events.append(SellerStatusEvent(
                seller_id=seller_id,
                previous_status='NEW_ONBOARDING',
                new_status=status,
                reason='Initial seller compliance verification',
                event_timestamp=created_at
            ))

    def _generate_listings(self, count: int):
        for i in range(1, count + 1):
            seller = random.choice(self.sellers)
            cat_tuple = random.choice(CATEGORIES)
            category = cat_tuple[0]
            
            listing_id = f"LIST-{seller.seller_id}-{i:06d}"
            price = Decimal(str(round(random.uniform(15.00, 350.00), 2)))
            stock = random.randint(10, 500)
            created_at = seller.created_at + timedelta(days=random.randint(1, 30))
            
            listing = ProductListing(
                listing_id=listing_id,
                seller_id=seller.seller_id,
                sku=f"SKU-{self.fake.lexify(text='????').upper()}-{i:04d}",
                title=f"{self.fake.catch_phrase()} ({category})",
                category=category,
                price=price,
                stock_quantity=stock,
                status='ACTIVE',
                created_at=created_at,
                updated_at=created_at
            )
            self.listings.append(listing)
            
            self.listing_events.append(ListingStatusEvent(
                listing_id=listing_id,
                previous_status='DRAFT',
                new_status='ACTIVE',
                reason='Listing published by seller',
                event_timestamp=created_at
            ))

    def _generate_customers(self, count: int):
        base_date = datetime(2026, 2, 1)
        for i in range(1, count + 1):
            cust_id = f"CUST-{i:06d}"
            customer = Customer(
                customer_id=cust_id,
                name=self.fake.name(),
                email=f"user_{i}_{self.fake.user_name()}@{self.fake.free_email_domain()}",
                phone=self.fake.phone_number()[:30],
                shipping_address=self.fake.street_address(),
                city=self.fake.city(),
                state=self.fake.state(),
                postal_code=self.fake.postcode(),
                created_at=base_date + timedelta(days=random.randint(0, 150))
            )
            self.customers.append(customer)

    def _generate_orders_and_lines(self, count: int):
        base_date = datetime(2026, 3, 1)
        rule_map = {r.category: r.base_rate for r in self.commission_rules}

        for i in range(1, count + 1):
            order_id = f"ORD-2026-{i:06d}"
            customer = random.choice(self.customers)
            order_date = base_date + timedelta(days=random.randint(0, 180), hours=random.randint(0, 23))
            
            # Determine line count: 1 to 4 lines per order (creating multi-seller orders)
            line_count = random.choices([1, 2, 3, 4], weights=[40, 35, 15, 10])[0]
            selected_listings = random.sample(self.listings, min(line_count, len(self.listings)))
            
            order_lines_for_this = []
            gross_sum = Decimal('0.00')

            # Status distribution: 80% DELIVERED, 10% SHIPPED, 5% PROCESSING, 3% CANCELLED, 2% RETURNED
            order_status = random.choices(
                ['DELIVERED', 'SHIPPED', 'PROCESSING', 'CANCELLED', 'RETURNED'],
                weights=[80, 10, 5, 3, 2]
            )[0]

            for line_idx, listing in enumerate(selected_listings, start=1):
                order_line_id = f"{order_id}-{line_idx:02d}"
                qty = random.randint(1, 3)
                unit_price = listing.price
                line_total = unit_price * qty
                gross_sum += line_total
                
                comm_rate = rule_map.get(listing.category, Decimal('0.1000'))
                comm_amount = (line_total * comm_rate).quantize(Decimal('0.01'))
                
                line_status = order_status
                if order_status == 'DELIVERED':
                    line_status = 'DELIVERED'
                
                line = OrderLine(
                    order_line_id=order_line_id,
                    order_id=order_id,
                    listing_id=listing.listing_id,
                    seller_id=listing.seller_id,
                    quantity=qty,
                    unit_price=unit_price,
                    line_total=line_total,
                    commission_rate=comm_rate,
                    commission_amount=comm_amount,
                    status=line_status,
                    created_at=order_date
                )
                self.order_lines.append(line)
                order_lines_for_this.append(line)

            shipping_fee = Decimal('5.00') if gross_sum < Decimal('100.00') else Decimal('0.00')
            tax_amount = (gross_sum * Decimal('0.05')).quantize(Decimal('0.01'))

            order = Order(
                order_id=order_id,
                customer_id=customer.customer_id,
                order_date=order_date,
                order_status=order_status,
                payment_status='PAID' if order_status != 'CANCELLED' else 'REFUNDED',
                total_gross_amount=gross_sum + shipping_fee + tax_amount,
                shipping_fee=shipping_fee,
                tax_amount=tax_amount,
                created_at=order_date,
                updated_at=order_date + timedelta(days=2)
            )
            self.orders.append(order)

            # Order Status Event
            self.order_events.append(OrderStatusEvent(
                order_id=order_id,
                previous_status='PLACED',
                new_status=order_status,
                reason='Order processed through automated marketplace checkout',
                event_timestamp=order_date
            ))

    def _generate_fulfillments_and_events(self):
        for line in self.order_lines:
            if line.status in ('CANCELLED', 'PENDING'):
                continue
                
            fulfillment_id = f"FUL-{line.order_line_id}"
            carrier = random.choice(CARRIERS)
            tracking_num = f"TRK-{carrier[:3].upper()}-{line.order_id[-6:]}-{line.order_line_id[-2:]}-{random.randint(1000, 9999)}"
            
            shipped_at = line.created_at + timedelta(days=random.randint(1, 3), hours=random.randint(1, 12))
            estimated_delivery = shipped_at + timedelta(days=random.randint(3, 5))
            
            # 8% deliberate delayed shipments
            is_delayed = (random.random() < 0.08)
            delay_days = random.randint(2, 6) if is_delayed else 0
            
            delivered_at = None
            status = 'IN_TRANSIT'
            
            if line.status == 'DELIVERED':
                delivered_at = estimated_delivery + timedelta(days=delay_days)
                status = 'DELIVERED'
            elif line.status == 'RETURNED':
                delivered_at = estimated_delivery
                status = 'RETURNED'
                
            fulfillment = Fulfillment(
                fulfillment_id=fulfillment_id,
                order_line_id=line.order_line_id,
                order_id=line.order_id,
                seller_id=line.seller_id,
                tracking_number=tracking_num,
                carrier=carrier,
                status=status,
                shipped_at=shipped_at,
                estimated_delivery=estimated_delivery,
                delivered_at=delivered_at,
                is_delayed=is_delayed,
                delay_days=delay_days,
                created_at=shipped_at,
                updated_at=delivered_at or shipped_at
            )
            self.fulfillments.append(fulfillment)

            # Fulfillment Events
            self.fulfillment_events.append(FulfillmentEvent(
                fulfillment_id=fulfillment_id,
                event_type='LABEL_CREATED',
                location=f"Seller Warehouse ({line.seller_id})",
                notes=f"Carrier {carrier} shipping label generated",
                event_timestamp=shipped_at - timedelta(hours=2)
            ))
            self.fulfillment_events.append(FulfillmentEvent(
                fulfillment_id=fulfillment_id,
                event_type='CARRIER_PICKUP',
                location=f"Origin Hub",
                notes=f"Dispatched via {carrier}",
                event_timestamp=shipped_at
            ))
            if delivered_at:
                self.fulfillment_events.append(FulfillmentEvent(
                    fulfillment_id=fulfillment_id,
                    event_type='DELIVERED',
                    location=f"Destination Delivery Point",
                    notes="Delivered and signature captured",
                    event_timestamp=delivered_at
                ))

    def _generate_reviews(self):
        delivered_lines = [l for l in self.order_lines if l.status == 'DELIVERED']
        # Sample reviews for ~40% of delivered lines
        sample_count = int(len(delivered_lines) * 0.40)
        review_lines = random.sample(delivered_lines, min(sample_count, len(delivered_lines)))

        for i, line in enumerate(review_lines, start=1):
            review_id = f"REV-2026-{i:06d}"
            order = next(o for o in self.orders if o.order_id == line.order_id)
            rating = random.choices([5, 4, 3, 2, 1], weights=[60, 20, 10, 5, 5])[0]
            
            review = CustomerReview(
                review_id=review_id,
                order_line_id=line.order_line_id,
                seller_id=line.seller_id,
                listing_id=line.listing_id,
                customer_id=order.customer_id,
                rating=rating,
                comment=self.fake.sentence() if rating >= 3 else f"Disappointed: {self.fake.sentence()}",
                created_at=line.created_at + timedelta(days=random.randint(6, 15))
            )
            self.reviews.append(review)

    def _generate_disputes(self, target_disputes: int):
        eligible_lines = [l for l in self.order_lines if l.status in ('DELIVERED', 'SHIPPED', 'RETURNED')]
        chosen_lines = random.sample(eligible_lines, min(target_disputes, len(eligible_lines)))

        for i, line in enumerate(chosen_lines, start=1):
            dispute_id = f"DSP-2026-{i:06d}"
            order = next(o for o in self.orders if o.order_id == line.order_id)
            dtype = random.choice([
                'ITEM_NOT_RECEIVED', 'DAMAGED_ITEM', 'WRONG_ITEM',
                'UNAUTHORIZED_CHARGE', 'DEFECTIVE_PRODUCT'
            ])
            # Status distribution: 40% RESOLVED_CUSTOMER_FAVOR, 30% RESOLVED_SELLER_FAVOR, 20% OPEN, 10% UNDER_INVESTIGATION
            status = random.choices(
                ['RESOLVED_CUSTOMER_FAVOR', 'RESOLVED_SELLER_FAVOR', 'OPEN', 'UNDER_INVESTIGATION'],
                weights=[40, 30, 20, 10]
            )[0]

            claim_amt = line.line_total
            deduction_amt = claim_amt if status == 'RESOLVED_CUSTOMER_FAVOR' else Decimal('0.00')
            resolution_dt = line.created_at + timedelta(days=random.randint(10, 25)) if 'RESOLVED' in status else None

            dispute = Dispute(
                dispute_id=dispute_id,
                order_id=order.order_id,
                order_line_id=line.order_line_id,
                seller_id=line.seller_id,
                customer_id=order.customer_id,
                dispute_type=dtype,
                status=status,
                claim_amount=claim_amt,
                deduction_amount=deduction_amt,
                resolution_date=resolution_dt,
                created_at=line.created_at + timedelta(days=random.randint(4, 10)),
                updated_at=resolution_dt or line.created_at
            )
            self.disputes.append(dispute)

    def _generate_payouts_and_lines(self):
        """
        Group delivered, eligible order lines by seller and settlement period into payout batches.
        Applies financial formula:
        Net payout = Gross sales - Commission - Refunds - Dispute deductions - Reserve holds + Eligible adjustments
        """
        delivered_lines = [l for l in self.order_lines if l.status == 'DELIVERED']
        lines_by_seller: Dict[str, List[OrderLine]] = {}
        for l in delivered_lines:
            lines_by_seller.setdefault(l.seller_id, []).append(l)

        payout_counter = 1
        for seller_id, lines in lines_by_seller.items():
            seller = next(s for s in self.sellers if s.seller_id == seller_id)
            
            # Chunk lines into batches of 10-25 lines per settlement
            chunk_size = 15
            for chunk_idx in range(0, len(lines), chunk_size):
                chunk = lines[chunk_idx:chunk_idx + chunk_size]
                payout_id = f"PAYOUT-2026-{payout_counter:06d}"
                batch_ref = f"BATCH-SETTLE-2026-W{(payout_counter % 52) + 1:02d}"
                
                latest_date = max(l.created_at for l in chunk)
                payout_date = latest_date + timedelta(days=14)

                gross = sum(l.line_total for l in chunk)
                commission = sum(l.commission_amount for l in chunk)
                reserve_rate = seller.reserve_rate or Decimal('0.1000')
                reserve_hold = (gross * reserve_rate).quantize(Decimal('0.01'))
                refunds = Decimal('0.00')
                dispute_deduction = Decimal('0.00')
                adjustments = Decimal('0.00')

                # Check if any chunk line had a resolved dispute
                chunk_line_ids = {l.order_line_id for l in chunk}
                chunk_disputes = [d for d in self.disputes if d.order_line_id in chunk_line_ids and d.status == 'RESOLVED_CUSTOMER_FAVOR']
                for d in chunk_disputes:
                    dispute_deduction += d.deduction_amount

                # Calculate Net Payout using the strict formula:
                net_payout = gross - commission - refunds - dispute_deduction - reserve_hold + adjustments

                payout = Payout(
                    payout_id=payout_id,
                    seller_id=seller_id,
                    batch_reference=batch_ref,
                    payout_date=payout_date,
                    status='PAID' if payout_date < datetime.utcnow() else 'SCHEDULED',
                    gross_amount=gross,
                    commission_deduction=commission,
                    refund_deduction=refunds,
                    dispute_deduction=dispute_deduction,
                    reserve_hold_amount=reserve_hold,
                    adjustments=adjustments,
                    net_payout_amount=net_payout,
                    reconciliation_status='RECONCILED',
                    created_at=payout_date - timedelta(days=3),
                    updated_at=payout_date
                )
                self.payouts.append(payout)

                # Generate Payout Lines itemizing the settlement
                line_idx = 1
                for l in chunk:
                    # Positive Sale line
                    self.payout_lines.append(PayoutLine(
                        payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                        payout_id=payout_id,
                        order_line_id=l.order_line_id,
                        line_type='SALE',
                        amount=l.line_total,
                        description=f"Gross sale credit for line {l.order_line_id}"
                    ))
                    line_idx += 1
                    
                    # Negative Commission line
                    self.payout_lines.append(PayoutLine(
                        payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                        payout_id=payout_id,
                        order_line_id=l.order_line_id,
                        line_type='COMMISSION',
                        amount=-l.commission_amount,
                        description=f"Marketplace commission fee on line {l.order_line_id}"
                    ))
                    line_idx += 1

                # Reserve hold line
                self.payout_lines.append(PayoutLine(
                    payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                    payout_id=payout_id,
                    line_type='RESERVE_HOLD',
                    amount=-reserve_hold,
                    description=f"Rolling reserve hold ({(reserve_rate * 100):.1f}%)"
                ))
                line_idx += 1

                # Dispute deductions if any
                for d in chunk_disputes:
                    self.payout_lines.append(PayoutLine(
                        payout_line_id=f"PAYLINE-{payout_id[-6:]}-{line_idx:03d}",
                        payout_id=payout_id,
                        order_line_id=d.order_line_id,
                        dispute_id=d.dispute_id,
                        line_type='DISPUTE',
                        amount=-d.deduction_amount,
                        description=f"Chargeback debit for dispute {d.dispute_id}"
                    ))
                    line_idx += 1

                # Payout Event
                self.payout_events.append(PayoutEvent(
                    payout_id=payout_id,
                    previous_status='SCHEDULED',
                    new_status=payout.status,
                    note=f"Disbursement batch processed for seller {seller_id}",
                    event_timestamp=payout_date
                ))
                payout_counter += 1

    def _inject_anomalies(self):
        """
        Inject the 5 deliberate anomaly scenarios with full ground-truth labels.
        These are stored with detected_by='GROUND_TRUTH' and is_ground_truth=True.
        """
        # Scenario 1: Payout before delivery or reserve release
        # Target: Take 2 paid payouts and inject an in-transit/shipped line into each
        undelivered_lines = [l for l in self.order_lines if l.status in ('PROCESSING', 'SHIPPED')][:2]
        paid_payouts = [p for p in self.payouts if p.status == 'PAID']
        for idx, line in enumerate(undelivered_lines):
            if paid_payouts:
                p = paid_payouts[idx % len(paid_payouts)]
                # Add a premature payout line into the paid payout
                premature_line_id = f"PAYLINE-{p.payout_id[-6:]}-PRE{idx+1:02d}"
                premature_payout_line = PayoutLine(
                    payout_line_id=premature_line_id,
                    payout_id=p.payout_id,
                    order_line_id=line.order_line_id,
                    line_type='SALE',
                    amount=line.line_total,
                    description=f"PREMATURE payout credit for undelivered line {line.order_line_id}"
                )
                self.payout_lines.append(premature_payout_line)
                
                self.ground_truth_anomalies.append(AnomalyRecord(
                    scenario_id=1,
                    scenario_name="Payout Before Delivery or Hold Release",
                    entity_type="PAYOUT",
                    entity_id=p.payout_id,
                    detected_by="GROUND_TRUTH",
                    is_ground_truth=True,
                    severity="CRITICAL",
                    description=f"Payout {p.payout_id} marked as PAID while line {line.order_line_id} is in status '{line.status}'",
                    details=f"line_id: {line.order_line_id}, line_status: {line.status}, payout_status: {p.status}"
                ))

        # Scenario 2: Commission applied twice
        # Target: Order line where commission deduction occurs twice in payout lines
        if len(self.payouts) >= 2 and len(self.order_lines) >= 2:
            target_payout = self.payouts[1]
            target_line = self.order_lines[0]
            extra_line_id = f"PAYLINE-{target_payout.payout_id[-6:]}-999"
            dup_commission_line = PayoutLine(
                payout_line_id=extra_line_id,
                payout_id=target_payout.payout_id,
                order_line_id=target_line.order_line_id,
                line_type='COMMISSION',
                amount=-target_line.commission_amount,
                description=f"DUPLICATE commission deduction for line {target_line.order_line_id}"
            )
            self.payout_lines.append(dup_commission_line)
            
            self.ground_truth_anomalies.append(AnomalyRecord(
                scenario_id=2,
                scenario_name="Duplicate Commission Applied",
                entity_type="COMMISSION",
                entity_id=target_line.order_line_id,
                detected_by="GROUND_TRUTH",
                is_ground_truth=True,
                severity="HIGH",
                description=f"Order line {target_line.order_line_id} was charged duplicate commission in payout {target_payout.payout_id}",
                details=f"order_line_id: {target_line.order_line_id}, payout_id: {target_payout.payout_id}, duplicate_amount: {target_line.commission_amount}"
            ))

        # Scenario 3: Suspended seller continues listing
        # Target: Find a suspended seller and keep their product listing in 'ACTIVE' status
        suspended_sellers = [s for s in self.sellers if s.status == 'SUSPENDED']
        if not suspended_sellers:
            self.sellers[0].status = 'SUSPENDED'
            suspended_sellers = [self.sellers[0]]
            
        target_suspended = suspended_sellers[0]
        active_listings_under_suspended = [l for l in self.listings if l.seller_id == target_suspended.seller_id]
        if active_listings_under_suspended:
            target_listing = active_listings_under_suspended[0]
            target_listing.status = 'ACTIVE'  # Anomaly: should be INACTIVE/DELISTED
            
            self.ground_truth_anomalies.append(AnomalyRecord(
                scenario_id=3,
                scenario_name="Suspended Seller Continues Listing",
                entity_type="SELLER",
                entity_id=target_suspended.seller_id,
                detected_by="GROUND_TRUTH",
                is_ground_truth=True,
                severity="HIGH",
                description=f"Suspended seller {target_suspended.seller_id} still has active listing {target_listing.listing_id}",
                details=f"seller_id: {target_suspended.seller_id}, listing_id: {target_listing.listing_id}, listing_status: {target_listing.status}"
            ))

        # Scenario 4: Dispute not deducted from payout
        # Target: Find a payout that contains an order line with a customer-favor dispute, but remove the dispute line
        dispute_lines = [pl for pl in self.payout_lines if pl.line_type == 'DISPUTE' and pl.dispute_id]
        if dispute_lines:
            target_dispute_line = dispute_lines[0]
            target_dispute_id = target_dispute_line.dispute_id
            # Remove the dispute deduction line from payout
            self.payout_lines.remove(target_dispute_line)
            
            self.ground_truth_anomalies.append(AnomalyRecord(
                scenario_id=4,
                scenario_name="Dispute Not Deducted From Payout",
                entity_type="DISPUTE",
                entity_id=target_dispute_id,
                detected_by="GROUND_TRUTH",
                is_ground_truth=True,
                severity="HIGH",
                description=f"Dispute {target_dispute_id} resolved in customer favor but not deducted from payout",
                details=f"dispute_id: {target_dispute_id}"
            ))

        # Scenario 5: Payout total does not match payout lines (Financial discrepancy)
        if len(self.payouts) >= 4:
            discrepant_payout = self.payouts[3]
            # Corrupt the header net_payout_amount by adding $250.00
            discrepant_payout.net_payout_amount += Decimal('250.00')
            discrepant_payout.reconciliation_status = 'DISCREPANCY'
            
            self.ground_truth_anomalies.append(AnomalyRecord(
                scenario_id=5,
                scenario_name="Payout Total Discrepancy",
                entity_type="RECONCILIATION",
                entity_id=discrepant_payout.payout_id,
                detected_by="GROUND_TRUTH",
                is_ground_truth=True,
                severity="CRITICAL",
                description=f"Payout header {discrepant_payout.payout_id} net amount diverges from sum of payout lines by +250.00",
                details=f"payout_id: {discrepant_payout.payout_id}, tampered_net: {discrepant_payout.net_payout_amount}"
            ))

    def save_to_db(self, database_uri: str = None):
        """Persist all generated records to the database."""
        with get_session(database_uri) as session:
            print("Persisting records to database...")
            session.add_all(self.commission_rules)
            session.add_all(self.sellers)
            session.flush()

            session.add_all(self.listings)
            session.add_all(self.customers)
            session.flush()

            session.add_all(self.orders)
            session.flush()

            session.add_all(self.order_lines)
            session.flush()

            session.add_all(self.fulfillments)
            session.add_all(self.reviews)
            session.add_all(self.disputes)
            session.flush()

            session.add_all(self.payouts)
            session.flush()

            session.add_all(self.payout_lines)
            session.add_all(self.seller_events)
            session.add_all(self.listing_events)
            session.add_all(self.order_events)
            session.add_all(self.fulfillment_events)
            session.add_all(self.payout_events)
            session.add_all(self.ground_truth_anomalies)
            session.commit()
            print("Successfully persisted synthetic dataset into database!")

    def get_summary(self) -> Dict[str, int]:
        return {
            'sellers': len(self.sellers),
            'listings': len(self.listings),
            'customers': len(self.customers),
            'orders': len(self.orders),
            'order_lines': len(self.order_lines),
            'fulfillments': len(self.fulfillments),
            'reviews': len(self.reviews),
            'disputes': len(self.disputes),
            'commission_rules': len(self.commission_rules),
            'payouts': len(self.payouts),
            'payout_lines': len(self.payout_lines),
            'events_total': (
                len(self.seller_events) + len(self.listing_events) +
                len(self.order_events) + len(self.fulfillment_events) +
                len(self.payout_events)
            ),
            'ground_truth_anomalies': len(self.ground_truth_anomalies)
        }
