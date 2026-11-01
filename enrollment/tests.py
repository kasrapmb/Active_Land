from datetime import date,timedelta
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections,connection
from django.test import Client,TestCase,TransactionTestCase,override_settings
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

class PaymentAndManagementTests(TestCase):
    def setUp(self): setup_data(self)
    def hold(self): return reserve(actor=self.parent,child_id=self.child.pk,session_id=self.session.pk)

    @patch('enrollment.gateway.backend')
    def test_verified_callback_is_idempotent(self,backend):
        from .services import start_gateway,verify_gateway
        gateway=backend.return_value
        gateway.request.return_value='authority-test'
        gateway.url.return_value='https://payment.example/test'
        gateway.verify.return_value='verified-reference'
        item=self.hold()
        url=start_gateway(actor=self.parent,booking_id=item.pk,callback_url='https://example.test/callback')
        self.assertEqual(url,'https://payment.example/test')
        with self.assertRaises(ValidationError): verify_gateway(booking_id=item.pk,authority='forged')
        first=verify_gateway(booking_id=item.pk,authority='authority-test')
        second=verify_gateway(booking_id=item.pk,authority='authority-test')
        self.assertEqual(first.pk,second.pk)
        self.assertFalse(first.needs_review)
        self.assertEqual(Subscription.objects.count(),1)
        gateway.verify.assert_called_once()

    @patch('enrollment.gateway.backend')
    def test_late_success_records_money_without_overselling(self,backend):
        from .services import verify_gateway
        from .models import GatewayPayment
        item=self.hold()
        Booking.objects.filter(pk=item.pk).update(gateway_authority='a',reserved_until=timezone.now()-timedelta(seconds=1))
        backend.return_value.verify.return_value='late-ref'
        result=verify_gateway(booking_id=item.pk,authority='a')
        self.assertTrue(result.needs_review)
        self.assertFalse(Subscription.objects.exists())
        self.assertEqual(GatewayPayment.objects.count(),1)

    def test_management_and_export_permissions(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get('/registration/management/').status_code,403)
        self.assertEqual(self.client.get('/registration/export/').status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/registration/management/').status_code,200)
        result=self.client.get('/registration/export/')
        self.assertEqual(result.status_code,200)
        self.assertTrue(result.content.startswith(b'PK'))

    def test_transfer_preserves_fee_and_expiry(self):
        from .services import transfer
        item=self.hold()
        sub=confirm_offline(actor=self.admin,booking_id=item.pk,reference='receipt-1')
        destination=Session.objects.filter(class_type__slug='candy').exclude(pk=self.session.pk).first()
        original_date=sub.expires_on
        transfer(actor=self.admin,booking_id=item.pk,target_id=destination.pk,note='اختلاف شهریه توسط پشتیبانی بررسی شد')
        sub.refresh_from_db()
        self.assertEqual(sub.session,destination)
        self.assertEqual(sub.expires_on,original_date)
        self.assertEqual(sub.paid_amount,1850000)

    @override_settings(PAYMENT_BACKEND='')
    def test_disabled_gateway_never_claims_payment_success(self):
        item=self.hold()
        self.client.force_login(self.parent)
        self.assertEqual(self.client.post(f'/registration/{item.pk}/pay/').status_code,302)
        self.assertFalse(Subscription.objects.exists())

class AbsenceTests(TestCase):
    def test_makeup_must_be_in_same_persian_month_and_not_a_holiday(self):
        from .models import Absence
        from catalog.models import OfficialHoliday
        import jdatetime
        setup_data(self)
        item=reserve(actor=self.parent,child_id=self.child.pk,session_id=self.session.pk)
        sub=confirm_offline(actor=self.admin,booking_id=item.pk,reference='absence-receipt')
        # Fixed dates provide two Saturdays in the same Persian month.
        sub.starts_on=date(2026,1,1);sub.expires_on=date(2026,2,1);sub.save()
        row=Absence(subscription=sub,recorded_by=self.admin,missed_on=date(2026,1,3),makeup_on=date(2026,1,10))
        row.full_clean();row.save()
        second=Absence(subscription=sub,recorded_by=self.admin,missed_on=date(2026,1,10),makeup_on=date(2026,1,17))
        with self.assertRaises(ValidationError): second.full_clean()
        OfficialHoliday.objects.create(day=date(2026,1,10),title='تعطیلی رسمی')
        with self.assertRaises(ValidationError): row.full_clean()

    def test_center_manager_cannot_manage_user_permissions(self):
        from django.contrib.auth.models import Group
        call_command('setup_roles')
        user=get_user_model().objects.create_user('manager',is_staff=True)
        user.groups.add(Group.objects.get(name='مدیر مجموعه اکتیولند'))
        self.assertTrue(user.has_perm('enrollment.change_booking'))
        self.assertFalse(user.has_perm('auth.change_user'))
        self.assertFalse(user.has_perm('auth.change_permission'))

class ManualAgeExceptionTests(TestCase):
    def test_only_site_admin_can_record_out_of_range_child_with_reason(self):
        from catalog.services import record_paid_month
        from django.contrib.auth.models import Group
        setup_data(self)
        call_command('setup_roles')
        manager=get_user_model().objects.create_user('manager',is_staff=True)
        manager.groups.add(Group.objects.get(name='مدیر مجموعه اکتیولند'))
        args=dict(parent=self.parent,child_name='کودک استثنا',birth_date=date(2020,1,1),session_id=self.session.pk,payment_reference='manual-exception')
        with self.assertRaises(ValidationError): record_paid_month(**args,recorded_by=manager,age_override_reason='هماهنگ شده')
        with self.assertRaises(ValidationError): record_paid_month(**args,recorded_by=self.admin)
        item=record_paid_month(**args,recorded_by=self.admin,age_override_reason='تأیید تلفنی توسط مدیر سایت')
        self.assertEqual(item.age_override_reason,'تأیید تلفنی توسط مدیر سایت')
        self.assertEqual(item.parent,self.parent)
        self.assertIsNotNone(item.child_id)
