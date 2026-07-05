from django.db import connection
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Liveness/readiness probe used by docker-compose healthchecks and by
    orchestrators. Verifies the database and cache are actually reachable,
    not just that the process is up.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        checks = {"database": self._check_db(), "cache": self._check_cache()}
        healthy = all(checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=200 if healthy else 503,
        )

    @staticmethod
    def _check_db():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    @staticmethod
    def _check_cache():
        try:
            cache.set("healthcheck", "1", timeout=5)
            return cache.get("healthcheck") == "1"
        except Exception:
            return False
