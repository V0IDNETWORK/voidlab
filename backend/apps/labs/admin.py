from django.contrib import admin

from .models import Category, Hint, Lab, LabProgress, Solution, Submission, UnlockedHint


class HintInline(admin.TabularInline):
    model = Hint
    extra = 1


class SolutionInline(admin.StackedInline):
    model = Solution
    extra = 0
    max_num = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "order")
    ordering = ("order",)


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "difficulty", "status", "points", "target_app")
    list_filter = ("category", "difficulty", "status")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [HintInline, SolutionInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "is_correct", "points_awarded", "created_at")
    list_filter = ("is_correct",)
    readonly_fields = [f.name for f in Submission._meta.fields]


@admin.register(LabProgress)
class LabProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "is_completed", "attempts", "hints_used", "penalty_points")
    list_filter = ("is_completed",)


admin.site.register(UnlockedHint)
