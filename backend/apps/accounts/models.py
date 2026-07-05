from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """VOIDLAB operator account.

    Extends Django's built-in user with the fields the platform needs for
    progress tracking and the leaderboard. `is_staff` (Django built-in)
    gates access to hints/solutions in the admin and via `IsStaffOrReadOnly`
    style permissions on the labs API.
    """

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    display_name = models.CharField(max_length=64, blank=True)
    bio = models.TextField(blank=True)

    # Denormalized for fast leaderboard sorting; kept in sync in
    # apps.labs.services.award_points() whenever a flag is captured.
    total_points = models.PositiveIntegerField(default=0)
    labs_completed = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.username

    @property
    def is_admin_operator(self) -> bool:
        """True for accounts allowed to view hints/solutions & lab authoring."""
        return self.is_staff or self.role == self.Role.ADMIN
