from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    ProfileSerializer,
    RegisterSerializer,
    VoidlabTokenObtainPairSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Public sign-up endpoint. Throttled under the 'auth' scope to slow
    down credential-stuffing / account-farming attempts against the lab
    platform itself.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "auth"


class VoidlabTokenObtainPairView(TokenObtainPairView):
    serializer_class = VoidlabTokenObtainPairSerializer
    throttle_scope = "auth"


class MeView(APIView):
    """Get/update the authenticated user's own profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
