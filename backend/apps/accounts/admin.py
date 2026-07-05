from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

admin.site.site_header = "VOIDLAB Admin"
admin.site.site_title = "VOIDLAB Admin"
admin.site.index_title = "Range Control"


@admin.register(User)
class VoidlabUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "total_points", "labs_completed", "is_staff")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("VOIDLAB Profile", {"fields": ("role", "display_name", "bio", "total_points", "labs_completed")}),
    )
