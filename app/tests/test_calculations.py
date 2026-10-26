from decimal import Decimal
from types import SimpleNamespace
from app.services.financial_calculations import calculate_metrics

def test_metrics_are_reproducible():
    app = SimpleNamespace(
        monthly_gross_income=Decimal("100000"),
        existing_monthly_debt=Decimal("20000"),
        proposed_monthly_payment=Decimal("15000"),
        loan_amount=Decimal("500000"),
        collateral_value=Decimal("700000"),
        revolving_balance=Decimal("10000"),
        revolving_limit=Decimal("50000"),
        credit_history_months=48,
    )
    result = calculate_metrics(app)
    assert result["dti_pct"] == "35.00"
    assert result["pti_pct"] == "15.00"
    assert result["ltv_pct"] == "71.43"
    assert result["credit_utilization_pct"] == "20.00"
