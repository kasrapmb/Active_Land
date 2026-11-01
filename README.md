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
