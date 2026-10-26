from app.services.credit_policy import assess_risk


def run_risk_assessment(
    metrics: dict,
    app,
    policy_evidence: list[dict] | None = None,
) -> dict:
    return assess_risk(metrics, app, policy_evidence)
