# Deployment

This configuration requires a Linux Docker host, domain with DNS pointing to it, open inbound ports 80/443 and purchased payment/SMS service accounts. No deployment has been performed.

1. Copy `.env.example` to `.env` and fill the required values securely. Generate a unique high-entropy Django secret and database password. Set APP_DOMAIN and DJANGO_ALLOWED_HOSTS to your hostname; PUBLIC_BASE_URL and CSRF_TRUSTED_ORIGINS to `https://your-hostname`. Never use DEBUG in production.
2. Build: `docker compose build web`. In the managed cloud runtime use the documented proxy CA mount: `docker build --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t activeland-web:local .`.
3. Start database: `docker compose up -d db`.
4. Migrate and seed: `docker compose run --rm web python manage.py migrate --noinput`, then `docker compose run --rm web python manage.py seed_catalog`.
5. Create your private admin account: `docker compose run --rm web python manage.py createsuperuser`.
6. Create the center manager with a separate account and group; grant only required catalog, child, subscription view and enrollment operation permissions. Do not give parents staff status. Do not grant manager user/group editing rights.
7. Check production settings: `docker compose run --rm web python manage.py check --deploy`.
8. Start application and scheduler: `docker compose up -d web scheduler proxy`. Caddy obtains and renews TLS certificates automatically once DNS resolves to this host.
9. Verify HTTPS homepage, `/health/`, OTP delivery, age restrictions, last-seat booking, actual gateway charge/verify, receipt, cancellation, waiting SMS and reminder. Gateway/SMS live checks require real accounts and have not been executed.

## Provider boundaries

`PAYMENT_BACKEND=enrollment.gateway.Zarinpal` selects the Zarinpal adapter. Supply PAYMENT_MERCHANT_ID in the host's secure configuration. The adapter converts stored toman to rial once, checks server-to-server verification, and records late successful payments for support review without overselling. Do not enable until merchant approval, callback hostname and provider behavior have been verified in the provider's supported test environment. No sandbox success endpoint is exposed by this app.

`SMS_SEND_FUNCTION` must name a Python callable `(phone, message)` supplied by the selected provider integration. It must return only after confirmed acceptance or raise on failure, keep credentials out of logs, and use HTTPS. Provider selection and credentials are still outstanding. OTP fails closed without it. Local development may explicitly enable `LOCAL_SMS_ENABLED=1` with DEBUG; generated codes then go to ignored `.local-sms/PHONE.txt` files, never a public endpoint. Do not enable this in production.

The scheduler runs once per minute and expires holds, queues first-waiter notifications and two-day renewal reminders, and retries pending SMS up to five times. One active invited waiter is outstanding at a time; operator handling of no-response invitations is manual until an invitation deadline policy is agreed. Invitations do not reserve a seat. Delivery is at-least-once: a crash after provider acceptance can duplicate SMS; provider idempotency should be added in the final provider adapter.

## Backups and restore

Schedule encrypted off-host backups, for example invoke `docker compose exec -T db pg_dump -U activeland -d activeland -Fc` and stream stdout to the chosen encrypted backup storage. Keep encryption keys and backup credentials outside this repository. Define retention with the operator. Periodically restore into a separate database using `pg_restore` and verify row counts and receipts before relying on the backups. Never test restoration over the live database. Caddy certificate volumes must also be retained. Automated backup destination and restore drills remain outstanding until hosting is selected.

## API

- `GET /api/v1/catalog/`: public class/schedule availability, fees in toman.
- `GET/POST /api/v1/children/`: authenticated parent's children. POST uses `full_name`, `birth_jalali` (`YYYY/MM/DD`), optional `gender`, `attended_before`, `notes`.
- `GET/POST /api/v1/bookings/`: parent's bookings. POST uses `child_id`, `session_id`, `accept_rules: true`, optional `action: "waiting"`.

All writes require the normal Django session and CSRF cookie/header. No wildcard CORS or bearer-token bypass. Errors use 400 for invalid data, 401 for unauthenticated API calls, 404 for inaccessible objects and 409 for booking-rule conflicts. Catalog availability is advisory; capacity is enforced transactionally at reservation time.

### Optional Kavenegar implementation

If Kavenegar is selected, set `SMS_OTP_SEND_FUNCTION=portal.sms.send_otp` and `SMS_SEND_FUNCTION=portal.sms.send_message`. Supply SMS_API_KEY securely, the approved SMS_OTP_TEMPLATE for authentication and SMS_SENDER for service notifications. Verification codes use the provider's lookup template endpoint, while notifications use the sender line. This adapter is implemented but live approval/delivery has not been tested. A different provider can use the same callable interfaces.

The current build has also been validated with a local PostgreSQL dump/restore into an isolated temporary database. This is separate from provisioning encrypted off-host backups. Django's optional HSTS-preload warning is expected: submitting the production domain to a browser preload list is a later hosting decision, not enabled automatically.

Before assigning the manager, run `python manage.py setup_roles` to create the restricted group without creating any accounts or passwords.
