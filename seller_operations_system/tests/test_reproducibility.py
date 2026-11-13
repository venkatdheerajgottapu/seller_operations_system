import pytest
from decimal import Decimal
from data_generator.generator import SyntheticDataGenerator, GLOBAL_SEED


def test_reproducibility_identical_runs():
    """
    Verify that two independent generator runs with seed 20261022 produce
    exact bitwise identical outputs for sellers, orders, amounts, and anomalies.
    """
    gen1 = SyntheticDataGenerator(seed=GLOBAL_SEED)
    summary1 = gen1.generate('STARTER')

    gen2 = SyntheticDataGenerator(seed=GLOBAL_SEED)
    summary2 = gen2.generate('STARTER')

    # 1. Compare summaries
    assert summary1 == summary2, f"Summaries diverge: {summary1} vs {summary2}"

    # 2. Compare seller IDs and names
    sellers1 = [(s.seller_id, s.name, s.status, s.rating) for s in gen1.sellers]
    sellers2 = [(s.seller_id, s.name, s.status, s.rating) for s in gen2.sellers]
    assert sellers1 == sellers2, "Seller lists diverge across reproducible runs"

    # 3. Compare order lines and line totals
    lines1 = [(l.order_line_id, l.seller_id, l.line_total, l.commission_amount) for l in gen1.order_lines]
    lines2 = [(l.order_line_id, l.seller_id, l.line_total, l.commission_amount) for l in gen2.order_lines]
    assert lines1 == lines2, "Order lines diverge across reproducible runs"

    # 4. Compare payouts and net amounts
    payouts1 = [(p.payout_id, p.seller_id, p.gross_amount, p.net_payout_amount) for p in gen1.payouts]
    payouts2 = [(p.payout_id, p.seller_id, p.gross_amount, p.net_payout_amount) for p in gen2.payouts]
    assert payouts1 == payouts2, "Payout batches diverge across reproducible runs"

    # 5. Compare ground truth anomalies
    anomalies1 = [(a.scenario_id, a.entity_type, a.entity_id) for a in gen1.ground_truth_anomalies]
    anomalies2 = [(a.scenario_id, a.entity_type, a.entity_id) for a in gen2.ground_truth_anomalies]
    assert anomalies1 == anomalies2, "Injected anomalies diverge across reproducible runs"

