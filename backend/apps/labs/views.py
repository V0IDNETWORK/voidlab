from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Hint, Lab, Solution, Submission
from .permissions import IsAdminOperator, IsAdminOperatorOrReadOnly
from .serializers import (
    CategorySerializer,
    FlagSubmitSerializer,
    LabDetailSerializer,
    LabListSerializer,
    SolutionSerializer,
    SubmissionSerializer,
)
from .services import submit_flag, unlock_hint


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class LabViewSet(viewsets.ModelViewSet):
    """Read access for any authenticated learner; write access (lab
    authoring) restricted to instructors/admins. Custom actions below cover
    the actual "play the lab" workflow: submitting a flag and unlocking hints.
    """

    queryset = Lab.objects.select_related("category").prefetch_related("hints").filter(status=Lab.Status.PUBLISHED)
    permission_classes = [IsAdminOperatorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category__code", "difficulty"]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "list":
            return LabListSerializer
        return LabDetailSerializer

    def get_permissions(self):
        # Gameplay actions (read, submit a flag, unlock a hint, view your own
        # history) are open to any authenticated learner. Only lab authoring
        # (create/update/destroy) and the solution walkthrough require an
        # admin/instructor account.
        if self.action in ("solution",):
            return [IsAdminOperator()]
        if self.action in ("list", "retrieve", "submit", "unlock_hint_action", "my_submissions"):
            return [permissions.IsAuthenticated()]
        return [IsAdminOperatorOrReadOnly()]

    @action(detail=True, methods=["post"], throttle_scope="flag_submit")
    def submit(self, request, slug=None):
        """POST { "flag": "VOIDLAB{...}" } — the core gameplay loop."""
        lab = self.get_object()
        serializer = FlagSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission = submit_flag(user=request.user, lab=lab, raw_value=serializer.validated_data["flag"])
        return Response(SubmissionSerializer(submission).data, status=200 if submission.is_correct else 400)

    @action(detail=True, methods=["post"], url_path="hints/(?P<hint_id>[^/.]+)/unlock")
    def unlock_hint_action(self, request, slug=None, hint_id=None):
        lab = self.get_object()
        hint = get_object_or_404(Hint, id=hint_id, lab=lab)
        progress = unlock_hint(user=request.user, lab=lab, hint=hint)
        return Response(
            {"hint_id": hint.id, "text": hint.text, "penalty_points": progress.penalty_points}
        )

    @action(detail=True, methods=["get"], permission_classes=[IsAdminOperator])
    def solution(self, request, slug=None):
        """Full walkthrough — staff/instructor/admin only, enforced server
        side via IsAdminOperator (not merely hidden client-side).
        """
        lab = self.get_object()
        solution = get_object_or_404(Solution, lab=lab)
        return Response(SolutionSerializer(solution).data)

    @action(detail=False, methods=["get"])
    def my_submissions(self, request):
        qs = Submission.objects.filter(user=request.user).select_related("lab")[:100]
        return Response(SubmissionSerializer(qs, many=True).data)
