from datetime import timedelta
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from catalog.billing import next_month
from catalog.models import Session, Subscription
from portal.models import Child
from .models import AuditEvent, Booking, Notification, WaitingEntry


def require_operator(actor):
    if not actor.is_active or not actor.is_staff or not actor.has_perm('enrollment.change_booking'):
        raise PermissionDenied


def expire_holds(session):
    Booking.objects.filter(session=session,status='held',reserved_until__lte=timezone.now()).update(status='expired')


def active_count(session):
    now = timezone.now()
    return Subscription.objects.filter(session=session,cancelled_at__isnull=True,starts_on__lte=timezone.localdate(),expires_on__gt=timezone.localdate()).count() + Booking.objects.filter(session=session,status='held',reserved_until__gt=now).count()


def validate_child(child,session):
    if not session.active or not session.class_type.active:
        raise ValidationError('ثبت‌نام این سانس فعال نیست.')
    if not session.class_type.accepts_birth_date(child.birth_date,timezone.localdate()):
        raise ValidationError('سن کودک برای این کلاس مجاز نیست؛ با مجموعه تماس بگیرید.')

@transaction.atomic
def reserve(*,actor,child_id,session_id):
    session = Session.objects.select_for_update().select_related('class_type').get(pk=session_id)
    child = Child.objects.select_for_update().get(pk=child_id,parent=actor)
    validate_child(child,session)
    profile = getattr(actor,'parentprofile',None)
    if not profile or not profile.full_name or not profile.emergency_phone:
        raise ValidationError('ابتدا نام والد و تماس اضطراری را در اطلاعات والد تکمیل کنید.')
    expire_holds(session)
    existing = Booking.objects.filter(child=child,session=session,status='held').first()
    if existing:
        return existing
    if Subscription.objects.filter(child=child,session=session,cancelled_at__isnull=True,expires_on__gt=timezone.localdate()).exists():
        raise ValidationError('این کودک اشتراک معتبر همین سانس را دارد؛ پس از سررسید تمدید کنید.')
    if active_count(session) >= session.capacity:
        raise ValidationError('ظرفیت تکمیل است؛ می‌توانید در فهرست انتظار ثبت شوید.')
    return Booking.objects.create(child=child,session=session,amount=session.class_type.monthly_fee,reserved_until=timezone.now()+timedelta(minutes=10))

@transaction.atomic
def join_waiting(*,actor,child_id,session_id):
    session = Session.objects.select_for_update().select_related('class_type').get(pk=session_id)
    child = Child.objects.get(pk=child_id,parent=actor)
    validate_child(child,session)
    if active_count(session) < session.capacity:
        raise ValidationError('این سانس ظرفیت دارد؛ ثبت‌نام مستقیم را انتخاب کنید.')
    entry,_ = WaitingEntry.objects.get_or_create(child=child,session=session,active=True)
    return entry


def notify_opening(session):
    # A notification is an invitation, not a capacity reservation or payment.
    if active_count(session) >= session.capacity or not session.active or not session.class_type.active:
        return
    if WaitingEntry.objects.filter(session=session,active=True,notified_at__isnull=False).exists():
        return
    entry = WaitingEntry.objects.select_for_update().filter(session=session,active=True,notified_at__isnull=True).select_related('child').first()
    if entry:
        Notification.objects.get_or_create(deduplication_key=f'waiting:{entry.pk}',defaults={'recipient':entry.child.parent,'message':f'اکتیولند: در سانس {session.class_type.name} ظرفیت آزاد شده است. برای ثبت‌نام و پرداخت به حساب خود مراجعه کنید.'})
        entry.notified_at = timezone.now()
        entry.save(update_fields=['notified_at'])

@transaction.atomic
def confirm_offline(*,actor,booking_id,reference):
    require_operator(actor)
    session_id = Booking.objects.values_list('session_id',flat=True).get(pk=booking_id)
    session = Session.objects.select_for_update().select_related('class_type').get(pk=session_id)
    booking = Booking.objects.select_for_update().select_related('child').get(pk=booking_id)
    if booking.status == 'paid':
        return booking.subscription
    if booking.status != 'held' or booking.reserved_until <= timezone.now():
        raise ValidationError('رزرو منقضی یا لغو شده است؛ رزرو تازه ایجاد کنید.')
    if booking.gateway_authority:
        raise ValidationError('برای این رزرو پرداخت درگاه آغاز شده است؛ ابتدا وضعیت درگاه را پیگیری کنید.')
    if not reference.strip():
        raise ValidationError('شناسه رسید الزامی است.')
    start = timezone.localdate()
    sub = Subscription.objects.create(parent=booking.child.parent,child=booking.child,child_name=booking.child.full_name,birth_date=booking.child.birth_date,session=session,starts_on=start,expires_on=next_month(start),paid_amount=booking.amount,payment_reference=reference.strip(),recorded_by=actor)
    booking.status,booking.subscription = 'paid',sub
    booking.save(update_fields=['status','subscription'])
    WaitingEntry.objects.filter(child=booking.child,session=session,active=True).update(active=False)
    AuditEvent.objects.create(actor=actor,action='offline-payment-confirmed',booking=booking)
    Notification.objects.get_or_create(deduplication_key=f'paid:{booking.pk}',defaults={'recipient':booking.child.parent,'message':'اکتیولند: ثبت‌نام و پرداخت شما تأیید شد. رسید در پنل والدین موجود است.'})
    return sub

