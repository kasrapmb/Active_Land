from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from .authentication import request_code, verify_code, normalize_phone
from .models import Child, LoginChallenge

class ParentTests(TestCase):
    def test_phone_normalization(self):
        self.assertEqual(normalize_phone('۰۹۱۲۳۴۵۶۷۸۹'),'09123456789')
        self.assertEqual(normalize_phone('+989123456789'),'09123456789')

    @patch('portal.authentication.deliver_code')
    def test_code_is_hashed_single_use_and_limited(self,send):
        request_code('09123456789','test-ip')
        code = send.call_args.args[1]
        row = LoginChallenge.objects.get()
        self.assertNotEqual(row.code_hash,code)
        for _ in range(5):
            self.assertIsNone(verify_code(row.phone,'xxxxxx'))
        self.assertIsNone(verify_code(row.phone,code))
        row.sent_at = timezone.now()-timedelta(minutes=2)
        row.save()
        request_code(row.phone,'test-ip')
        code = send.call_args.args[1]
        user = verify_code(row.phone,code)
        self.assertIsNotNone(user)
        self.assertFalse(user.has_usable_password())
        self.assertIsNone(verify_code(row.phone,code))

    @patch('portal.authentication.deliver_code')
    def test_expired_code_fails(self,send):
        request_code('09123456789','test-ip')
        LoginChallenge.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertIsNone(verify_code('09123456789',send.call_args.args[1]))

    @override_settings(SMS_SEND_FUNCTION='',LOCAL_SMS_ENABLED=False)
    def test_missing_provider_does_not_issue_valid_challenge(self):
        response = self.client.post('/account/login/',{'phone':'09123456789'})
        self.assertContains(response,'ارسال پیامک در دسترس نیست')
        self.assertFalse(LoginChallenge.objects.exists())

    def test_child_saved_to_current_parent_and_jalali_converted(self):
        user = get_user_model().objects.create_user('parent:test')
        other = get_user_model().objects.create_user('other')
        self.client.force_login(user)
        response = self.client.post('/account/children/new/',{'full_name':'کودک من','birth_jalali':'۱۴۰۳/۰۸/۲۴','parent':other.pk})
        self.assertEqual(response.status_code,302)
        child = Child.objects.get()
        self.assertEqual(child.parent,user)
        self.assertEqual(str(child.birth_date),'2024-11-14')
        self.client.force_login(other)
        self.assertNotContains(self.client.get('/account/'),'کودک من')

    def test_login_required_and_logout_post_only(self):
        self.assertEqual(self.client.get('/account/').status_code,302)
        user = get_user_model().objects.create_user('parent:test')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/account/logout/').status_code,405)
        self.assertEqual(self.client.post('/account/logout/').status_code,302)
