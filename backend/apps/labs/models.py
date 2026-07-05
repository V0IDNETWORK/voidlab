from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """An OWASP Top 10:2025 risk category.

    OWASP refreshed the Top 10 in late 2025; VOIDLAB tracks that current
    list (rather than the older 2021 edition) so the curriculum stays
    aligned with the standard practitioners are tested against today.
    """

    code = models.CharField(max_length=10, unique=True, help_text="e.g. A01, A02 ... A10")
    name = models.CharField(max_length=120)
    short_name = models.CharField(max_length=60, help_text="Compact label for UI chips")
    description = models.TextField()
    icon = models.CharField(max_length=40, default="shield", help_text="lucide-react icon name")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.code} · {self.name}"


class Lab(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"
        INSANE = "insane", "Insane"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="labs")
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PUBLISHED)

    summary = models.CharField(max_length=280, help_text="One-liner shown on lab cards")
    briefing = models.TextField(help_text="Full scenario/briefing, markdown supported")
    objective = models.TextField(help_text="What the learner must achieve to capture the flag")

    points = models.PositiveIntegerField(default=100)

    # Which isolated container this lab targets, matched against
    # settings.VULNERABLE_APP_URLS keys (e.g. "sqli-lab").
    target_app = models.CharField(max_length=40, blank=True)
    target_path = models.CharField(max_length=200, blank=True, default="/")

    flag_hash = models.CharField(max_length=255, help_text="Hashed via make_password(); never store plaintext")

    estimated_minutes = models.PositiveSmallIntegerField(default=30)
    order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__order", "order", "id"]

    def __str__(self):
        return f"[{self.category.code}] {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def set_flag(self, raw_flag: str) -> None:
        """Hash and store a plaintext flag. Used by the seed command / admin."""
        self.flag_hash = make_password(raw_flag)

    def check_flag(self, raw_flag: str) -> bool:
        if not raw_flag or not self.flag_hash:
            return False
        return check_password(raw_flag.strip(), self.flag_hash)


class Hint(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="hints")
    order = models.PositiveSmallIntegerField(default=1)
    text = models.TextField()
    point_penalty = models.PositiveIntegerField(
        default=5, help_text="Points deducted from this lab's reward the first time a user unlocks this hint"
    )

    class Meta:
        ordering = ["lab", "order"]

    def __str__(self):
        return f"Hint {self.order} for {self.lab.title}"


class Solution(models.Model):
    """Full walkthrough. Visible only to staff/admin accounts (see
    apps.labs.permissions.IsAdminOperatorOrReadOnlyHints) — kept out of the
    student-facing serializer entirely rather than just hidden in the UI.
    """

    lab = models.OneToOneField(Lab, on_delete=models.CASCADE, related_name="solution")
    content = models.TextField(help_text="Full markdown walkthrough, admin/instructor only")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Solution for {self.lab.title}"


class UnlockedHint(models.Model):
    """Marks that `user` has spent the point penalty to reveal `hint`.
    Existence of this row is what the hints serializer checks to decide
    whether to include the hint's text for a given requester.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unlocked_hints")
    hint = models.ForeignKey(Hint, on_delete=models.CASCADE, related_name="unlocks")
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "hint")

    def __str__(self):
        return f"{self.user} unlocked hint#{self.hint_id}"


class Submission(models.Model):
    """Every flag attempt, correct or not — powers per-lab attempt counters,
    anti-brute-force throttling, and an audit trail.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions")
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="submissions")
    submitted_value = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    points_awarded = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "lab"])]

    def __str__(self):
        status = "✔" if self.is_correct else "✘"
        return f"{status} {self.user} → {self.lab}"


class LabProgress(models.Model):
    """One row per (user, lab): denormalized completion state so dashboard
    and lab-list queries don't have to aggregate Submission on every load.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress")
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="progress_entries")
    is_completed = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    hints_used = models.PositiveIntegerField(default=0)
    penalty_points = models.PositiveIntegerField(
        default=0, help_text="Sum of point_penalty across every hint this user has unlocked for this lab"
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "lab")

    def __str__(self):
        return f"{self.user} · {self.lab} · {'done' if self.is_completed else 'in progress'}"
