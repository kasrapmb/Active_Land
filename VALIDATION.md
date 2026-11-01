# Validation evidence

- PostgreSQL 16: all 32 tests passed, including a two-thread race for one remaining seat. SQLite: 31 passed, PostgreSQL-only race test skipped.
- Chromium: homepage filters/dialogs, phone login via an explicitly enabled private local SMS inbox, parent profile, Persian birth-date child creation, registration hold, private API and dashboard; checked widths 320, 390 and 1440 with no horizontal overflow or JavaScript errors.
- Docker production image built with pinned Python dependencies and TLS verification retained.
- Production-mode Gunicorn: homepage 200 with database class data, PostgreSQL `/health/` response, WhiteNoise stylesheet 200. Tested internal HTTP behind a simulated trusted HTTPS proxy header; no public TLS certificate or domain was provisioned.
- Fresh production database migrations and catalog seed succeeded. `check --deploy` reported only optional HSTS preload warning; browser preload-list enrollment is intentionally not enabled automatically.
- PostgreSQL dump restored successfully into a separate temporary database; four catalog classes verified. This does not establish encrypted off-host backup readiness or restoration of real customer data.
- Payment and SMS adapters were tested using mocked provider responses. No real SMS or financial transaction was sent. Live credentials, account approvals and provider-specific acceptance tests remain required.
- GitHub Actions configuration added for PostgreSQL tests, migration drift, static collection and JavaScript syntax. Remote workflow execution is not claimed unless observed separately.


## Management workspace update

- PostgreSQL: all 42 tests passed. SQLite: 41 passed; one PostgreSQL-only concurrency test skipped.
- Added checks for class/session navigation, private child records, correct renewal boundaries, ignoring older renewed/cancelled periods, lesson counts excluding holidays, idempotent present/absent correction and rejection of future/non-session dates.
- Chromium: management index, class view, roster, child file and Django admin at 1440/390/320 widths; local Vazirmatn font loaded, no horizontal overflow and no JavaScript errors. Saving attendance through the CSRF-protected browser form succeeded.
- Fixed a missing settings import in the login view and added a successful OTP-form regression test.
