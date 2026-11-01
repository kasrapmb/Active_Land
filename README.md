# اکتیولند

Initial RTL, responsive homepage implementation and Django foundation. This is not yet a production registration system.

## Local development

Python 3.12:

```sh
cd /workspace/Active_Land
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
DJANGO_DEBUG=1 .venv/bin/python manage.py migrate --noinput
DJANGO_DEBUG=1 .venv/bin/python manage.py check
DJANGO_DEBUG=1 .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
```

SQLite is the local default. Set POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST and POSTGRES_PORT to select PostgreSQL. PostgreSQL integration has not been validated yet. Production requires DJANGO_SECRET_KEY and explicit DJANGO_ALLOWED_HOSTS; never enable debug publicly. Production server, HTTPS, backup and deployment configuration remain to be implemented.

## Implemented

- Homepage, CSS play illustration, four class cards, age filters and weekly schedule dialogs.
- Responsive layouts, keyboard dialogs and reduced-motion support.
- Django template rendering and built-in admin/auth migrations.

## Remaining

Database-backed catalog, parent OTP authentication, child profiles and age validation, course enrollment, transactional capacity reservations, payments, SMS, parent dashboard, custom Persian management, waiting lists, discounts, financial reports and production infrastructure. Schedule data currently lives in the frontend and must be moved to the catalog database. No capacity availability or payment success is simulated. Business rules for cancellation, age boundaries, refunds and mid-course enrollment await confirmation.

The frontend does not load third-party resources. Font currently uses system Tahoma/Arial; a locally hosted Persian font can follow.

`tools/preview.py` serves only the UI when Django dependencies are unavailable; it is not an application server.

## Database catalog and management

Run `DJANGO_DEBUG=1 .venv/bin/python manage.py seed_catalog` after migrations. This adds initial classes once and preserves manager edits and intentionally deleted sessions on subsequent runs. The homepage and schedule dialogs read the database. Create individual staff accounts with `manage.py createsuperuser` for the site administrator; grant the center manager only catalog permissions through Django groups. Never share accounts or commit passwords.

Run checks with `DJANGO_DEBUG=1 .venv/bin/python manage.py test catalog`.

Confirmed business rules: capacity initially 15 per session, no discounts, age measured on registration day, ongoing enrollment, one missed session recoverable within the same month, further absences forfeited, transfers and price differences handled by support. Refund/cancellation rules remain unspecified. Billing period for mid-course enrollment and waiting-list invitation behavior await clarification. Age intervals currently use inclusive lower and exclusive upper birthdays: [12,24), [24,36), [36,48) months. The upper boundary at exactly 48 months should be confirmed before activating enrollment.

Age validation is a tested domain helper, not a live registration endpoint yet. Capacity is configured but no reservation or payment flow exists yet. Django admin provides catalog management now; the custom operational dashboard remains outstanding.

## Rolling monthly subscriptions

The full listed fee applies on any registration day. A paid month starts on the registration date and expires on the same Persian calendar day of the following month (exclusive). When that day does not exist, use the last day of the next month. There is no automatic renewal or debit. The next payment must be explicitly confirmed. Holidays do not shift the subscription expiry date; confirm any requested exception with management.

`Subscription` records the paid fee and receipt immutably through the read-only admin. `OfficialHoliday` is editable by authorized staff; enter verified holidays explicitly. There is no automatic official-holiday feed yet. `session_occurs_on` excludes those dates from the weekly schedule.

An authorized operator can record a **previously verified, full-fee offline payment** with:

```sh
DJANGO_DEBUG=1 .venv/bin/python manage.py record_paid_month \
  --staff STAFF_USERNAME --parent PARENT_USERNAME --child 'نام کودک' \
  --birth-date YYYY-MM-DD --session SESSION_ID --reference UNIQUE_RECEIPT
```

The birth date argument is Gregorian. No sample accounts or default passwords are created. The service checks staff permission, registration-day age, active catalog entries, capacity and unique payment reference; it locks the session row on PostgreSQL. SQLite is only for local development and does not demonstrate concurrency safety. PostgreSQL concurrency tests and payment reservations remain required before public enrollment. Current child identity is a name/date snapshot; normalized child profiles, duplicate-enrollment protection, renewal UI, absence tracking and waiting-list SMS are subsequent work. Do not expose this offline service as a gateway callback.
