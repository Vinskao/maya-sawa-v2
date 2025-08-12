"""
Test settings for maya-sawa-v2
"""

from .base import *  # noqa

# Use in-memory SQLite database for testing
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable debug mode for tests
DEBUG = False

# Use console email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable CSRF for API tests
API_REQUIRE_CSRF = False

# Disable authentication for API tests
API_REQUIRE_AUTHENTICATION = False

# Disable rate limiting for tests
API_RATE_LIMIT_ENABLED = False

# Use simple cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable Celery for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use test secret key
SECRET_KEY = "test-secret-key-for-testing-only"

# Disable logging for tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}

# Disable allauth email verification for tests
ACCOUNT_EMAIL_VERIFICATION = "none"

# Use test Redis URL
REDIS_URL = "redis://localhost:6379/1"  # Use different database for tests
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Disable static files collection for tests
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Disable media files for tests
MEDIA_ROOT = "/tmp/test-media/"

# Disable whitenoise for tests
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]

# Disable security middleware for tests
MIDDLEWARE = [m for m in MIDDLEWARE if "security" not in m]

# Use test allowed hosts
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Disable SSL redirect for tests
SECURE_SSL_REDIRECT = False

# Disable HSTS for tests
SECURE_HSTS_SECONDS = 0

# Disable content type sniffing for tests
SECURE_CONTENT_TYPE_NOSNIFF = False

# Disable frame options for tests
X_FRAME_OPTIONS = "SAMEORIGIN"

# Use test session settings
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Disable admin force allauth for tests
DJANGO_ADMIN_FORCE_ALLAUTH = False
