import os

from .base import *  # noqa: F401,F403

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host]

# Zeabur terminates TLS in front of the container and forwards the original
# protocol via the header above, so every request Django sees can be told
# to redirect to HTTPS and to advertise HSTS (HTTP Strict Transport
# Security: tells browsers to only ever use HTTPS for this host) safely.
# Without these four, Django's own `manage.py check --deploy` fails
# (security.W004, security.W005, security.W008, security.W021) even when
# every secret is configured correctly, so the CI job can never turn
# green. INCLUDE_SUBDOMAINS is safe here because ALLOWED_HOSTS is a single
# Zeabur-assigned subdomain with nothing beneath it; PRELOAD only changes
# the header this app sends, it does not submit the domain to the browser
# preload list by itself.
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year, the conventional value for HSTS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
