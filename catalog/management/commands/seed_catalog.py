from datetime import time
from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import ClassType, Session

class Command(BaseCommand):
    help = 'Add missing initial classes and sessions without overwriting manager edits.'
    @transaction.atomic
    def handle(self, *args, **options):
        rows = [
            ('candy','نقل و نبات',12,24,60,1850000,'pink','🍬','اولین کشف‌های کوچولو، با بازی و همراهی شما.',[(0,19,20),(4,18,19)]),
            ('honey','قند و عسل',24,36,60,1850000,'yellow','🍯','فرصتی شیرین برای بازی، تجربه و کشف دنیای اطراف.',[(2,16,17),(3,16,17)]),
            ('heart','دردونه',36,48,60,1850000,'lavender','💗','بازی‌های تازه و تجربه‌های مشترک برای دنیای کودک شما.',[(0,18,19)]),
            ('sprout','جوونه',36,48,90,2400000,'sage','🌱','آمادگی استقلال کودک با فعالیت‌های شناختی و تقویت تمرکز.',[(2,17,18.5)]),
        ]
        for position,(slug,name,low,high,duration,fee,theme,icon,description,slots) in enumerate(rows):
            course, created = ClassType.objects.get_or_create(slug=slug, defaults=dict(name=name,min_age_months=low,max_age_months=high,duration_minutes=duration,monthly_fee=fee,theme=theme,icon=icon,description=description,position=position))
            if created:
                for day,start,end in slots:
                    Session.objects.create(class_type=course,weekday=day,start_time=time(start),end_time=time(int(end),30 if end%1 else 0),capacity=15)
        self.stdout.write(self.style.SUCCESS('Initial catalog available; existing records preserved.'))
