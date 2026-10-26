
from uuid import uuid4
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app, settings
from app.models import AuditRecord, UnderwritingRecord

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": settings.api_key or ""}


def payload(app_id=None):
    return {
        "application_id": app_id or f"PERSIST_{uuid4().hex}",
        "applicant_reference": "SYNTHETIC-PERSISTENCE-TEST",
        "monthly_gross_income": "80000",
        "existing_monthly_debt": "15000",
        "proposed_monthly_payment": "12000",
        "loan_amount": "400000",
        "collateral_value": "600000",
        "revolving_balance": "15000",
        "revolving_limit": "50000",
        "credit_history_months": 36,
        "has_required_documents": True,
    }


def test_saved_application_can_be_retrieved():
    body = payload()

    created = client.post(
        "/applications/underwrite",
        json=body,
        headers=AUTH_HEADERS,
    )
    assert created.status_code == 200

    fetched = client.get(
        f"/applications/{body['application_id']}",
        headers=AUTH_HEADERS,
    )
    assert fetched.status_code == 200

    data = fetched.json()
    assert data["application_id"] == body["application_id"]
    assert data["policy_version"] == created.json()["audit"]["policy_version"]
    assert data["result"]["recommendation"] == "REFER"
    assert data["result"]["metrics"]["dti_pct"] == "33.75"


def test_missing_application_returns_404():
    response = client.get(
        f"/applications/NOT_FOUND_{uuid4().hex}",
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 404



def test_underwriting_and_audit_records_are_persisted():
    body = payload()

    response = client.post(
        "/applications/underwrite",
        json=body,
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        record = db.get(UnderwritingRecord, body["application_id"])
        assert record is not None
        assert record.applicant_reference == body["applicant_reference"]
        assert record.policy_version
        assert record.result_json["recommendation"] == "REFER"

        audit_records = db.scalars(
            select(AuditRecord).where(
                AuditRecord.application_id == body["application_id"]
            )
        ).all()

        # Exactly one audit event for this successful submission.
        assert len(audit_records) == 1

        audit = audit_records[0]
        assert audit.application_id == record.application_id
        assert audit.event_type == "UNDERWRITING_RECOMMENDATION_CREATED"
        assert audit.policy_version == record.policy_version

        # Decision metadata must match the saved underwriting result.
        assert (
            audit.details_json["recommendation"]
            == record.result_json["recommendation"]
        )
        assert (
            audit.details_json["risk_grade"]
            == record.result_json["risk_grade"]
        )
        assert (
            audit.details_json["intake_status"]
            == record.result_json["intake_status"]
        )
        assert (
            audit.details_json["fairness_status"]
            == record.result_json["fairness_status"]
        )

        # Audit details must not include raw financial input fields.
        sensitive_input_fields = {
            "monthly_gross_income",
            "existing_monthly_debt",
            "proposed_monthly_payment",
            "loan_amount",
            "collateral_value",
            "revolving_balance",
            "revolving_limit",
        }
        assert sensitive_input_fields.isdisjoint(audit.details_json.keys())


def test_duplicate_submission_does_not_create_second_audit_record():
    body = payload()

    first = client.post(
        "/applications/underwrite",
        json=body,
        headers=AUTH_HEADERS,
    )
    assert first.status_code == 200

    second = client.post(
        "/applications/underwrite",
        json=body,
        headers=AUTH_HEADERS,
    )
    assert second.status_code == 409

    with SessionLocal() as db:
        records = db.scalars(
            select(UnderwritingRecord).where(
                UnderwritingRecord.application_id == body["application_id"]
            )
        ).all()

        audits = db.scalars(
            select(AuditRecord).where(
                AuditRecord.application_id == body["application_id"]
            )
        ).all()

        assert len(records) == 1
        assert len(audits) == 1



def test_commit_failure_rolls_back_underwriting_and_audit_records():
    body = payload()
    application_id = body["application_id"]

    with patch(
        "app.repository.Session.commit",
        side_effect=SQLAlchemyError("simulated commit failure"),
    ):
        response = client.post(
            "/applications/underwrite",
            json=body,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 500

    with SessionLocal() as db:
        assert db.get(UnderwritingRecord, application_id) is None

        audits = db.scalars(
            select(AuditRecord).where(
                AuditRecord.application_id == application_id
            )
        ).all()

        assert audits == []
        assert db.execute(select(1)).scalar_one() == 1
