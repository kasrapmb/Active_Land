from datetime import date, timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from catalog.models import OfficialHoliday, Session, Subscription
from portal.models import Child, ParentProfile
from .models import Absence, Attendance
from .roster import billing_status, lesson_summary
from .services import record_attendance

TODAY = date(2026, 11, 2)

class ManagementWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_catalog', verbosity=0)
        call_command('setup_roles', verbosity=0)
        User = get_user_model()
        cls.manager = User.objects.create_user('manager', is_staff=True)
        cls.manager.groups.add(Group.objects.get(name='مدیر مجموعه اکتیولند'))
        cls.parent = User.objects.create_user('parent')
        cls.other = User.objects.create_user('other')
        ParentProfile.objects.create(user=cls.parent, phone='09123456789', full_name='والد آزمون', emergency_phone='09123456780')
        cls.child = Child.objects.create(parent=cls.parent, full_name='کودک آزمون', birth_date=date(2025, 3, 1), notes='حساسیت غذایی')
        cls.slot = Session.objects.filter(class_type__slug='candy', weekday=0).get()
        cls.subscription = Subscription.objects.create(child=cls.child, parent=cls.parent, child_name=cls.child.full_name, birth_date=cls.child.birth_date, session=cls.slot, starts_on=date(2026, 10, 24), expires_on=date(2026, 11, 24), paid_amount=1850000, payment_reference='management-receipt', recorded_by=cls.manager)

    def setUp(self):
        self.clock = patch('django.utils.timezone.localdate', return_value=TODAY)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.client.force_login(self.manager)

    def test_manager_can_navigate_class_session_and_child(self):
        home = self.client.get(reverse('management'))
        self.assertContains(home, reverse('management-class', args=[self.slot.class_type_id]))
        course = self.client.get(reverse('management-class', args=[self.slot.class_type_id]))
        self.assertContains(course, reverse('management-session', args=[self.slot.pk]))
        roster = self.client.get(reverse('management-session', args=[self.slot.pk]))
        self.assertContains(roster, 'کودک آزمون')
        self.assertContains(roster, '۱۴۰۵/۰۹/۰۳')
        self.assertEqual(roster.context['summary']['active'], 1)
        self.assertEqual(roster.context['rows'][0]['lessons']['planned'], 5)
        child = self.client.get(reverse('management-child', args=[self.child.pk]))
        self.assertContains(child, 'حساسیت غذایی')
        self.assertContains(child, 'والد آزمون')

    def test_parent_cannot_read_roster_or_other_child(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse('management-session', args=[self.slot.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('management-child', args=[self.child.pk])).status_code, 403)
        self.assertContains(self.client.get(reverse('child-detail', args=[self.child.pk])), 'حساسیت غذایی')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('child-detail', args=[self.child.pk])).status_code, 404)

    def test_presence_absence_correction_is_idempotent(self):
        args = dict(actor=self.manager, subscription_id=self.subscription.pk, day=date(2026, 10, 31))
        record_attendance(**args, status='present')
        record_attendance(**args, status='present')
        self.assertEqual(Attendance.objects.count(), 1)
        record_attendance(**args, status='absent')
        self.assertFalse(Attendance.objects.exists())
        self.assertEqual(Absence.objects.count(), 1)
        record_attendance(**args, status='clear')
        self.assertFalse(Absence.objects.exists())

    def test_future_holiday_wrong_day_and_parent_are_rejected(self):
        for day in (date(2026, 11, 7), date(2026, 11, 1), date(2026, 10, 17)):
            with self.assertRaises(ValidationError):
                record_attendance(actor=self.manager, subscription_id=self.subscription.pk, day=day, status='present')
        OfficialHoliday.objects.create(day=date(2026, 10, 31), title='تعطیل رسمی')
        with self.assertRaises(ValidationError):
            record_attendance(actor=self.manager, subscription_id=self.subscription.pk, day=date(2026, 10, 31), status='present')
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            record_attendance(actor=self.parent, subscription_id=self.subscription.pk, day=date(2026, 10, 24), status='present')

    def test_lesson_counts_do_not_invent_attendance_and_exclude_holidays(self):
        summary = lesson_summary(self.subscription, today=TODAY)
        self.assertEqual(summary['planned'], 5)
        self.assertEqual(summary['present'], 0)
        self.assertEqual(summary['unrecorded'], 2)
        self.assertEqual(summary['remaining'], 3)
        OfficialHoliday.objects.create(day=date(2026, 11, 7), title='تعطیل رسمی')
        self.assertEqual(lesson_summary(self.subscription, today=TODAY)['planned'], 4)

    def test_renewed_and_cancelled_old_periods_do_not_create_false_dues(self):
        Subscription.objects.create(child=self.child, parent=self.parent, child_name=self.child.full_name, birth_date=self.child.birth_date, session=self.slot, starts_on=date(2026, 9, 24), expires_on=date(2026, 10, 24), paid_amount=1850000, payment_reference='older-month', recorded_by=self.manager)
        response = self.client.get(reverse('management-session', args=[self.slot.pk]), {'status': 'due'})
        self.assertEqual(len(response.context['rows']), 0)
        Subscription.objects.filter(pk=self.subscription.pk).update(cancelled_at=timezone.now())
        response = self.client.get(reverse('management-session', args=[self.slot.pk]), {'status': 'all'})
        self.assertEqual(len(response.context['rows']), 0)
        self.assertEqual(response.context['summary']['due'], 0)

    def test_attendance_post_and_search(self):
        response = self.client.post(reverse('management-attendance', args=[self.subscription.pk]), {'day': '۱۴۰۵/۰۸/۰۹', 'status': 'present', 'return_status': 'all', 'return_q': 'کودک'})
        self.assertEqual(response.status_code, 302)
        from urllib.parse import parse_qs, urlparse
        query = parse_qs(urlparse(response.url).query)
        self.assertEqual(query['status'], ['all'])
        self.assertEqual(query['q'], ['کودک'])
        self.assertTrue(Attendance.objects.filter(day=date(2026, 10, 31)).exists())
        roster = self.client.get(reverse('management-session', args=[self.slot.pk]), {'q': 'ناشناخته'})
        self.assertEqual(len(roster.context['rows']), 0)
        roster = self.client.get(reverse('management-session', args=[self.slot.pk]), {'q': '۰۹۱۲۳۴۵۶۷۸۹'})
        self.assertEqual(len(roster.context['rows']), 1)

    def test_billing_status_at_expiry(self):
        self.assertEqual(billing_status(self.subscription, date(2026, 11, 21))['tone'], 'warning')
        self.assertEqual(billing_status(self.subscription, date(2026, 11, 24))['tone'], 'danger')


class ChildProfileEditTests(TestCase):
    def test_only_parent_can_edit_and_birth_date_is_prefilled(self):
        import jdatetime
        parent = get_user_model().objects.create_user('profile-parent')
        other = get_user_model().objects.create_user('profile-other')
        child = Child.objects.create(parent=parent, full_name='پروفایل کودک', birth_date=date(2025, 3, 1))
        self.client.force_login(parent)
        response = self.client.get(reverse('child-edit', args=[child.pk]))
        self.assertEqual(response.context['form'].initial['birth_jalali'], '1403/12/11')
        response = self.client.post(reverse('child-edit', args=[child.pk]), {'full_name': 'نام تازه', 'birth_jalali': '۱۴۰۳/۱۲/۱۱', 'notes': 'یادداشت مربی', 'parent': other.pk})
        self.assertEqual(response.status_code, 302)
        child.refresh_from_db()
        self.assertEqual(child.parent, parent)
        self.assertEqual(child.notes, 'یادداشت مربی')
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('child-edit', args=[child.pk])).status_code, 404)
