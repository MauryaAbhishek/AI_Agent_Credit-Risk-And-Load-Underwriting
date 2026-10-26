from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditRecord, UnderwritingRecord


def save_result(db: Session, application, result: dict) -> None:
    try:
        existing = db.get(
            UnderwritingRecord,
            application.application_id,
        )
        if existing:
            raise ValueError(
                "application_id already exists; use a new ID "
                "for a new submission or scenario."
            )

        record = UnderwritingRecord(
            application_id=application.application_id,
            applicant_reference=application.applicant_reference,
            policy_version=settings.policy_version,
            result_json=result,
        )

        audit = AuditRecord(
            application_id=application.application_id,
            event_type="UNDERWRITING_RECOMMENDATION_CREATED",
            policy_version=settings.policy_version,
            details_json={
                "recommendation": result["recommendation"],
                "risk_grade": result["risk_grade"],
                "intake_status": result["intake_status"],
                "fairness_status": result["fairness_status"],
                "note": (
                    "Audit payload excludes raw applicant financial inputs."
                ),
            },
        )

        db.add(record)
        db.add(audit)
        db.commit()

    except Exception:
        db.rollback()
        raise


def get_result(db: Session, application_id: str):
    record = db.get(UnderwritingRecord, application_id)
    if not record:
        return None

    return {
        "application_id": record.application_id,
        "created_at": (
            record.created_at.isoformat() if record.created_at else None
        ),
        "policy_version": record.policy_version,
        "result": record.result_json,
    }


def readiness(db: Session) -> bool:
    db.execute(select(1))
    return True


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

        # The new session can still query the database.
        assert db.execute(select(1)).scalar_one() == 1
