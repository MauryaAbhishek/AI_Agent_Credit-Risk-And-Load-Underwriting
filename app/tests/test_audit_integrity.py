from datetime import datetime, timezone
from copy import deepcopy

from app.audit_integrity import verify_audit_chain
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



def make_chained_events():
    first = sample_event()
    first["event_hash"] = calculate_event_hash(**first)

    second = {
        **sample_event(),
        "event_id": 2,
        "application_id": "SYNTHETIC_AUDIT_TEST_2",
        "previous_hash": first["event_hash"],
    }
    second["event_hash"] = calculate_event_hash(**second)

    return [first, second]


def test_valid_audit_chain_passes():
    result = verify_audit_chain(make_chained_events())

    assert result["valid"] is True
    assert result["verified_count"] == 2
    assert result["unverifiable_count"] == 0
    assert result["errors"] == []


def test_modified_event_details_are_detected():
    events = make_chained_events()
    events[0]["details"]["recommendation"] = "DECLINE"

    result = verify_audit_chain(events)

    assert result["valid"] is False
    assert any(
        error["error"] == "event_hash_mismatch"
        for error in result["errors"]
    )


def test_broken_chain_link_is_detected():
    events = make_chained_events()
    events[1]["previous_hash"] = "f" * 64

    result = verify_audit_chain(events)

    assert result["valid"] is False
    assert any(
        error["error"] == "previous_hash_mismatch"
        for error in result["errors"]
    )


def test_missing_hash_is_reported_as_unverifiable():
    events = make_chained_events()
    events[0]["event_hash"] = None

    result = verify_audit_chain(events)

    assert result["valid"] is False
    assert result["unverifiable_count"] == 1
    assert any(
        error["error"] == "missing_event_hash"
        for error in result["errors"]
    )
