from validation.schema_validator import SystemDataValidator


def test_system_schema_and_id_validation():
    """Verify system-wide foreign keys, zero-padded ID conventions, and precision."""
    val = SystemDataValidator.validate_all()
    assert val['id_conventions_valid'] is True, f"ID violations: {val['violations']}"
    assert val['foreign_keys_consistent'] is True, f"FK violations: {val['violations']}"
    assert val['monetary_precision_valid'] is True

