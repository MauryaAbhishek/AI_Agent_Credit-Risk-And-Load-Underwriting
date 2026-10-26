from app.config import settings
from app.services.credit_policy import validate_policy_evidence


def evidence(
    source="demo_dti.md",
    version=None,
    text="# Demo policy\nStatus: development-only, not approved for lending.",
):
    return {
        "id": "demo-dti",
        "source": source,
        "policy_version": version or settings.policy_version,
        "text": text,
        "distance": 0.1,
    }


def test_valid_demo_evidence_is_never_approved_for_lending():
    result = validate_policy_evidence([evidence()])

    assert result["status"] == "VALID_DEMO_ONLY"
    assert result["evidence_count"] == 1
    assert result["approved_for_lending"] is False


def test_missing_evidence_is_unavailable():
    result = validate_policy_evidence([])

    assert result["status"] == "UNAVAILABLE"
    assert result["approved_for_lending"] is False


def test_wrong_policy_version_is_rejected():
    result = validate_policy_evidence(
        [evidence(version="different-policy-version")]
    )

    assert result["status"] == "VERSION_MISMATCH"
    assert result["evidence_count"] == 0
    assert result["approved_for_lending"] is False


def test_system_fallback_is_not_treated_as_policy_document():
    result = validate_policy_evidence([
        {
            "id": "retrieval-unavailable",
            "source": "system",
            "text": "Policy retrieval unavailable; human review required.",
            "distance": None,
        }
    ])

    assert result["status"] == "INVALID_EVIDENCE"
    assert result["evidence_count"] == 0


def test_document_without_demo_disclaimer_is_rejected():
    result = validate_policy_evidence([
        evidence(text="# Policy\nThis text has no required disclaimer.")
    ])

    assert result["status"] == "INVALID_EVIDENCE"
    assert result["evidence_count"] == 0


def test_mixed_versions_are_not_accepted_as_valid_evidence():
    result = validate_policy_evidence([
        evidence(),
        evidence(source="stale_policy.md", version="old-policy-version"),
    ])

    assert result["status"] == "VERSION_MISMATCH"
    assert result["approved_for_lending"] is False




def test_invalid_evidence_is_never_approved_for_lending():
    result = validate_policy_evidence([
        evidence(text="# Policy\nNo required disclaimer.")
    ])

    assert result["status"] == "INVALID_EVIDENCE"
    assert result["approved_for_lending"] is False


def test_all_policy_validation_outcomes_deny_lending_approval():
    cases = [
        [],
        [evidence(version="different-policy-version")],
        [
            evidence(
                text="# Policy\nMissing required disclaimer."
            )
        ],
        [evidence()],
    ]

    for policy_evidence in cases:
        result = validate_policy_evidence(policy_evidence)

        assert result["approved_for_lending"] is False


def test_malformed_evidence_is_not_accepted():
    result = validate_policy_evidence([
        {
            "id": "malformed",
            "source": "",
            "policy_version": settings.policy_version,
            "text": "",
            "distance": None,
        }
    ])

    assert result["status"] == "INVALID_EVIDENCE"
    assert result["evidence_count"] == 0
    assert result["approved_for_lending"] is False

