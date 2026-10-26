
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditRecord, UnderwritingRecord


def save_result(db: Session, application, result: dict) -> None:
    """Persist an underwriting result and its audit event atomically."""
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
                "policy_evidence_status": result[
                    "policy_evidence_status"
                ],
                "policy_evidence_validation": result[
                    "policy_evidence_validation"
                ],
                "human_review_required": True,
                "approved_for_lending": False,
                "note": (
                    "Decision-support demo only. Human underwriter "
                    "review is required. This record does not "
                    "authorize lending. Raw applicant financial "
                    "inputs are excluded from audit details."
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
