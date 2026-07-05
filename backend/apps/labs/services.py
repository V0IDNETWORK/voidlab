"""Scoring and progress logic, kept out of the views/serializers so it has a
single, testable home and views stay thin.
"""
from django.db import transaction
from django.utils import timezone

from .models import Lab, LabProgress, Submission


class DuplicateHintError(Exception):
    """Raised when a hint has already been unlocked (no double penalty)."""


@transaction.atomic
def submit_flag(*, user, lab: Lab, raw_value: str) -> Submission:
    """Validate a flag submission, update progress, and award points exactly
    once per lab (subsequent correct-but-already-solved submissions are
    recorded for the audit trail but award zero additional points).
    """
    progress, _ = LabProgress.objects.select_for_update().get_or_create(user=user, lab=lab)
    is_correct = lab.check_flag(raw_value)

    points_awarded = 0
    if is_correct and not progress.is_completed:
        points_awarded = max(lab.points - progress.penalty_points, 0)
        progress.is_completed = True
        progress.completed_at = timezone.now()

        user.total_points += points_awarded
        user.labs_completed += 1
        user.save(update_fields=["total_points", "labs_completed"])

    progress.attempts += 1
    progress.save()

    return Submission.objects.create(
        user=user,
        lab=lab,
        submitted_value=raw_value[:255],
        is_correct=is_correct,
        points_awarded=points_awarded,
    )


@transaction.atomic
def unlock_hint(*, user, lab: Lab, hint) -> LabProgress:
    """Deduct a hint's point penalty from what the user will earn on this
    lab. Idempotent per (user, lab, hint) via UnlockedHint so re-requesting
    an already-unlocked hint never double-charges the penalty.
    """
    from .models import UnlockedHint  # local import to avoid circulars at module load

    progress, _ = LabProgress.objects.select_for_update().get_or_create(user=user, lab=lab)

    _, created = UnlockedHint.objects.get_or_create(user=user, hint=hint)
    if created:
        progress.hints_used += 1
        progress.penalty_points += hint.point_penalty
        progress.save(update_fields=["hints_used", "penalty_points"])

    return progress