@transaction.atomic
def cancel(*,actor,booking_id):
    require_operator(actor)
    session_id = Booking.objects.values_list('session_id',flat=True).get(pk=booking_id)
    session = Session.objects.select_for_update().select_related('class_type').get(pk=session_id)
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status == 'cancelled':
        return
    if booking.subscription_id:
        Subscription.objects.filter(pk=booking.subscription_id).update(cancelled_at=timezone.now())
    booking.status = 'cancelled'
    booking.save(update_fields=['status'])
    AuditEvent.objects.create(actor=actor,action='cancelled-refund-needs-support',booking=booking)
    notify_opening(session)

@transaction.atomic
def start_gateway(*,actor,booking_id,callback_url):
    from .gateway import backend
    booking=Booking.objects.select_for_update().select_related('child').get(pk=booking_id,child__parent=actor)
    if booking.status!='held' or booking.reserved_until<=timezone.now():
        raise ValidationError('رزرو منقضی شده است؛ رزرو تازه ایجاد کنید.')
    gateway=backend()
    if not booking.gateway_authority:
        booking.gateway_authority=gateway.request(booking,callback_url)
        booking.save(update_fields=['gateway_authority'])
    return gateway.url(booking.gateway_authority)

@transaction.atomic
def verify_gateway(*,booking_id,authority):
    from .gateway import backend
    from .models import GatewayPayment
    session_id=Booking.objects.values_list('session_id',flat=True).get(pk=booking_id)
    session=Session.objects.select_for_update().get(pk=session_id)
    booking=Booking.objects.select_for_update().select_related('child').get(pk=booking_id)
    if not booking.gateway_authority or authority!=booking.gateway_authority:
        raise ValidationError('شناسه پرداخت نامعتبر است.')
    existing=GatewayPayment.objects.filter(booking=booking).first()
    if existing: return existing
    reference=backend().verify(booking)
    review=booking.status!='held' or booking.reserved_until<=timezone.now()
    payment=GatewayPayment.objects.create(booking=booking,reference=reference,amount=booking.amount,needs_review=review)
    booking.gateway_reference=reference
    booking.save(update_fields=['gateway_reference'])
    if not review:
        start=timezone.localdate()
        sub=Subscription.objects.create(parent=booking.child.parent,child=booking.child,child_name=booking.child.full_name,birth_date=booking.child.birth_date,session=session,starts_on=start,expires_on=next_month(start),paid_amount=booking.amount,payment_reference='gateway:'+reference,recorded_by=booking.child.parent)
        booking.subscription,booking.status=sub,'paid'
        booking.save(update_fields=['subscription','status'])
        WaitingEntry.objects.filter(child=booking.child,session=session,active=True).update(active=False)
        Notification.objects.get_or_create(deduplication_key=f'paid:{booking.pk}',defaults={'recipient':booking.child.parent,'message':'اکتیولند: پرداخت و ثبت‌نام شما تأیید شد. رسید در پنل والدین موجود است.'})
    return payment

@transaction.atomic
def transfer(*,actor,booking_id,target_id,note):
    require_operator(actor)
    source_id=Booking.objects.values_list('session_id',flat=True).get(pk=booking_id)
    locked=list(Session.objects.select_for_update().filter(pk__in=sorted({source_id,target_id})).order_by('pk'))
    target=next((row for row in locked if row.pk==target_id),None)
    if not target: raise ValidationError('سانس مقصد یافت نشد.')
    item=Booking.objects.select_for_update().select_related('child').get(pk=booking_id)
    if item.session_id!=source_id: raise ValidationError('سانس تغییر کرده است؛ دوباره تلاش کنید.')
    if target_id==source_id: return item
    if item.status!='paid' or not item.subscription.is_active_on(timezone.localdate()):
        raise ValidationError('فقط اشتراک فعال قابل انتقال است.')
    validate_child(item.child,target)
    if active_count(target)>=target.capacity: raise ValidationError('سانس مقصد ظرفیت ندارد.')
    if not note.strip(): raise ValidationError('توضیح هماهنگی تسویه با پشتیبانی الزامی است.')
    if Subscription.objects.filter(child=item.child,session=target,cancelled_at__isnull=True,expires_on__gt=timezone.localdate()).exists():
        raise ValidationError('کودک در سانس مقصد اشتراک معتبر دارد.')
    Subscription.objects.filter(pk=item.subscription_id).update(session=target)
    item.session=target
    item.save(update_fields=['session'])
    AuditEvent.objects.create(actor=actor,booking=item,action='transferred',detail=f'{source_id} -> {target_id}; {note}')
    notify_opening(next(row for row in locked if row.pk==source_id))
    return item
