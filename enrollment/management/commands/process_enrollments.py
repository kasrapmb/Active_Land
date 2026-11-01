from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from catalog.models import Session,Subscription
from enrollment.models import Notification
from enrollment.services import expire_holds,notify_opening

class Command(BaseCommand):
    help='Expire holds, queue waiting invitations and renewal reminders; deliver through configured SMS backend.'
    def handle(self,*args,**options):
        for pk in Session.objects.values_list('pk',flat=True).iterator():
            with transaction.atomic():
                session=Session.objects.select_for_update().select_related('class_type').get(pk=pk)
                expire_holds(session)
                notify_opening(session)
        for sub in Subscription.objects.filter(cancelled_at__isnull=True,expires_on=timezone.localdate()+timedelta(days=2)):
            Notification.objects.get_or_create(deduplication_key=f'renewal:{sub.pk}',defaults={'recipient':sub.parent,'message':'اکتیولند: دو روز تا سررسید اشتراک فرزندتان باقی مانده است. برای تمدید با مجموعه هماهنگ کنید.'})
        if not settings.SMS_SEND_FUNCTION:
            self.stdout.write('SMS provider is not configured; notifications remain queued.')
            return
        send=import_string(settings.SMS_SEND_FUNCTION)
        for pk in Notification.objects.filter(sent_at__isnull=True,attempts__lt=5).values_list('pk',flat=True).iterator():
            with transaction.atomic():
                item=Notification.objects.select_for_update().select_related('recipient').get(pk=pk)
                if item.sent_at: continue
                item.attempts+=1
                item.save(update_fields=['attempts'])
                profile=getattr(item.recipient,'parentprofile',None)
                if not profile: continue
                try: send(profile.phone,item.message)
                except Exception: continue
                item.sent_at=timezone.now()
                item.save(update_fields=['sent_at'])
        self.stdout.write('Enrollment maintenance complete.')
