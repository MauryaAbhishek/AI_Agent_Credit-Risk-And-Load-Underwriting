from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

class LoanApplication(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    application_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    applicant_reference: str = Field(min_length=1, max_length=100)
    monthly_gross_income: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    existing_monthly_debt: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    proposed_monthly_payment: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    loan_amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    collateral_value: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)
    revolving_balance: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)
    revolving_limit: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=2)
    credit_history_months: int = Field(ge=0, le=1200)
    has_required_documents: bool = True

    @model_validator(mode="after")
    def validate_revolving_pair(self):
        if (self.revolving_balance is None) != (self.revolving_limit is None):
            raise ValueError("revolving_balance and revolving_limit must both be provided or both be omitted")
        if self.revolving_balance is not None and self.revolving_limit is not None:
            if self.revolving_balance > self.revolving_limit:
                raise ValueError("revolving_balance cannot exceed revolving_limit")
        return self

class UnderwritingResponse(BaseModel):
    application_id: str
    intake_status: str
    metrics: dict[str, Any]
    risk_grade: str
    risk_factors: list[str]
    recommendation: str
    conditions: list[str]
    policy_evidence: list[dict[str, Any]]
    policy_evidence_status: str
    policy_evidence_validation: dict[str, Any]
    fairness_status: str
    audit: dict[str, Any]
    explanation_letter_draft: str

class WhatIfRequest(BaseModel):
    application: LoanApplication
    changes: dict[str, Any] = Field(default_factory=dict)
