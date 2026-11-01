from datetime import date,timedelta
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections,connection
from django.test import Client,TestCase,TransactionTestCase
from django.utils import timezone
from catalog.models import ClassType,Session,Subscription
from portal.models import Child,ParentProfile
from .models import Booking,Notification,WaitingEntry
from .services import cancel,confirm_offline,join_waiting,reserve

def setup_data(obj):
    call_command('seed_catalog',verbosity=0)
    User=get_user_model()
    obj.parent=User.objects.create_user('parent:test')
    obj.other=User.objects.create_user('other')
    obj.admin=User.objects.create_superuser('admin',password='test-only')
    ParentProfile.objects.create(user=obj.parent,phone='09123456789',full_name='والد',emergency_phone='09123456780')
    today=timezone.localdate()
    obj.child=Child.objects.create(parent=obj.parent,full_name='کودک',birth_date=today.replace(year=today.year-1)-timedelta(days=90))
    obj.session=Session.objects.filter(class_type__slug='candy').first()
    obj.session.capacity=1
    obj.session.save()

class BookingTests(TestCase):
    def setUp(self): setup_data(self)
    def hold(self): return reserve(actor=self.parent,child_id=self.child.pk,session_id=self.session.pk)

    def test_hold_idempotency_and_capacity(self):
        hold=self.hold()
        self.assertEqual(self.hold().pk,hold.pk)
        child=Child.objects.create(parent=self.parent,full_name='دوم',birth_date=self.child.birth_date)
        with self.assertRaises(ValidationError): reserve(actor=self.parent,child_id=child.pk,session_id=self.session.pk)
        Booking.objects.filter(pk=hold.pk).update(reserved_until=timezone.now()-timedelta(seconds=1))
        new=reserve(actor=self.parent,child_id=child.pk,session_id=self.session.pk)
        hold.refresh_from_db()
        self.assertEqual(hold.status,'expired')
        self.assertEqual(new.status,'held')

    def test_ownership_and_age_enforced(self):
        with self.assertRaises(Child.DoesNotExist): reserve(actor=self.other,child_id=self.child.pk,session_id=self.session.pk)
        self.child.birth_date=date(2020,1,1);self.child.save()
        with self.assertRaises(ValidationError): self.hold()

    def test_offline_payment_is_once_and_fee_snapshot(self):
        item=self.hold()
        course=self.session.class_type
        course.monthly_fee=2000000;course.save()
        sub=confirm_offline(actor=self.admin,booking_id=item.pk,reference='receipt-1')
        self.assertEqual(sub.paid_amount,1850000)
        self.assertEqual(confirm_offline(actor=self.admin,booking_id=item.pk,reference='receipt-1').pk,sub.pk)
        self.assertEqual(Subscription.objects.count(),1)
        self.assertEqual(Notification.objects.count(),1)
        self.client.force_login(self.parent)
        self.assertContains(self.client.get(f'/account/receipts/{sub.pk}/'),'۱٬۸۵۰٬۰۰۰')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f'/account/receipts/{sub.pk}/').status_code,404)
        self.assertEqual(self.client.get(f'/registration/{item.pk}/').status_code,404)

    def test_expired_or_nonstaff_cannot_confirm(self):
        from django.core.exceptions import PermissionDenied
        item=self.hold()
        with self.assertRaises(PermissionDenied): confirm_offline(actor=self.parent,booking_id=item.pk,reference='a')
        Booking.objects.filter(pk=item.pk).update(reserved_until=timezone.now()-timedelta(seconds=1))
        with self.assertRaises(ValidationError): confirm_offline(actor=self.admin,booking_id=item.pk,reference='a')

    def test_cancel_queues_only_first_waiter(self):
        item=self.hold()
        confirm_offline(actor=self.admin,booking_id=item.pk,reference='receipt-1')
        child=Child.objects.create(parent=self.parent,full_name='انتظار',birth_date=self.child.birth_date)
        wait=join_waiting(actor=self.parent,child_id=child.pk,session_id=self.session.pk)
        self.assertEqual(join_waiting(actor=self.parent,child_id=child.pk,session_id=self.session.pk).pk,wait.pk)
        cancel(actor=self.admin,booking_id=item.pk)
        call_command('process_enrollments',verbosity=0)
        self.assertEqual(Notification.objects.filter(deduplication_key=f'waiting:{wait.pk}').count(),1)
        self.assertIsNotNone(WaitingEntry.objects.get(pk=wait.pk).notified_at)
        item.refresh_from_db()
        self.assertFalse(item.subscription.is_active_on(timezone.localdate()))

    def test_api_auth_csrf_and_invalid_input(self):
        self.assertEqual(self.client.get('/api/v1/children/').status_code,401)
        self.client.force_login(self.parent)
        self.assertEqual(self.client.post('/api/v1/bookings/',data='[]',content_type='application/json').status_code,400)
        self.assertEqual(self.client.get('/api/v1/catalog/').status_code,200)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.parent)
        self.assertEqual(csrf.post('/api/v1/bookings/',data='{}',content_type='application/json').status_code,403)

class PostgreSQLCapacityTests(TransactionTestCase):
    def test_last_seat_cannot_be_sold_twice(self):
        if connection.vendor!='postgresql': self.skipTest('Requires PostgreSQL row locks')
        setup_data(self)
        second=Child.objects.create(parent=self.parent,full_name='دوم',birth_date=self.child.birth_date)
        from threading import Barrier
        barrier=Barrier(2)
        def attempt(child_id):
            close_old_connections()
            try:
                parent=get_user_model().objects.get(pk=self.parent.pk)
                barrier.wait(timeout=10)
                try:
                    reserve(actor=parent,child_id=child_id,session_id=self.session.pk)
                    return 'held'
                except ValidationError: return 'full'
            finally: close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(attempt,[self.child.pk,second.pk]))
        self.assertCountEqual(result,['held','full'])
        self.assertEqual(Booking.objects.filter(status='held').count(),1)
