
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app, settings
from app.services.credit_policy import assess_risk

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": settings.api_key or ""}


def payload(app_id=None):
    return {
        "application_id": app_id or f"TEST_{uuid4().hex}",
        "applicant_reference": "SYNTHETIC-001",
        "monthly_gross_income": "100000",
        "existing_monthly_debt": "20000",
        "proposed_monthly_payment": "15000",
        "loan_amount": "500000",
        "collateral_value": "700000",
        "revolving_balance": "10000",
        "revolving_limit": "50000",
        "credit_history_months": 48,
        "has_required_documents": True,
    }


def submit(body, headers=None):
    return client.post(
        "/applications/underwrite",
        json=body,
        headers=AUTH_HEADERS if headers is None else headers,
    )


def test_live():
    assert client.get("/health/live").status_code == 200


def test_rejects_extra_protected_field():
    body = payload()
    body["religion"] = "example"

    response = submit(body)
    assert response.status_code == 422



def test_underwriting():
    response = submit(payload())

    assert response.status_code == 200

    data = response.json()

    # Core underwriting response
    assert data["metrics"]["dti_pct"] == "35.00"
    assert data["recommendation"] == "REFER"

    # Policy evidence validation must be exposed by the API.
    assert "policy_evidence_status" in data
    assert data["policy_evidence_status"] in {
        "UNAVAILABLE",
        "VERSION_MISMATCH",
        "INVALID_EVIDENCE",
        "VALID_DEMO_ONLY",
    }

    validation = data["policy_evidence_validation"]
    assert isinstance(validation, dict)
    assert "status" in validation
    assert "approved_for_lending" in validation
    assert validation["approved_for_lending"] is False

    # Demo policy evidence must never authorize real lending.
    assert data["recommendation"] == "REFER"



def test_duplicate_id_conflicts():
    body = payload()

    first = submit(body)
    second = submit(body)

    assert first.status_code == 200
    assert second.status_code == 409


def test_missing_api_key_is_rejected():
    response = submit(payload(), headers={})
    assert response.status_code == 401


def test_incorrect_api_key_is_rejected():
    response = submit(
        payload(),
        headers={"X-API-Key": "definitely-not-the-correct-key"},
    )
    assert response.status_code == 401


def test_zero_income_is_rejected():
    body = payload()
    body["monthly_gross_income"] = "0"

    assert submit(body).status_code == 422


def test_zero_collateral_is_rejected():
    body = payload()
    body["collateral_value"] = "0"

    assert submit(body).status_code == 422


def test_negative_loan_amount_is_rejected():
    body = payload()
    body["loan_amount"] = "-1"

    assert submit(body).status_code == 422


def test_negative_existing_debt_is_rejected():
    body = payload()
    body["existing_monthly_debt"] = "-1"

    assert submit(body).status_code == 422


def test_revolving_balance_cannot_exceed_limit():
    body = payload()
    body["revolving_balance"] = "50001"
    body["revolving_limit"] = "50000"

    assert submit(body).status_code == 422


def risk_grade_for(dti, ltv):
    # Test the actual risk-band function without database or HTTP side effects.
    metrics = {
        "dti_pct": str(Decimal(dti)),
        "ltv_pct": str(Decimal(ltv)) if ltv is not None else None,
    }
    application = type(
        "Application",
        (),
        {"credit_history_months": 48},
    )()

    return assess_risk(metrics, application)["risk_grade"]


def test_dti_boundary_at_35_percent():
    assert risk_grade_for("35.00", "70.00") == "LOW_DEMO_RISK"


def test_dti_just_above_35_percent():
    assert risk_grade_for("35.01", "70.00") == "MODERATE_DEMO_RISK"


def test_dti_boundary_at_45_percent():
    assert risk_grade_for("45.00", "70.00") == "MODERATE_DEMO_RISK"


def test_dti_just_above_45_percent():
    assert risk_grade_for("45.01", "70.00") == "ELEVATED_DEMO_RISK"


def test_ltv_boundary_at_80_percent():
    assert risk_grade_for("30.00", "80.00") == "LOW_DEMO_RISK"


def test_ltv_just_above_80_percent():
    assert risk_grade_for("30.00", "80.01") == "MODERATE_DEMO_RISK"


def test_ltv_boundary_at_95_percent():
    assert risk_grade_for("30.00", "95.00") == "MODERATE_DEMO_RISK"


def test_ltv_just_above_95_percent():
    assert risk_grade_for("30.00", "95.01") == "ELEVATED_DEMO_RISK"
