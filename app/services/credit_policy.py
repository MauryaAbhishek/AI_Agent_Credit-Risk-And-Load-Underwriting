from decimal import Decimal

from app.config import settings


def validate_policy_evidence(policy_evidence: list[dict] | None) -> dict:
    """Validate provenance and version; never treat demo text as approved policy."""
    if not policy_evidence:
        return {
            "status": "UNAVAILABLE",
            "policy_version": settings.policy_version,
            "evidence_count": 0,
            "issues": ["No policy evidence was retrieved."],
            "approved_for_lending": False,
        }

    issues = []
    usable_documents = []

    for document in policy_evidence:
        if not isinstance(document, dict):
            issues.append("A policy evidence item is not a valid object.")
            continue

        source = document.get("source")
        version = document.get("policy_version")
        content = document.get("text")

        if not source or source == "system":
            issues.append("Policy evidence has no verifiable document source.")
            continue

        if not version or version == "unknown":
            issues.append(f"Policy document {source} has no declared version.")
            continue

        if version != settings.policy_version:
            issues.append(
                f"Policy document {source} has version {version}; "
                f"expected {settings.policy_version}."
            )
            continue

        if not isinstance(content, str) or not content.strip():
            issues.append(f"Policy document {source} has no usable text.")
            continue

        if "development-only, not approved for lending" not in content.lower():
            issues.append(
                f"Policy document {source} lacks the required demo-only disclaimer."
            )
            continue

        usable_documents.append(document)

    if issues:
        status = (
            "VERSION_MISMATCH"
            if any("version" in issue.lower() for issue in issues)
            else "INVALID_EVIDENCE"
        )
    elif usable_documents:
        status = "VALID_DEMO_ONLY"
    else:
        status = "INVALID_EVIDENCE"
        issues.append("No policy evidence passed validation.")

    return {
        "status": status,
        "policy_version": settings.policy_version,
        "evidence_count": len(usable_documents),
        "issues": issues,
        "approved_for_lending": False,
    }


def assess_risk(
    metrics: dict,
    app,
    policy_evidence: list[dict] | None = None,
) -> dict:
    # These are fixed demonstration thresholds, not approved lending criteria.
    factors, bands = [], []

    dti = Decimal(metrics["dti_pct"])
    if dti <= Decimal("35"):
        bands.append(1)
        factors.append(f"DTI is {dti}%, within the lower demo band (<=35%).")
    elif dti <= Decimal("45"):
        bands.append(2)
        factors.append(f"DTI is {dti}%, within the moderate demo band (>35% to 45%).")
    else:
        bands.append(3)
        factors.append(f"DTI is {dti}%, above the demo 45% threshold.")

    ltv_value = metrics.get("ltv_pct")
    if ltv_value is not None:
        ltv = Decimal(ltv_value)
        if ltv <= Decimal("80"):
            bands.append(1)
            factors.append(f"LTV is {ltv}%, within the lower demo band (<=80%).")
        elif ltv <= Decimal("95"):
            bands.append(2)
            factors.append(f"LTV is {ltv}%, within the moderate demo band (>80% to 95%).")
        else:
            bands.append(3)
            factors.append(f"LTV is {ltv}%, above the demo 95% threshold.")

    if app.credit_history_months < 12:
        bands.append(2)
        factors.append(
            "Credit history is shorter than 12 months; additional review may be appropriate."
        )
    else:
        factors.append(f"Credit history provided: {app.credit_history_months} months.")

    max_band = max(bands, default=2)
    grade = {
        1: "LOW_DEMO_RISK",
        2: "MODERATE_DEMO_RISK",
        3: "ELEVATED_DEMO_RISK",
    }[max_band]

    evidence_validation = validate_policy_evidence(policy_evidence)

    return {
        "risk_grade": grade,
        "risk_factors": factors,
        "policy_version": settings.policy_version,
        "policy_evidence_status": evidence_validation["status"],
        "policy_evidence_validation": evidence_validation,
    }
