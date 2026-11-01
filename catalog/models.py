from django.core.exceptions import ValidationError
from django.db import models


class ClassType(models.Model):
    slug = models.SlugField('شناسه', unique=True)
    name = models.CharField('نام کلاس', max_length=100)
    description = models.TextField('معرفی')
    min_age_months = models.PositiveSmallIntegerField('حداقل سن به ماه')
    max_age_months = models.PositiveSmallIntegerField('حد بالای سن به ماه')
    duration_minutes = models.PositiveSmallIntegerField('مدت جلسه به دقیقه', default=60)
    monthly_fee = models.PositiveIntegerField('شهریه ماهانه به تومان')
    theme = models.CharField('رنگ کارت', max_length=15, choices=[(x,x) for x in ['pink','yellow','lavender','sage']])
    icon = models.CharField('نماد', max_length=10, default='🌈')
    position = models.PositiveSmallIntegerField('ترتیب نمایش', default=0)
    active = models.BooleanField('فعال', default=True)

    class Meta:
        ordering = ['position', 'pk']
        verbose_name = 'کلاس'
        verbose_name_plural = 'کلاس‌ها'
        constraints = [
            models.CheckConstraint(condition=models.Q(max_age_months__gt=models.F('min_age_months')), name='valid_age_range'),
            models.CheckConstraint(condition=models.Q(duration_minutes__gt=0), name='positive_duration'),
            models.CheckConstraint(condition=models.Q(monthly_fee__gt=0), name='positive_fee'),
        ]

    def __str__(self):
        return self.name

    def accepts_birth_date(self, birth_date, registration_date):
        # Compare dates directly so age boundaries follow the child's actual birthday.
        from calendar import monthrange
        def anniversary(months):
            year, month = divmod(birth_date.year * 12 + birth_date.month - 1 + months, 12)
            month += 1
            return birth_date.replace(year=year, month=month, day=min(birth_date.day, monthrange(year, month)[1]))
        return anniversary(self.min_age_months) <= registration_date < anniversary(self.max_age_months)


class Session(models.Model):
    DAYS = [(0,'شنبه'),(1,'یکشنبه'),(2,'دوشنبه'),(3,'سه‌شنبه'),(4,'چهارشنبه'),(5,'پنجشنبه'),(6,'جمعه')]
    class_type = models.ForeignKey(ClassType, on_delete=models.PROTECT, related_name='sessions', verbose_name='کلاس')
    weekday = models.PositiveSmallIntegerField('روز', choices=DAYS)
    start_time = models.TimeField('ساعت شروع')
    end_time = models.TimeField('ساعت پایان')
    capacity = models.PositiveSmallIntegerField('ظرفیت', default=15)
    active = models.BooleanField('فعال', default=True)

    class Meta:
        ordering = ['weekday','start_time']
        verbose_name = 'سانس'
        verbose_name_plural = 'سانس‌ها'
        constraints = [
            models.CheckConstraint(condition=models.Q(capacity__gt=0), name='positive_capacity'),
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F('start_time')), name='valid_session_time'),
            models.CheckConstraint(condition=models.Q(weekday__lte=6), name='valid_weekday'),
            models.UniqueConstraint(fields=['class_type','weekday','start_time'], name='unique_class_session'),
        ]

    def __str__(self):
        return f'{self.class_type} — {self.get_weekday_display()} {self.start_time:%H:%M}'

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'ساعت پایان باید بعد از شروع باشد.'})
