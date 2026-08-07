from django.contrib import admin
from .models import VideoSession


@admin.register(VideoSession)
class VideoSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "loan",
        "borrower",
        "loan_officer",
        "schedule_date",
        "schedule_time",
        "duration_minutes",
        "zoom_meeting_id",
        "created_at",
    )
    list_filter = (
        "schedule_date",
        "duration_minutes",
        "created_at",
    )
    search_fields = (
        "zoom_meeting_id",
        "borrower__email",
        "borrower__first_name",
        "borrower__last_name",
        "loan_officer__email",
        "loan_officer__first_name",
        "loan_officer__last_name",
        "comments",
    )
    autocomplete_fields = ("loan", "borrower", "loan_officer")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "schedule_date"
    ordering = ("-schedule_date", "-schedule_time")