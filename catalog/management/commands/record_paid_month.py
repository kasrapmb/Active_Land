from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from catalog.billing import persian_date
from catalog.services import record_paid_month

class Command(BaseCommand):
    help = 'Record one verified offline full-fee payment, using an authorized staff account.'
    def add_arguments(self, parser):
        parser.add_argument('--parent', required=True)
        parser.add_argument('--staff', required=True)
        parser.add_argument('--child', required=True)
        parser.add_argument('--birth-date', required=True, help='Gregorian YYYY-MM-DD')
        parser.add_argument('--session', required=True, type=int)
        parser.add_argument('--reference', required=True)

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            parent = User.objects.get(username=options['parent'])
            staff = User.objects.get(username=options['staff'],is_staff=True,is_active=True)
            subscription = record_paid_month(parent=parent,recorded_by=staff,child_name=options['child'],birth_date=date.fromisoformat(options['birth_date']),session_id=options['session'],payment_reference=options['reference'])
        except (User.DoesNotExist,ValueError,ValidationError,PermissionError,IntegrityError) as exc:
            raise CommandError('ثبت انجام نشد؛ حساب‌ها، سن، ظرفیت و یکتایی رسید را بررسی کنید.') from exc
        self.stdout.write(self.style.SUCCESS(f'اشتراک {subscription.pk} ثبت شد؛ سررسید: {persian_date(subscription.expires_on)}'))
