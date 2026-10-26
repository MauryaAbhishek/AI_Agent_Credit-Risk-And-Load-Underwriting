from datetime import datetime, timezone

from app.audit_integrity import calculate_event_hash, verify_event_hash


def sample_event():
    return {
        "event_id": 1,
        "application_id": "SYNTHETIC_AUDIT_TEST",
        "event_type": "UNDERWRITING_RECOMMENDATION_CREATED",
        "policy_version": "demo-policy-v1",
        "created_at": datetime(2026, 10, 25, tzinfo=timezone.utc),
        "details": {
            "recommendation": "REFER",
            "risk_grade": "LOW_DEMO_RISK",
            "intake_status": "COMPLETE",
            "fairness_status": "REVIEW_REQUIRED",
        },
        "previous_hash": None,
    }


def test_same_event_produces_same_hash():
    event = sample_event()

    first = calculate_event_hash(**event)
    second = calculate_event_hash(**event)

    assert first == second
    assert len(first) == 64


def test_changed_decision_metadata_changes_hash():
    event = sample_event()
    original_hash = calculate_event_hash(**event)

    event["details"]["recommendation"] = "DECLINE"

    assert calculate_event_hash(**event) != original_hash


def test_changed_previous_hash_changes_hash():
    event = sample_event()
    original_hash = calculate_event_hash(**event)

    event["previous_hash"] = "a" * 64

    assert calculate_event_hash(**event) != original_hash


def test_verification_detects_modified_event():
    event = sample_event()
    event_hash = calculate_event_hash(**event)

    assert verify_event_hash(expected_hash=event_hash, **event)

    modified = {**event, "policy_version": "modified-policy"}

    assert not verify_event_hash(expected_hash=event_hash, **modified)
