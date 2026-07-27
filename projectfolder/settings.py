"""
Django settings for projectfolder project.
Configured for Multi-Tenant Production Deployment.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SECURITY & ENVIRONMENT CONFIGURATION
# ==============================================================================

# 1. SECRET KEY: Read from env, with a dev-only fallback
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-v&vy05gnofd954!t2y4na4wxy+6kit+1a0-3_6jvwnxj@$@*u^'
)

# 2. DEBUG MODE: Defaults to False unless explicitly set to 'True' in env
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

# 3. ALLOWED HOSTS & CSRF
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '.threeangels.com,localhost,.localhost,127.0.0.1,127.0.0.1:8000').split(',')

CSRF_TRUSTED_ORIGINS = [
    'https://*.threeangels.com',
    'https://threeangels.com',
    'http://localhost',
    'http://*.localhost',       # Allows subdomains locally
    'http://*.localhost:8002',  # Allows your specific local port
    'http://localhost:8000',
    'http://127.0.0.1',
    'http://127.0.0.1:8000',
]

# 4. STRICT PRODUCTION SECURITY SETTINGS
if not DEBUG:
    # Cookie Protections
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'

    # SSL & Proxy Settings
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True

    # HTTP Strict Transport Security (HSTS) - Enforces HTTPS for all subdomains
    SECURE_HSTS_SECONDS = 31536000  # 1 Year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ==============================================================================
# MULTI-TENANT APPLICATION DEFINITION
# ==============================================================================

SHARED_APPS = [
    'django_tenants',
    'schools_manager',
    'users',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

TENANT_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'students_app',
    'users',
    'bootstrap4',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "schools_manager.School"
TENANT_DOMAIN_MODEL = "schools_manager.Domain"
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True

# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serves static files efficiently
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'projectfolder.urls'
PUBLIC_SCHEMA_URLCONF = 'projectfolder.urls_public'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'projectfolder.wsgi.application'

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': os.environ.get('DB_NAME', 'school_tenant_db'),
        'USER': os.environ.get('DB_USER', 'admin'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'supersecretpassword'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '15432'),
    }
}

DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# ==============================================================================
# PASSWORDS & LOCALIZATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# STATIC & MEDIA FILES STORAGE
# ==============================================================================

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# WhiteNoise production storage configuration
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ==============================================================================
# AUTHENTICATION & REDIRECTS
# ==============================================================================

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'students_app:dashboard'
LOGOUT_REDIRECT_URL = 'users:login'
AUTH_USER_MODEL = 'users.CustomUser'