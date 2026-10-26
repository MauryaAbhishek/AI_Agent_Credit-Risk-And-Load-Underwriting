def draft_explanation(application_id: str, intake: dict, risk: dict, decision: dict) -> str:
    reasons = " ".join(risk["risk_factors"])
    if intake["issues"]:
        reasons += " Intake issues: " + " ".join(intake["issues"])
    return (
        f"DRAFT FOR AUTHORIZED REVIEW — application {application_id}. "
        f"Workflow recommendation: {decision['recommendation']}. "
        f"Risk classification: {risk['risk_grade']}. {reasons} "
        f"Conditions: {' '.join(decision['conditions'])} "
        "Synthetic demonstration only; not a final lending notice or legally sufficient adverse-action explanation."
    )
