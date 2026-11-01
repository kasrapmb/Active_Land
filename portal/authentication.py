import hashlib
import re
import secrets
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from .models import LoginChallenge, LoginRate, ParentProfile

class DeliveryUnavailable(Exception):
    pass

def normalize_phone(value):
    value = str(value).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789')).strip().replace(' ','')
    if value.startswith('+98'):
        value = '0' + value[3:]
    if not re.fullmatch(r'09\d{9}',value):
        raise ValidationError('شماره همراه را با ۰۹ و در ۱۱ رقم وارد کنید.')
    return value

@transaction.atomic
def consume_rate(key, limit=10):
    now = timezone.now()
    digest = hashlib.sha256(key.encode()).hexdigest()
    rate, _ = LoginRate.objects.get_or_create(key=digest,defaults={'window_start':now})
    rate = LoginRate.objects.select_for_update().get(pk=rate.pk)
    if rate.window_start <= now - timedelta(hours=1):
        rate.window_start, rate.count = now, 0
    if rate.count >= limit:
        return False
    rate.count += 1
    rate.save()
    return True

def deliver_code(phone, code):
    otp_backend = getattr(settings,'SMS_OTP_SEND_FUNCTION','')
    backend = getattr(settings,'SMS_SEND_FUNCTION','')
    if otp_backend:
        import_string(otp_backend)(phone,code)
    elif backend:
        import_string(backend)(phone, f'کد ورود اکتیولند: {code}')
    elif settings.DEBUG and getattr(settings,'LOCAL_SMS_ENABLED',False):
        # Explicit local-only inbox, never an HTTP response or public log.
        root = settings.BASE_DIR / '.local-sms'
        root.mkdir(mode=0o700,exist_ok=True)
        path = root / f'{phone}.txt'
        import os
        fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as handle:
            handle.write(code)
    else:
        raise DeliveryUnavailable('سرویس پیامک هنوز پیکربندی نشده است.')

def request_code(phone, ip):
    phone = normalize_phone(phone)
    if not consume_rate('phone:'+phone,5) or not consume_rate('ip:'+ip,30):
        raise ValidationError('تعداد درخواست‌ها زیاد است؛ یک ساعت دیگر تلاش کنید.')
    with transaction.atomic():
        now = timezone.now()
        challenge, _ = LoginChallenge.objects.get_or_create(phone=phone,defaults={'code_hash':'','expires_at':now,'sent_at':now-timedelta(minutes=2)})
        challenge = LoginChallenge.objects.select_for_update().get(pk=challenge.pk)
        if challenge.sent_at > now-timedelta(seconds=60):
            raise ValidationError('برای ارسال دوباره یک دقیقه صبر کنید.')
        code = f'{secrets.randbelow(1000000):06d}'
        challenge.code_hash = make_password(code)
        challenge.sent_at, challenge.expires_at = now, now+timedelta(minutes=3)
        challenge.used, challenge.attempts = False, 0
        challenge.save()
        deliver_code(phone,code)
    return phone

@transaction.atomic
def verify_code(phone, code):
    phone = normalize_phone(phone)
    challenge = LoginChallenge.objects.select_for_update().filter(phone=phone).first()
    if not challenge or challenge.used or challenge.expires_at <= timezone.now() or challenge.attempts >= 5:
        return None
    challenge.attempts += 1
    code = str(code).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹','0123456789'))
    if not check_password(code,challenge.code_hash):
        challenge.save(update_fields=['attempts'])
        return None
    challenge.used = True
    challenge.save(update_fields=['attempts','used'])
    User = get_user_model()
    user, created = User.objects.get_or_create(username='parent:'+phone)
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
    if not user.is_active:
        return None
    ParentProfile.objects.get_or_create(user=user,defaults={'phone':phone})
    return user
