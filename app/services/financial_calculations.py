from decimal import Decimal, ROUND_HALF_UP

HUNDRED = Decimal("100")

def pct(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return (numerator / denominator * HUNDRED).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def calculate_metrics(app) -> dict:
    total_debt = app.existing_monthly_debt + app.proposed_monthly_payment
    dti = pct(total_debt, app.monthly_gross_income)
    pti = pct(app.proposed_monthly_payment, app.monthly_gross_income)
    ltv = pct(app.loan_amount, app.collateral_value) if app.collateral_value else None
    utilization = None
    if app.revolving_balance is not None and app.revolving_limit is not None:
        utilization = pct(app.revolving_balance, app.revolving_limit)
    return {
        "gross_monthly_income": str(app.monthly_gross_income),
        "existing_monthly_debt": str(app.existing_monthly_debt),
        "proposed_monthly_payment": str(app.proposed_monthly_payment),
        "total_monthly_debt_including_proposed": str(total_debt),
        "dti_pct": str(dti) if dti is not None else None,
        "pti_pct": str(pti) if pti is not None else None,
        "ltv_pct": str(ltv) if ltv is not None else None,
        "credit_utilization_pct": str(utilization) if utilization is not None else None,
        "credit_history_months": app.credit_history_months,
    }
