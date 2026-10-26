def run_intake(app) -> dict:
    issues = []
    if not app.has_required_documents:
        issues.append("Required documents are missing.")
    return {"status": "NEEDS_INFORMATION" if issues else "VALID", "issues": issues}
