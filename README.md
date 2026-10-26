# Credit Risk & Loan Underwriting — Production-Oriented MVP

This is a **production-oriented MVP baseline**, not a certified lending system. It adds API-key protection, configuration validation, persistent application/audit records, PostgreSQL deployment support, structured logs, health/readiness endpoints, deterministic calculations, policy retrieval, and tests.

## Included agents
1. Intake Agent — schema and completeness checks
2. Metrics Agent — deterministic Python `Decimal` calculations, with Pandas for portfolio summaries
3. Risk Assessment Agent — illustrative, versioned policy rules and evidence
4. Decision Agent — conservative recommendation; never auto-approves
5. What-if Simulator — reruns a scenario without overwriting the original
6. Fairness & Audit Agent — records decision trace; not a statistical fairness certification
7. Explanation Letter Agent — draft only, never auto-sent

## Critical scope limitations
- Demo policy thresholds are placeholders and must not be used for actual lending.
- Outputs are recommendations requiring an authorized human underwriter.
- No real credit bureau, identity verification, document OCR, or payment data integrations are included.
- This project is not legally or regulatorily certified. Before real-world use, add formal model/policy validation, privacy/security review, role-based access control, secrets management, migrations, monitoring/alerting, backups, retention/deletion procedures, and jurisdiction-specific compliance.
- Do not submit real personal or financial information to this demo until your organization has approved its security and privacy controls.

## Local setup (Python 3.12)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python -m app.vector_store.ingest_policies
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

Run tests:
```bash
pytest -q
```

## Production-like Docker setup

1. Copy `.env.example` to `.env`.
2. Set `API_KEY` and `POSTGRES_PASSWORD` to long random secrets. Never commit `.env`.
3. In `.env`, use `APP_ENV=production` and a non-default API key.
4. Run:
```bash
docker compose up --build -d
docker compose logs -f api
```
5. Index policy documents in the environment where the Chroma volume is mounted:
```bash
docker compose exec api python -m app.vector_store.ingest_policies
```
The API is bound to `127.0.0.1:8000` on the host by default. Put it behind a properly configured TLS reverse proxy before exposing it beyond localhost.

## Authentication

Every `/applications/*` and `/portfolio/*` route requires `X-API-Key`. `/health/live` is public. `/health/ready` checks database connectivity. For production, `API_KEY` is required at startup. Use a secret manager in deployment rather than storing production secrets in files.

Example:
```bash
curl -H "X-API-Key: $API_KEY" http://127.0.0.1:8000/health/ready
```

## Underwriting example

```bash
curl -X POST http://127.0.0.1:8000/applications/underwrite \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "application_id":"DEMO-001",
    "applicant_reference":"SYNTHETIC-001",
    "monthly_gross_income":"100000",
    "existing_monthly_debt":"20000",
    "proposed_monthly_payment":"15000",
    "loan_amount":"500000",
    "collateral_value":"700000",
    "revolving_balance":"10000",
    "revolving_limit":"50000",
    "credit_history_months":48,
    "has_required_documents":true
  }'
```

## API routes
- `GET /health/live` — process liveness
- `GET /health/ready` — database readiness
- `POST /applications/underwrite` — execute workflow and persist application + audit record
- `GET /applications/{application_id}` — fetch stored result
- `POST /applications/what-if` — run a scenario without overwriting the base application
- `POST /portfolio/summary` — Pandas aggregation for supplied result rows

## Architecture
- LangGraph orchestrates the deterministic workflow.
- ChromaDB provides semantic retrieval over policy documents.
- Policy retrieval is supporting evidence only; it does not change a rule threshold or override deterministic code.
- SQLAlchemy stores application results and audit records.
- Pydantic rejects undeclared input fields; protected characteristics are not accepted as underwriting inputs.
- Pandas is used for portfolio aggregation; `Decimal` is used for monetary/ratio calculations.

## Next steps before real lending
1. Replace demo policy with approved, signed, versioned policy definitions.
2. Add Alembic migrations, RBAC/OIDC, rate limiting, per-user audit attribution, and tenant isolation.
3. Add automated security scanning, dependency pinning/lockfile, CI, load tests, backup/restore drills, metrics and alerts.
4. Validate adverse-action explanation requirements and fairness evaluation with compliance/legal teams.
