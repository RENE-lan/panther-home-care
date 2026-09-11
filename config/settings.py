"""Panther Home Care — Django settings."""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Minimal .env loader (no dependency): KEY=value lines into os.environ.
    Existing environment variables always win. Ignores blanks and # comments."""
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            # strip inline comments and surrounding quotes/whitespace
            val = val.split(" #", 1)[0].strip().strip('"').strip("'")
            os.environ.setdefault(key, val)
    except FileNotFoundError:
        pass


_load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me-in-production")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "corsheaders",
    # Authentication (django-allauth): email/password + social sign-in
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "allauth.socialaccount.providers.facebook",
    # Panther modules
    "accounts",
    "clients",
    "caregivers",
    "scheduling",
    "reports",
    "incidents",
    "notifications",
    "audit",
    "ai",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notifications.context_processors.unread_alerts",
                "accounts.context_processors.agency",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL in production; SQLite for local/dev out of the box.
if os.environ.get("DATABASE_URL", "").startswith("postgres"):
    import dj_database_url  # optional dependency
    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"])}
elif os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "panther"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Lubumbashi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "accounts.backends.MultiIdentifierBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "account_login"

# ---- django-allauth ----
# Email + password sign-up/sign-in works out of the box (no SMTP needed for the demo).
# Username is kept too, so the seeded demo login (rene / panther123) still works.
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_SIGNUP_FORM_CLASS = "accounts.forms.PantherSignupForm"
ACCOUNT_EMAIL_VERIFICATION = "none"     # set to "mandatory" once SMTP is configured
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_ADAPTER = "accounts.adapter.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapter.SocialAdapter"
SOCIALACCOUNT_LOGIN_ON_GET = True        # go straight to the provider on button click
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---- Optional AI provider (for LLM-powered features like the daily brief) ----
# Paste your key into .env — never in code, and never in the frontend. When unset,
# the app falls back to its built-in rule-based AI, so nothing breaks.
AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai").lower()  # openai | anthropic | gemini
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "")

# Notifications delivery
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Panther Home Care <no-reply@panthergroup.cd>")
if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
# Optional SMS via Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.environ.get("TWILIO_FROM", "")

# Social providers. The buttons render always; each becomes live once its OAuth
# credentials are supplied via environment variables (see README).
SOCIALACCOUNT_PROVIDERS = {}
if os.environ.get("GOOGLE_CLIENT_ID"):
    SOCIALACCOUNT_PROVIDERS["google"] = {"APP": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""), "key": ""}}
if os.environ.get("FACEBOOK_CLIENT_ID"):
    SOCIALACCOUNT_PROVIDERS["facebook"] = {"APP": {
        "client_id": os.environ["FACEBOOK_CLIENT_ID"],
        "secret": os.environ.get("FACEBOOK_CLIENT_SECRET", ""), "key": ""}}
if os.environ.get("APPLE_CLIENT_ID"):
    SOCIALACCOUNT_PROVIDERS["apple"] = {"APP": {
        "client_id": os.environ["APPLE_CLIENT_ID"],
        "secret": os.environ.get("APPLE_SECRET", ""),
        "key": os.environ.get("APPLE_KEY_ID", ""),
        "settings": {"certificate_key": os.environ.get("APPLE_PRIVATE_KEY", "")}}}

# ---- Cross-origin (React frontend hosted separately, e.g. on Render) ----
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").rstrip("/")
BACKEND_URL = os.environ.get("BACKEND_URL", "").rstrip("/")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [u for u in [FRONTEND_URL] if u]
CSRF_TRUSTED_ORIGINS = [u for u in [FRONTEND_URL, BACKEND_URL] if u]
CSRF_TRUSTED_ORIGINS += ["https://*.onrender.com"]
# Render terminates TLS at its proxy:
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Production hardening (only active when DEBUG is off)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Allow the separately-hosted React SPA to send the session cookie:
    if FRONTEND_URL:
        SESSION_COOKIE_SAMESITE = "None"
        CSRF_COOKIE_SAMESITE = "None"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    X_FRAME_OPTIONS = "DENY"
