import uuid
from django.conf import settings
from django.db import models

class Booking(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    child = models.ForeignKey('portal.Child',on_delete=models.PROTECT)
    session = models.ForeignKey('catalog.Session',on_delete=models.PROTECT)
    amount = models.PositiveIntegerField('مبلغ به تومان')
    created_at = models.DateTimeField(auto_now_add=True)
    reserved_until = models.DateTimeField('پایان رزرو موقت')
    status = models.CharField(max_length=12,default='held',choices=[('held','رزرو موقت'),('paid','پرداخت‌شده'),('expired','منقضی'),('cancelled','لغوشده')])
    subscription = models.OneToOneField('catalog.Subscription',on_delete=models.PROTECT,null=True,blank=True)
    gateway_authority = models.CharField(max_length=200,null=True,blank=True,unique=True)
    gateway_reference = models.CharField(max_length=200,null=True,blank=True,unique=True)
    class Meta:
        verbose_name = 'ثبت‌نام'
        verbose_name_plural = 'ثبت‌نام‌ها'
        constraints = [models.UniqueConstraint(fields=['child','session'],condition=models.Q(status='held'),name='one_hold_per_child_session')]

class WaitingEntry(models.Model):
    child = models.ForeignKey('portal.Child',on_delete=models.PROTECT)
    session = models.ForeignKey('catalog.Session',on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True,blank=True)
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ['created_at','pk']
        verbose_name = 'درخواست انتظار'
        verbose_name_plural = 'فهرست انتظار'
        constraints = [models.UniqueConstraint(fields=['child','session'],condition=models.Q(active=True),name='one_active_wait_request')]

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    message = models.TextField()
    deduplication_key = models.CharField(max_length=160,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True,blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    class Meta:
        verbose_name = 'اعلان'
        verbose_name_plural = 'اعلان‌ها'

class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    booking = models.ForeignKey(Booking,on_delete=models.PROTECT)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = 'رویداد مدیریت'
        verbose_name_plural = 'سوابق عملیات'

class GatewayPayment(models.Model):
    booking = models.OneToOneField(Booking,on_delete=models.PROTECT)
    reference = models.CharField(max_length=200,unique=True)
    amount = models.PositiveIntegerField('مبلغ به تومان')
    needs_review = models.BooleanField('نیازمند پیگیری پشتیبانی',default=False)
    verified_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = 'پرداخت درگاه'
        verbose_name_plural = 'پرداخت‌های درگاه'

class Absence(models.Model):
    subscription = models.ForeignKey('catalog.Subscription',on_delete=models.PROTECT)
    missed_on = models.DateField('تاریخ غیبت')
    makeup_on = models.DateField('تاریخ جبران',null=True,blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        verbose_name='غیبت'
        verbose_name_plural='غیبت و جبران جلسه'
        constraints=[models.UniqueConstraint(fields=['subscription','missed_on'],name='one_absence_per_date'),models.UniqueConstraint(fields=['subscription'],condition=models.Q(makeup_on__isnull=False),name='one_makeup_per_subscription')]
    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        from catalog.services import session_occurs_on
        import jdatetime
        if not self.subscription_id or not self.missed_on: return
        sub=self.subscription
        if not sub.is_active_on(self.missed_on) or not session_occurs_on(sub.session,self.missed_on):
            raise ValidationError('تاریخ غیبت باید روز برگزاری کلاس در اعتبار اشتراک باشد.')
        if self.makeup_on:
            missed=jdatetime.date.fromgregorian(date=self.missed_on)
            makeup=jdatetime.date.fromgregorian(date=self.makeup_on)
            if self.makeup_on<=self.missed_on or (missed.year,missed.month)!=(makeup.year,makeup.month):
                raise ValidationError('جبران باید بعد از غیبت و در همان ماه شمسی باشد.')
            if not sub.is_active_on(self.makeup_on) or not session_occurs_on(sub.session,self.makeup_on):
                raise ValidationError('تاریخ جبران باید روز مجاز کلاس در اعتبار اشتراک باشد.')
