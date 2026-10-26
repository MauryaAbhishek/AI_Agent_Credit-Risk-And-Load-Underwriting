def run_decision(intake: dict, risk: dict) -> dict:
    # No automated approvals or declines in this MVP; human underwriting is mandatory.
    if intake["status"] != "VALID":
        return {"recommendation": "REFER", "conditions": ["Resolve intake issues before underwriting review."]}
    if risk["risk_grade"] == "ELEVATED_DEMO_RISK":
        return {"recommendation": "REFER", "conditions": ["Human underwriter review required; demo risk band is elevated."]}
    if risk["risk_grade"] == "MODERATE_DEMO_RISK":
        return {"recommendation": "REFER", "conditions": ["Human underwriter must review supporting evidence and approved policy."]}
    return {"recommendation": "REFER", "conditions": ["Human underwriter approval is required; demo metrics cannot authorize lending."]}
