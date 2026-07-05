from django.conf import settings
from rest_framework import serializers

from .models import Category, Hint, Lab, LabProgress, Solution, Submission, UnlockedHint


class CategorySerializer(serializers.ModelSerializer):
    lab_count = serializers.IntegerField(source="labs.count", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "code", "name", "short_name", "description", "icon", "order", "lab_count")


class HintSerializer(serializers.ModelSerializer):
    """Hint text is redacted until the requesting user has spent the point
    penalty to unlock it — enforced here, not just in the UI, so hitting the
    API directly can't bypass the point cost.
    """

    is_unlocked = serializers.SerializerMethodField()
    text = serializers.SerializerMethodField()

    class Meta:
        model = Hint
        fields = ("id", "order", "point_penalty", "is_unlocked", "text")

    def get_is_unlocked(self, obj) -> bool:
        user = self.context["request"].user
        return self._unlocked_ids(user).__contains__(obj.id) if user.is_authenticated else False

    def get_text(self, obj):
        user = self.context["request"].user
        if user.is_authenticated and obj.id in self._unlocked_ids(user):
            return obj.text
        return None

    def _unlocked_ids(self, user):
        cache_attr = "_voidlab_unlocked_hint_ids"
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, set(UnlockedHint.objects.filter(user=user).values_list("hint_id", flat=True)))
        return getattr(self, cache_attr)


class LabListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lab
        fields = (
            "id",
            "title",
            "slug",
            "category",
            "difficulty",
            "summary",
            "points",
            "estimated_minutes",
            "is_completed",
        )

    def get_is_completed(self, obj) -> bool:
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return LabProgress.objects.filter(user=user, lab=obj, is_completed=True).exists()


class LabDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    hints = HintSerializer(many=True, read_only=True)
    is_completed = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()
    target_url = serializers.SerializerMethodField()
    has_solution = serializers.SerializerMethodField()

    class Meta:
        model = Lab
        fields = (
            "id",
            "title",
            "slug",
            "category",
            "difficulty",
            "summary",
            "briefing",
            "objective",
            "points",
            "estimated_minutes",
            "target_url",
            "hints",
            "is_completed",
            "attempts",
            "has_solution",
        )

    def get_is_completed(self, obj) -> bool:
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return LabProgress.objects.filter(user=user, lab=obj, is_completed=True).exists()

    def get_attempts(self, obj) -> int:
        user = self.context["request"].user
        if not user.is_authenticated:
            return 0
        progress = LabProgress.objects.filter(user=user, lab=obj).first()
        return progress.attempts if progress else 0

    def get_target_url(self, obj):
        base = settings.VULNERABLE_APP_URLS.get(obj.target_app)
        if not base:
            return None
        return base.rstrip("/") + "/" + obj.target_path.lstrip("/")

    def get_has_solution(self, obj) -> bool:
        return Solution.objects.filter(lab=obj).exists()


class SolutionSerializer(serializers.ModelSerializer):
    """Only ever reachable through a view gated by IsAdminOperator."""

    class Meta:
        model = Solution
        fields = ("lab", "content", "updated_at")


class FlagSubmitSerializer(serializers.Serializer):
    flag = serializers.CharField(max_length=255, trim_whitespace=True)


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ("id", "lab", "is_correct", "points_awarded", "created_at")
        read_only_fields = fields
