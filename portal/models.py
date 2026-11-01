from django.conf import settings
from django.db import models

class ParentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField('شماره همراه', max_length=11, unique=True)
    full_name = models.CharField('نام و نام خانوادگی والد', max_length=150, blank=True)
    emergency_phone = models.CharField('تماس اضطراری', max_length=11, blank=True)
    class Meta:
        verbose_name = 'والد'
        verbose_name_plural = 'والدین'
    def __str__(self):
        return self.full_name or self.phone

class Child(models.Model):
    parent = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='children')
    full_name = models.CharField('نام و نام خانوادگی کودک',max_length=150)
    birth_date = models.DateField('تاریخ تولد')
    gender = models.CharField('جنسیت (اختیاری)',max_length=10,blank=True,choices=[('girl','دختر'),('boy','پسر')])
    attended_before = models.BooleanField('سابقه حضور در اکتیولند',default=False)
    notes = models.TextField('نکات ضروری برای مربی (اختیاری)',blank=True,max_length=2000)
    class Meta:
        verbose_name = 'کودک'
        verbose_name_plural = 'کودکان'
    def __str__(self):
        return self.full_name

    @property
    def age_months(self):
        from django.utils import timezone
        today=timezone.localdate()
        return (today.year-self.birth_date.year)*12+today.month-self.birth_date.month-(today.day<self.birth_date.day)

class LoginChallenge(models.Model):
    phone = models.CharField(max_length=11,unique=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)

class LoginRate(models.Model):
    key = models.CharField(max_length=64,unique=True)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
