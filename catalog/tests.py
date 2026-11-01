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
