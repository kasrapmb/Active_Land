# Validation evidence

- PostgreSQL 16: all 32 tests passed, including a two-thread race for one remaining seat. SQLite: 31 passed, PostgreSQL-only race test skipped.
- Chromium: homepage filters/dialogs, phone login via an explicitly enabled private local SMS inbox, parent profile, Persian birth-date child creation, registration hold, private API and dashboard; checked widths 320, 390 and 1440 with no horizontal overflow or JavaScript errors.
- Docker production image built with pinned Python dependencies and TLS verification retained.
- Production-mode Gunicorn: homepage 200 with database class data, PostgreSQL `/health/` response, WhiteNoise stylesheet 200. Tested internal HTTP behind a simulated trusted HTTPS proxy header; no public TLS certificate or domain was provisioned.
- Fresh production database migrations and catalog seed succeeded. `check --deploy` reported only optional HSTS preload warning; browser preload-list enrollment is intentionally not enabled automatically.
- PostgreSQL dump restored successfully into a separate temporary database; four catalog classes verified. This does not establish encrypted off-host backup readiness or restoration of real customer data.
- Payment and SMS adapters were tested using mocked provider responses. No real SMS or financial transaction was sent. Live credentials, account approvals and provider-specific acceptance tests remain required.
- GitHub Actions configuration added for PostgreSQL tests, migration drift, static collection and JavaScript syntax. Remote workflow execution is not claimed unless observed separately.
