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


def test_reproducibility_exported_files_bitwise_identical(tmp_path):
    """
    Generate two datasets with seed 20261022 and export their tables to CSV.
    Verify that the exported CSVs are 100% bitwise identical with matching SHA-256 hashes.
    """
    import csv
    import hashlib

    dir1 = tmp_path / "run1"
    dir2 = tmp_path / "run2"
    dir1.mkdir()
    dir2.mkdir()

    gen1 = SyntheticDataGenerator(seed=GLOBAL_SEED)
    gen1.generate('STARTER')

    gen2 = SyntheticDataGenerator(seed=GLOBAL_SEED)
    gen2.generate('STARTER')

    tables = {
        'sellers': [s.to_dict() for s in gen1.sellers],
        'orders': [o.to_dict() for o in gen1.orders],
        'payouts': [p.to_dict() for p in gen1.payouts]
    }
    tables2 = {
        'sellers': [s.to_dict() for s in gen2.sellers],
        'orders': [o.to_dict() for o in gen2.orders],
        'payouts': [p.to_dict() for p in gen2.payouts]
    }

    for name in tables:
        path1 = dir1 / f"{name}.csv"
        path2 = dir2 / f"{name}.csv"
        with open(path1, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=tables[name][0].keys())
            w.writeheader()
            w.writerows(tables[name])
        with open(path2, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=tables2[name][0].keys())
            w.writeheader()
            w.writerows(tables2[name])

        hash1 = hashlib.sha256(path1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(path2.read_bytes()).hexdigest()
        assert hash1 == hash2, f"Bitwise export hash mismatch for {name}: {hash1} != {hash2}"


