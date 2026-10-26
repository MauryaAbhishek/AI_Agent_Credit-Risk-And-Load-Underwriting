# Demo policy: loan-to-value (LTV)
Policy version: demo-policy-v1
Status: development-only, not approved for lending.

- LTV = loan amount / verified collateral value.
- For demo tests only, LTV <= 80% is the lower demo band.
- For demo tests only, LTV > 80% and <= 95% is the moderate demo band.
- For demo tests only, LTV > 95% is the elevated demo band.
- LTV is relevant only for a secured product with verified collateral.
- LTV alone must never determine a real lending decision.
