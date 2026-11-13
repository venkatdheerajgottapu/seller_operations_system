from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from database.connection import get_session
from app.models import CommissionRule, OrderLine, PayoutLine


class CommissionService:
    """Effective-dated commission rules, calculation, and duplicate charge prevention."""

    @staticmethod
    def get_effective_rule(category: str, order_date: datetime) -> Optional[CommissionRule]:
        with get_session() as session:
            rule = (
                session.query(CommissionRule)
                .filter(
                    CommissionRule.category == category,
                    CommissionRule.effective_from <= order_date,
                    (CommissionRule.effective_to.is_(None) | (CommissionRule.effective_to >= order_date)),
                    CommissionRule.is_active.is_(True)
                )
                .order_by(CommissionRule.effective_from.desc())
                .first()
            )
            return rule

    @staticmethod
    def calculate_commission(category: str, gross_amount: Decimal, order_date: datetime) -> Dict[str, Any]:
        """
        Calculate commission fee using effective-dated rule with min/max caps.
        """
        rule = CommissionService.get_effective_rule(category, order_date)
        base_rate = rule.base_rate if rule else Decimal('0.1000')
        min_commission = rule.min_commission if rule else Decimal('0.50')
        max_commission = rule.max_commission if rule else None

        calculated = (gross_amount * base_rate).quantize(Decimal('0.01'))
        if calculated < min_commission:
            calculated = min_commission
        if max_commission and calculated > max_commission:
            calculated = max_commission

        return {
            'rate': base_rate,
            'amount': calculated,
            'rule_id': rule.rule_id if rule else 'DEFAULT_FALLBACK'
        }

    @staticmethod
    def check_duplicate_commission(order_line_id: str) -> bool:
        """
        Audit whether commission was charged more than once for a given order line.
        """
        with get_session() as session:
            comm_line_count = session.query(PayoutLine).filter(
                PayoutLine.order_line_id == order_line_id,
                PayoutLine.line_type == 'COMMISSION'
            ).count()
            return comm_line_count > 1

