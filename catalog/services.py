from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .billing import next_month
from .models import OfficialHoliday, Session, Subscription


@transaction.atomic
def record_paid_month(*, parent, child_name, birth_date, session_id, payment_reference, recorded_by):
    """Staff-only recording of a verified offline payment, never a gateway callback."""
    if not recorded_by.has_perm('catalog.add_subscription'):
        raise PermissionError('Subscription recording requires staff permission.')
    session = Session.objects.select_for_update().select_related('class_type').get(pk=session_id)
    start = timezone.localdate()
    if not session.active or not session.class_type.active:
        raise ValidationError('ثبت‌نام این سانس فعال نیست.')
    if not session.class_type.accepts_birth_date(birth_date, start):
        raise ValidationError('سن کودک خارج از محدوده است؛ ثبت استثنا نیازمند هماهنگی جداگانه است.')
    from enrollment.services import active_count
    if active_count(session) >= session.capacity:
        raise ValidationError('ظرفیت سانس تکمیل است.')
    if not child_name.strip() or not payment_reference.strip():
        raise ValidationError('نام کودک و شناسه پرداخت الزامی است.')
    return Subscription.objects.create(parent=parent,child_name=child_name.strip(),birth_date=birth_date,session=session,starts_on=start,expires_on=next_month(start),paid_amount=session.class_type.monthly_fee,payment_reference=payment_reference.strip(),recorded_by=recorded_by)


def session_occurs_on(session, day):
    # Python Monday=0; the catalog uses Saturday=0.
    return session.active and session.class_type.active and (day.weekday() + 2) % 7 == session.weekday and not OfficialHoliday.objects.filter(day=day).exists()
