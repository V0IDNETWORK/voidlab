from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password_confirm", "display_name")

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserPublicSerializer(serializers.ModelSerializer):
    """Safe-to-expose subset used in leaderboards and lab authorship."""

    class Meta:
        model = User
        fields = ("id", "username", "display_name", "total_points", "labs_completed")


class ProfileSerializer(serializers.ModelSerializer):
    is_admin_operator = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "display_name",
            "bio",
            "role",
            "total_points",
            "labs_completed",
            "is_admin_operator",
            "date_joined",
        )
        read_only_fields = ("id", "username", "role", "total_points", "labs_completed", "date_joined")


class VoidlabTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Embeds a couple of non-sensitive claims in the JWT so the frontend can
    render the navbar/role gating without an extra round trip on first paint.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["is_admin_operator"] = user.is_admin_operator
        return token
