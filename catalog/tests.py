from datetime import date
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from .models import ClassType, Session

class CatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_catalog', verbosity=0)

    def test_catalog_matches_poster(self):
        self.assertEqual(ClassType.objects.count(), 4)
        self.assertEqual(Session.objects.count(), 6)
        self.assertEqual(set(Session.objects.values_list('capacity',flat=True)), {15})
        sprout = ClassType.objects.get(slug='sprout')
        self.assertEqual(sprout.monthly_fee, 2400000)
        self.assertEqual(str(sprout.sessions.get().end_time), '18:30:00')

    def test_age_is_checked_on_registration_date(self):
        candy = ClassType.objects.get(slug='candy')
        honey = ClassType.objects.get(slug='honey')
        born = date(2024, 1, 20)
        self.assertFalse(candy.accepts_birth_date(born, date(2025,1,19)))
        self.assertTrue(candy.accepts_birth_date(born, date(2025,1,20)))
        self.assertTrue(candy.accepts_birth_date(born, date(2026,1,19)))
        self.assertFalse(candy.accepts_birth_date(born, date(2026,1,20)))
        self.assertTrue(honey.accepts_birth_date(born, date(2026,1,20)))

    def test_leap_day_birthday(self):
        candy = ClassType.objects.get(slug='candy')
        self.assertTrue(candy.accepts_birth_date(date(2024,2,29), date(2025,2,28)))

    def test_seed_preserves_manager_edits_and_deleted_sessions(self):
        item = ClassType.objects.get(slug='candy')
        item.monthly_fee = 2000000
        item.save()
        item.sessions.all().delete()
        call_command('seed_catalog', verbosity=0)
        item.refresh_from_db()
        self.assertEqual(item.monthly_fee, 2000000)
        self.assertEqual(item.sessions.count(),0)

    def test_home_uses_database_and_hides_inactive_content(self):
        item = ClassType.objects.get(slug='candy')
        item.name = 'نام ویرایش‌شده'
        item.save()
        response = self.client.get('/')
        self.assertContains(response, 'نام ویرایش‌شده')
        self.assertContains(response, '۱٬۸۵۰٬۰۰۰')
        item.active = False
        item.save()
        self.assertNotContains(self.client.get('/'), 'نام ویرایش‌شده')

    def test_admin_requires_login_and_permissions(self):
        self.assertEqual(self.client.get('/admin/catalog/classtype/').status_code,302)
        user = get_user_model().objects.create_user(username='parent', password='test-only-password')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/admin/catalog/classtype/').status_code,302)

class MonthlyBillingTests(TestCase):
    def test_same_persian_day_next_month(self):
        import jdatetime
        from .billing import next_month
        start = jdatetime.date(1405,8,24).togregorian()
        self.assertEqual(next_month(start), jdatetime.date(1405,9,24).togregorian())

    def test_short_month_and_year_rollover(self):
        import jdatetime
        from .billing import next_month
        self.assertEqual(next_month(jdatetime.date(1405,6,31).togregorian()), jdatetime.date(1405,7,30).togregorian())
        self.assertEqual(next_month(jdatetime.date(1405,12,24).togregorian()), jdatetime.date(1406,1,24).togregorian())
        result = jdatetime.date.fromgregorian(date=next_month(jdatetime.date(1405,11,30).togregorian()))
        self.assertEqual((result.year,result.month,result.day),(1405,12,29))

    def test_paid_month_dates_capacity_and_permission(self):
        from unittest.mock import patch
        from .services import record_paid_month
        from .models import Subscription
        from django.core.exceptions import ValidationError
        call_command('seed_catalog', verbosity=0)
        admin = get_user_model().objects.create_superuser(username='admin',password='test-only')
        parent = get_user_model().objects.create_user(username='parent')
        session = Session.objects.filter(class_type__slug='candy').first()
        session.capacity = 1
        session.save()
        args = dict(parent=parent,child_name='کودک',birth_date=date(2024,6,1),session_id=session.pk,payment_reference='receipt-1',recorded_by=admin)
        with patch('catalog.services.timezone.localdate',return_value=date(2026,1,1)):
            with self.assertRaises(PermissionError):
                record_paid_month(**{**args,'recorded_by':parent})
            sub = record_paid_month(**args)
            self.assertTrue(sub.is_active_on(sub.starts_on))
            self.assertFalse(sub.is_active_on(sub.expires_on))
            self.assertEqual(sub.paid_amount,1850000)
            with self.assertRaises(ValidationError):
                record_paid_month(**{**args,'payment_reference':'receipt-2'})
        self.assertEqual(Subscription.objects.count(),1)

    def test_only_scheduled_days_except_official_holidays(self):
        from .services import session_occurs_on
        from .models import OfficialHoliday
        call_command('seed_catalog', verbosity=0)
        session = Session.objects.get(class_type__slug='candy',weekday=0)
        saturday = date(2026,1,3)
        self.assertTrue(session_occurs_on(session,saturday))
        self.assertFalse(session_occurs_on(session,date(2026,1,4)))
        OfficialHoliday.objects.create(day=saturday,title='تعطیلی رسمی')
        self.assertFalse(session_occurs_on(session,saturday))
