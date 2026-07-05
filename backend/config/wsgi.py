"""WSGI config for VOIDLAB. Daphne (ASGI) is the primary server; this is kept
for tooling that expects a standard WSGI callable (e.g. some PaaS health checks)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
