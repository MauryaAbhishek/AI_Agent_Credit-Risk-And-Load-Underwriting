from app.services.financial_calculations import calculate_metrics
def run_metrics(app) -> dict:
    return calculate_metrics(app)
