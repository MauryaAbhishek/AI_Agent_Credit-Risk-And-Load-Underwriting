from uuid import uuid4

from fastapi.testclient import TestClient

from app.audit_integrity import calculate_event_hash
from app.db import SessionLocal
from app.main import app, settings
from app.models import AuditRecord

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": settings.api_key or ""}


def create_event(db, *, event_hash=True, previous_hash=None):
    event = AuditRecord(
        application_id=f"AUDIT_TEST_{uuid4().hex}",
        event_type="SYNTHETIC_AUDIT_TEST",
        policy_version="test-policy-v1",
        details_json={"recommendation": "REFER"},
        previous_hash=previous_hash,
        event_hash=None,
    )
    db.add(event)
    db.flush()

    if event_hash:
        event.event_hash = calculate_event_hash(
            event_id=event.id,
            application_id=event.application_id,
            event_type=event.event_type,
            policy_version=event.policy_version,
            created_at=event.created_at,
            details=event.details_json,
            previous_hash=event.previous_hash,
        )

    return event


def test_audit_verify_rejects_missing_api_key():
    response = client.get("/audit/verify", headers={})
    assert response.status_code == 401


def test_audit_verify_rejects_invalid_api_key():
    response = client.get(
        "/audit/verify",
        headers={"X-API-Key": "invalid-test-key"},
    )
    assert response.status_code == 401


def test_audit_verify_detects_tampered_event():
    with SessionLocal() as db:
        event = create_event(db)
        db.commit()
        event_id = event.id

    try:
        with SessionLocal() as db:
            event = db.get(AuditRecord, event_id)
            event.details_json = {"recommendation": "DECLINE"}
            db.commit()

        response = client.get("/audit/verify", headers=AUTH_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any(
            error.get("event_id") == event_id
            and error.get("error") == "event_hash_mismatch"
            for error in data["errors"]
        )
    finally:
        with SessionLocal() as db:
            event = db.get(AuditRecord, event_id)
            if event is not None:
                db.delete(event)
                db.commit()


def test_audit_verify_reports_legacy_event_as_unverifiable():
    with SessionLocal() as db:
        event = create_event(db, event_hash=False)
        db.commit()
        event_id = event.id

    try:
        response = client.get("/audit/verify", headers=AUTH_HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["unverifiable_count"] >= 1
        assert any(
            error.get("event_id") == event_id
            and error.get("error") == "missing_event_hash"
            for error in data["errors"]
        )
    finally:
        with SessionLocal() as db:
            event = db.get(AuditRecord, event_id)
            if event is not None:
                db.delete(event)
                db.commit()
