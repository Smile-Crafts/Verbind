"""
Django settings for the Verbind project (project folder name stayed
'travelbuddy' internally so your existing venv/paths don't break).

Reads from environment variables where present, with safe local-dev
defaults so `python manage.py runserver` on your laptop still works
exactly as before with zero setup.
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core security settings -------------------------------------------
# Locally these fall back to the old dev-only values. On Railway, set
# real values as environment variables (see DEPLOY.md).
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-secret-key-change-me')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Railway gives every deploy a *.up.railway.app domain automatically.
# ALLOWED_HOSTS accepts that plus anything you add via env var, comma-separated.
ALLOWED_HOSTS = ['.railway.app', 'localhost', '127.0.0.1']
extra_hosts = os.environ.get('ALLOWED_HOSTS', '')
if extra_hosts:
    ALLOWED_HOSTS += [h.strip() for h in extra_hosts.split(',') if h.strip()]

# Railway terminates HTTPS in front of the app and forwards over HTTP,
# so Django needs to trust that header to know the real request was secure.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h and not h.startswith('.')]
csrf_trusted_extra = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_trusted_extra:
    CSRF_TRUSTED_ORIGINS += [o.strip() for o in csrf_trusted_extra.split(',') if o.strip()]

# In production (DEBUG=False), enforce HTTPS-only cookies and redirects.
# Railway serves HTTPS at the edge and forwards to the app over HTTP, which
# is exactly what SECURE_PROXY_SSL_HEADER above tells Django to trust.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

SITE_NAME = 'Verbind'
# Used to build absolute links in emails (e.g. "click here to verify your
# email"), since email clients can't resolve a relative URL. Defaults to
# local dev; set SITE_URL as a Railway env var once deployed, e.g.
# https://web-production-5536dc.up.railway.app  (no trailing slash).
SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'trips',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'travelbuddy.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'trips.context_processors.unread_messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'travelbuddy.wsgi.application'

# --- Database -----------------------------------------------------------
# Locally: sqlite, same as always. On Railway: reads DATABASE_URL, which
# Railway sets automatically once you attach a Postgres database.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# --- Static files (CSS, the verbind.css stylesheet) ---------------------
# Whitenoise serves these directly from the Django process in production,
# so no separate static file host is needed.
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Uploaded files (profile pictures, "verification" documents).
# NOTE: Railway's filesystem is not permanent storage — files uploaded
# here can be lost on redeploy. Fine for team testing; before real users,
# move this to a cloud storage bucket (e.g. Cloudflare R2 or S3).
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# --- Email ---
# Emails print to the server log instead of sending for real, both locally
# and on Railway, until real SMTP credentials are set as env vars below.
#
# To send real emails, set these as environment variables (Railway or local):
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST=smtp.gmail.com
#   EMAIL_PORT=587
#   EMAIL_USE_TLS=True
#   EMAIL_HOST_USER=youraddress@gmail.com
#   EMAIL_HOST_PASSWORD=your-16-character-app-password   (Gmail "app password", not your login password)
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Verbind <noreply@verbind.local>')

# Free tier: non-pro users can join this many rides per calendar month.
FREE_JOINS_PER_MONTH = 2
