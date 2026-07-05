"""
ASGI config for VOIDLAB.

Routes plain HTTP to Django as usual, and upgrades `/ws/` connections to the
Channels layer that powers the interactive in-browser terminal.
"""
import os

import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

django_asgi_app = get_asgi_application()

from apps.core.ws_auth import JWTAuthMiddlewareStack  # noqa: E402
from apps.terminal import routing as terminal_routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(URLRouter(terminal_routing.websocket_urlpatterns))
        ),
    }
)
