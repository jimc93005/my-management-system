"""
Django settings for projectfolder project.
Configured for Multi-Tenant Production Deployment.
"""

from pathlib import Path
import os
from environ import Env
from pygments.styles import default

BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Initialize env
env = Env()

# 3. Read the .env file
Env.read_env(BASE_DIR / ".env")
# ==============================================================================
# SECURITY & ENVIRONMENT CONFIGURATION
# ==============================================================================

# 1. SECRET KEY: Read from env, with a dev-only fallback
# SECRET_KEY = env(
#     'SECRET_KEY',

# )

# 2. DEBUG MODE: Defaults to False unless explicitly set to 'True' in env
# DEBUG = env('DEBUG').lower() == 'true'

# 3. ALLOWED HOSTS & CSRF
# ALLOWED_HOSTS = env('ALLOWED_HOSTS',).split(',')

# 1. SECRET KEY: Read from env, with a fallback
SECRET_KEY = env('SECRET_KEY', default='your-super-secret-key-here')

# 2. DEBUG MODE: Safely parse boolean from env
DEBUG = env.bool('DEBUG', default=True)

# 3. ALLOWED HOSTS & CSRF
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])



CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])



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
    SECURE_SSL_REDIRECT = False

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
    'django_bootstrap5'
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
                'students_app.context_processors.school_footer_context'
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
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': env('POSTGRES_PORT'),
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



# ==========================================
# EMAIL SETTINGS
# ==========================================
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='')


# WhiteNoise production storage configuration
STORAGES = {
    "default": {
        "BACKEND": "django_tenants.files.storage.TenantFileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MULTITENANT_RELATIVE_MEDIA_ROOT = "%s"
# ==============================================================================
# AUTHENTICATION & REDIRECTS
# ==============================================================================

LOGIN_URL = 'users:login'
LOGIN_REDIRECT_URL = 'students_app:dashboard'
LOGOUT_REDIRECT_URL = 'users:login'
AUTH_USER_MODEL = 'users.CustomUser'