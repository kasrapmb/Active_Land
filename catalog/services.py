from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .billing import next_month
from .models import OfficialHoliday, Session, Subscription


@transaction.atomic
def record_paid_month(*, parent, child_name, birth_date, session_id, payment_reference, recorded_by, age_override_reason=""):
    """Staff-only recording of a verified offline payment, never a gateway callback."""
    if not recorded_by.is_active or not recorded_by.is_staff or not recorded_by.has_perm('enrollment.change_booking'):
        raise PermissionError('Subscription recording requires staff permission.')
    session = Session.objects.select_for_update().select_related('class_type').get(pk=session_id)
    start = timezone.localdate()
    if not session.active or not session.class_type.active:
        raise ValidationError('ثبت‌نام این سانس فعال نیست.')
    if not session.class_type.accepts_birth_date(birth_date, start) and not (recorded_by.is_superuser and age_override_reason.strip()):
        raise ValidationError('سن کودک خارج از محدوده است؛ ثبت استثنا نیازمند هماهنگی جداگانه است.')
    from enrollment.services import active_count
    if active_count(session) >= session.capacity:
        raise ValidationError('ظرفیت سانس تکمیل است.')
    if not child_name.strip() or not payment_reference.strip():
        raise ValidationError('نام کودک و شناسه پرداخت الزامی است.')
    from portal.models import Child
    child,_ = Child.objects.get_or_create(parent=parent,full_name=child_name.strip(),birth_date=birth_date)
    if Subscription.objects.filter(child=child,session=session,cancelled_at__isnull=True,expires_on__gt=start).exists():
        raise ValidationError('این کودک در همین سانس اشتراک معتبر دارد.')
    subscription = Subscription.objects.create(child=child,age_override_reason=age_override_reason.strip(),parent=parent,child_name=child_name.strip(),birth_date=birth_date,session=session,starts_on=start,expires_on=next_month(start),paid_amount=session.class_type.monthly_fee,payment_reference=payment_reference.strip(),recorded_by=recorded_by)
    from enrollment.models import Notification, WaitingEntry
    WaitingEntry.objects.filter(child=child,session=session,active=True).update(active=False)
    Notification.objects.get_or_create(deduplication_key=f'manual-paid:{subscription.pk}',defaults={'recipient':parent,'message':'اکتیولند: ثبت‌نام و پرداخت حضوری شما ثبت شد. رسید در پنل والدین موجود است.'})
    return subscription


def session_occurs_on(session, day):
    # Python Monday=0; the catalog uses Saturday=0.
    return session.active and session.class_type.active and (day.weekday() + 2) % 7 == session.weekday and not OfficialHoliday.objects.filter(day=day).exists()
