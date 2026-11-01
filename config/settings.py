import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('Set DJANGO_SECRET_KEY or enable DJANGO_DEBUG for local development.')
    SECRET_KEY = 'local-development-only-not-for-production'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'catalog', 'portal', 'enrollment']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'portal.middleware.PrivatePages', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[], 'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR / 'db.sqlite3'}}
if os.environ.get('POSTGRES_DB'):
    DATABASES = {'default': {'ENGINE':'django.db.backends.postgresql','NAME':os.environ['POSTGRES_DB'],'USER':os.environ['POSTGRES_USER'],'PASSWORD':os.environ['POSTGRES_PASSWORD'],'HOST':os.environ.get('POSTGRES_HOST','localhost'),'PORT':os.environ.get('POSTGRES_PORT','5432')}}
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
WSGI_APPLICATION = 'config.wsgi.application'
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/account/'
SMS_SEND_FUNCTION = os.environ.get('SMS_SEND_FUNCTION', '')
LOCAL_SMS_ENABLED = DEBUG and os.environ.get('LOCAL_SMS_ENABLED', '0') == '1'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True

PAYMENT_BACKEND = os.environ.get('PAYMENT_BACKEND', '')
PAYMENT_MERCHANT_ID = os.environ.get('PAYMENT_MERCHANT_ID', '')
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', 'http://localhost:8000' if DEBUG else '')

STORAGES = {'default': {'BACKEND':'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
if not DEBUG:
    if not os.environ.get('POSTGRES_DB'):
        raise RuntimeError('Production requires PostgreSQL configuration.')
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Enable only behind the supplied reverse proxy, never on a public direct port.
    if os.environ.get('TRUST_PROXY_HTTPS','0') == '1':
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CSRF_TRUSTED_ORIGINS = [origin for origin in os.environ.get('CSRF_TRUSTED_ORIGINS','').split(',') if origin]

SMS_OTP_SEND_FUNCTION = os.environ.get('SMS_OTP_SEND_FUNCTION', '')
SMS_API_KEY = os.environ.get('SMS_API_KEY', '')
SMS_OTP_TEMPLATE = os.environ.get('SMS_OTP_TEMPLATE', '')
SMS_SENDER = os.environ.get('SMS_SENDER', '')

TRUST_PROXY_CLIENT_IP = os.environ.get('TRUST_PROXY_HTTPS','0') == '1'
