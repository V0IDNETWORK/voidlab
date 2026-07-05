"""
JWT authentication for Channels WebSocket connections.

The browser's native WebSocket API can't send a custom Authorization
header on the handshake, so the SPA connects with `?token=<access_jwt>`
in the URL instead and this middleware validates it the same way DRF's
JWTAuthentication would for a normal HTTP request — same SIMPLE_JWT
settings, same signature/expiry checks, just adapted to the ASGI scope.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(raw_token: str):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        validated = AccessToken(raw_token)
        return User.objects.get(id=validated["user_id"])
    except (InvalidToken, TokenError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware:
    """ASGI middleware: reads ?token=<jwt> from the query string and sets
    scope['user'] accordingly, falling back to AnonymousUser on any failure.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        scope["user"] = await get_user_from_token(token) if token else AnonymousUser()
        return await self.app(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
