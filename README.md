# اکتیولند

Persian RTL registration application for ongoing mother-and-child classes. Django 5.2, PostgreSQL in production, responsive server-rendered frontend and session-authenticated JSON API.

## Development

```sh
cd /workspace/Active_Land
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
DJANGO_DEBUG=1 .venv/bin/python manage.py migrate --noinput
DJANGO_DEBUG=1 .venv/bin/python manage.py seed_catalog
DJANGO_DEBUG=1 .venv/bin/python manage.py setup_roles
DJANGO_DEBUG=1 LOCAL_SMS_ENABLED=1 .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
```

Local-only SMS codes go to ignored owner-readable `.local-sms/PHONE.txt` files. This explicit debug option never activates in production. No default accounts or passwords are created. Use `manage.py createsuperuser` to create your private site administrator. Assign the restricted manager group to a separate staff account for the center manager.

SQLite is a development fallback. Set POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST and POSTGRES_PORT to use PostgreSQL. Production refuses to boot without PostgreSQL and a DJANGO_SECRET_KEY.

## Capabilities

- Database-backed homepage, class/age filters, independent weekly sessions and registration forms.
- Parent OTP login with hashed expiring single-use codes, rate limits and attempt limits; optional Kavenegar adapter.
- Multi-child profiles with Persian date input, parent/contact information, private dashboard and payment receipts.
- Rolling Persian-calendar-month subscriptions, full listed fee on any registration day, explicit renewal after expiry. A nonexistent next-month day uses that month's last day.
- Ten-minute capacity reservations with PostgreSQL row locks, age/ownership checks and idempotent current hold retrieval.
- Optional Zarinpal request/verify adapter with toman-to-rial conversion; repeated verification cannot create duplicate subscriptions. Late paid callbacks are recorded for support review without allocating an expired seat.
- Staff verification of offline payments; transfer/cancellation operations with audit history and support-led price/refund handling.
- Waiting list with first-waiter SMS outbox, expiry processing, renewal reminders and provider retries.
- Persian management dashboard, Excel export, restricted manager roles, holiday and absence/makeup records.
- JSON API under `/api/v1/`, CSRF-protected mutations, private-page cache protection.
- Gunicorn, WhiteNoise and Docker/Caddy deployment configuration.

## Business rules

Initial session capacity is 15, editable by the manager. Fees: 1,850,000 toman for نقل و نبات / قند و عسل / دردونه; 2,400,000 for جوونه. No discounts. Classes run continuously except explicitly entered official holidays. Holidays do not automatically extend the subscription. Age is checked on registration; implemented intervals are [12,24), [24,36), [36,48) months. Out-of-range children require offline coordination; only the site superuser can record a paid manual exception with a reason. No public bypass is exposed. Confirm the exact 48-month boundary with the operator before launch.

One missed session can be marked for makeup in the same Persian month and within subscription validity. Further absences cannot be redeemed. Support handles transfers and any price difference. Cancellation never automatically issues a refund. Waiting invitations do not reserve capacity; a nonresponding invited request can be closed by the manager after follow-up. An automatic invitation deadline has not been specified.

## Tests

```sh
DJANGO_DEBUG=1 .venv/bin/python manage.py test catalog portal enrollment
```

The last-seat race test runs only on PostgreSQL and is skipped on SQLite. Use the PostgreSQL environment variables above to execute the whole suite. End-to-end browser validation covers OTP through the private local inbox, parent details, child creation and booking at mobile/desktop widths. Provider tests use mocks; no live money or SMS is represented as tested.

## Operations and remaining launch prerequisites

See [deployment and API guide](deploy/README.md). Run `process_enrollments` every minute; the supplied scheduler container does this. `seed_catalog` only inserts missing initial classes and never overwrites manager edits or recreates intentionally deleted sessions.

The application has not been deployed to a public domain. Hosting/DNS, payment merchant approval, SMS account/template/sender, real-provider end-to-end checks, operator-entered holidays, encrypted off-host backups and a restore drill are required before release. Production SMS/online payment stay disabled without configuration. Provider callable interfaces permit changing vendors. The initial frontend-only `tools/preview.py` is retained for UI work and is not an application server.


## Management workspace

After staff authentication, open `/registration/management/`. Choose a class, then its session to see current children, temporary holds, open capacity, renewals due within three days, and the last subscription per child. Previous renewed months do not create duplicate overdue entries. Cancelled latest registrations are excluded from renewal follow-up.

The session roster supports name/mobile search (including Persian digits), active/due/all filters and a Persian date selector. Managers can mark present/absent or clear mistakes on valid past/current lesson dates. Future dates, holidays and dates outside subscription validity are rejected. Attendance changes are audited. A missing attendance entry is explicitly unrecorded, never assumed present or absent.

Lesson totals are calculated from the subscription interval and the session's current weekly schedule, excluding manager-entered official holidays. They are scheduled lessons, not a purchased fixed-session package. The roster separates scheduled, actual presence, absence, upcoming and past-unrecorded counts. Changes to the weekly schedule/holiday list update the planned count; recorded attendance remains separate.

Child files show birth date, age, parent/emergency contact, instructor notes and subscription/lesson history. Managers need explicit child/profile read permissions. Parents can view/edit only their own children; historical receipt snapshots are preserved. Parent dashboard child cards link directly to the child file.

The self-hosted Vazirmatn variable font (v33.003, SIL Open Font License) is used on public pages, the parent workspace and Django admin. Font files and license are in `catalog/static/catalog/fonts/`.

### Updating on Windows PowerShell

After obtaining the latest source, keep your existing `.venv` and local database. Run:

```powershell
$env:DJANGO_DEBUG = "1"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py setup_roles
.\.venv\Scripts\python.exe manage.py runserver
```

Log in through `/admin/` with your site administrator account, then choose “میزکار مدیریت اکتیولند”. The homepage also shows a management shortcut for staff. Assign the manager group only to the authorized center manager.
