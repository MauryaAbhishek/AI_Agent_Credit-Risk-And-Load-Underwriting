from langgraph.graph import StateGraph, START, END
from app.workflow.state import UnderwritingState
from app.agents.intake_agent import run_intake
from app.agents.metrics_agent import run_metrics
from app.agents.risk_assessment_agent import run_risk_assessment
from app.agents.decision_agent import run_decision
from app.agents.fairness_audit_agent import run_fairness_audit
from app.agents.explanation_letter_agent import draft_explanation
from app.vector_store.policy_retriever import retrieve_policy

def intake_node(state: UnderwritingState):
    return {"intake": run_intake(state["application"])}

def metrics_node(state: UnderwritingState):
    return {"metrics": run_metrics(state["application"])}

def policy_node(state: UnderwritingState):
    m = state["metrics"]
    a = state["application"]
    q = f"Approved underwriting policy DTI {m.get('dti_pct')} percent LTV {m.get('ltv_pct')} percent"
    return {"policy_evidence": retrieve_policy(q)}

def risk_node(state: UnderwritingState):
    return {
        "risk": run_risk_assessment(
            state["metrics"],
            state["application"],
            state.get("policy_evidence", []),
        )
    }

def decision_node(state: UnderwritingState):
    return {"decision": run_decision(state["intake"], state["risk"])}

def audit_node(state: UnderwritingState):
    return {"audit": run_fairness_audit(state["intake"], state["risk"], state["decision"])}

def explanation_node(state: UnderwritingState):
    return {"explanation": draft_explanation(
        state["application"].application_id, state["intake"], state["risk"], state["decision"]
    )}

def build_graph():
    g = StateGraph(UnderwritingState)
    for name, node in [
        ("intake", intake_node), ("metrics", metrics_node), ("policy_retrieval", policy_node),
        ("risk_assessment", risk_node), ("decision", decision_node),
        ("fairness_audit", audit_node), ("explanation_letter", explanation_node)
    ]:
        g.add_node(name, node)
    g.add_edge(START, "intake")
    g.add_edge("intake", "metrics")
    g.add_edge("metrics", "policy_retrieval")
    g.add_edge("policy_retrieval", "risk_assessment")
    g.add_edge("risk_assessment", "decision")
    g.add_edge("decision", "fairness_audit")
    g.add_edge("fairness_audit", "explanation_letter")
    g.add_edge("explanation_letter", END)
    return g.compile()

underwriting_graph = build_graph()
