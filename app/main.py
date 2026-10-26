import hmac
import logging
from typing import Any
import pandas as pd
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from app.audit_integrity import verify_audit_chain
from app.config import settings
from app.logging_config import configure_logging
from app.db import get_db
from app.models import UnderwritingRecord, AuditRecord
from app.repository import save_result, get_result
from app.schemas.application import LoanApplication, UnderwritingResponse, WhatIfRequest
from app.workflow.graph import underwriting_graph

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Production-oriented synthetic demo. Human review required; not approved for real lending.",
)

origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

@app.middleware("http")
async def request_logging(request: Request, call_next):
    response = await call_next(request)
    logger.info("request method=%s path=%s status=%s", request.method, request.url.path, response.status_code)
    return response

def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    # In development, an absent key is allowed for convenient local exploration.
    # Production startup rejects a missing/short key via Settings validation.
    if settings.app_env.lower() != "production" and not settings.api_key:
        return True
    if not settings.api_key or not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return True

@app.get("/health/live")
def live():
    return {"status": "alive"}

@app.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        logger.exception("Readiness check failed")
        raise HTTPException(status_code=503, detail="Database is not ready.") from exc

def run_workflow(application: LoanApplication) -> dict:
    result = underwriting_graph.invoke({"application": application})
    return {
        "application_id": application.application_id,
        "intake_status": result["intake"]["status"],
        "metrics": result["metrics"],
        "risk_grade": result["risk"]["risk_grade"],
        "risk_factors": result["risk"]["risk_factors"],
        "recommendation": result["decision"]["recommendation"],
        "conditions": result["decision"]["conditions"],
        "policy_evidence": result.get("policy_evidence", []),
        "policy_evidence_status": result["risk"]["policy_evidence_status"],
        "policy_evidence_validation": result["risk"]["policy_evidence_validation"],
        "fairness_status": result["audit"]["status"],
        "audit": result["audit"],
        "explanation_letter_draft": result["explanation"],
    }

@app.get(
    "/audit/verify",
    dependencies=[Depends(require_api_key)],
)
def verify_audit_integrity(db: Session = Depends(get_db)):
    """Verify stored audit hashes and links without exposing audit details."""
    try:
        records = db.scalars(
            select(AuditRecord).order_by(AuditRecord.id.asc())
        ).all()

        events = [
            {
                "event_id": record.id,
                "application_id": record.application_id,
                "event_type": record.event_type,
                "policy_version": record.policy_version,
                "created_at": record.created_at,
                "details": record.details_json,
                "previous_hash": record.previous_hash,
                "event_hash": record.event_hash,
            }
            for record in records
        ]

        verification = verify_audit_chain(events)

        if not records:
            status = "NO_EVENTS"
        elif verification["valid"]:
            status = "VERIFIED"
        else:
            status = "INTEGRITY_ISSUES"

        logger.info(
            "audit verification completed status=%s events=%s "
            "verified=%s unverifiable=%s errors=%s",
            status,
            len(records),
            verification["verified_count"],
            verification["unverifiable_count"],
            len(verification["errors"]),
        )

        return {
            "status": status,
            "total_events": len(records),
            **verification,
            "note": (
                "Hash verification provides tamper evidence, not "
                "proof against an attacker who can rewrite the entire "
                "database and recompute its hashes. Legacy events without "
                "hashes are not considered verified."
            ),
        }

    except Exception as exc:
        logger.exception("Audit integrity verification failed")
        raise HTTPException(
            status_code=500,
            detail="Audit verification failed; check server logs.",
        ) from exc


@app.post("/applications/underwrite", response_model=UnderwritingResponse, dependencies=[Depends(require_api_key)])
def underwrite(application: LoanApplication, db: Session = Depends(get_db)):
    try:
        result = run_workflow(application)
        save_result(db, application, result)
        logger.info("underwriting recommendation created application_id=%s", application.application_id)
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Underwriting workflow failed")
        raise HTTPException(status_code=500, detail="Underwriting workflow failed; check server logs using request time.") from exc

@app.get("/applications/{application_id}", dependencies=[Depends(require_api_key)])
def fetch_application(application_id: str, db: Session = Depends(get_db)):
    result = get_result(db, application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found.")
    return result

@app.post("/applications/what-if", dependencies=[Depends(require_api_key)])
def what_if(request: WhatIfRequest):
    allowed = set(LoanApplication.model_fields.keys()) - {"application_id", "applicant_reference"}
    invalid = set(request.changes) - allowed
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unsupported what-if fields: {sorted(invalid)}")
    changed = request.application.model_dump()
    changed.update(request.changes)
    # Keep the scenario clearly separate from the original; no persistence/overwrite.
    changed["application_id"] = request.application.application_id + "-SCENARIO"
    try:
        scenario = LoanApplication(**changed)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Scenario inputs failed validation.") from exc
    return {
        "baseline": run_workflow(request.application),
        "scenario": run_workflow(scenario),
        "changed_fields": sorted(request.changes.keys()),
        "note": "Synthetic scenario only; no application record is modified and human review is required.",
    }

@app.post("/portfolio/summary", dependencies=[Depends(require_api_key)])
def portfolio_summary(rows: list[dict[str, Any]]):
    if not rows:
        raise HTTPException(status_code=400, detail="Provide at least one result row.")
    frame = pd.DataFrame(rows)
    output: dict[str, Any] = {"row_count": int(len(frame)), "columns": list(frame.columns)}
    for column, key in [("recommendation", "recommendation_counts"), ("risk_grade", "risk_grade_counts")]:
        if column in frame.columns:
            output[key] = {str(k): int(v) for k, v in frame[column].fillna("UNKNOWN").value_counts().items()}
    return output
