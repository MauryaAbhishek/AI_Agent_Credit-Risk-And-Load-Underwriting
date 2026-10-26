from typing import TypedDict, Any
class UnderwritingState(TypedDict, total=False):
    application: Any
    intake: dict
    metrics: dict
    risk: dict
    decision: dict
    policy_evidence: list
    audit: dict
    explanation: str
