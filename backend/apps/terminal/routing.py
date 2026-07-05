from django.urls import re_path

from .consumers import TerminalConsumer

websocket_urlpatterns = [
    re_path(r"^ws/terminal/(?P<lab_slug>[\w-]+)/$", TerminalConsumer.as_asgi()),
]
