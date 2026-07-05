from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import UserPublicSerializer

User = get_user_model()
CACHE_KEY = "leaderboard:top100"
CACHE_TTL_SECONDS = 15


class LeaderboardView(APIView):
    """Top 100 operatives by total_points. Short-lived cache keeps this cheap
    even if the dashboard polls it frequently; correctness matters far less
    here than snappy UI, so a few seconds of staleness is an acceptable trade.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = cache.get(CACHE_KEY)
        if data is None:
            qs = User.objects.filter(is_active=True).order_by("-total_points", "-labs_completed")[:100]
            data = UserPublicSerializer(qs, many=True).data
            cache.set(CACHE_KEY, data, CACHE_TTL_SECONDS)

        my_rank = None
        for i, row in enumerate(data, start=1):
            if row["id"] == request.user.id:
                my_rank = i
                break

        return Response({"results": data, "my_rank": my_rank})
