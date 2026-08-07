from apps.account.models import User
from apps.common.models import BaseModel
from apps.loan.models import Loan
from django.db import models


class VideoSession(BaseModel):
    loan = models.ForeignKey(
        Loan, on_delete=models.SET_NULL, null=True, related_name="video_sessions"
    )
    borrower = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="video_sessions"
    )
    loan_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="officer_video_sessions",
    )
    zoom_meeting_id = models.CharField(max_length=225, blank=True, null=True)
    schedule_date = models.DateField(blank=True, null=True)
    schedule_time = models.TimeField(blank=True, null=True)
    duration_minutes = models.IntegerField(blank=True, null=True)
    meeting_url = models.URLField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        borrower_name = self.borrower.full_name if self.borrower else "N/A"
        return (
            f"Video Session for Loan #{self.loan.id if self.loan else 'N/A'} "
            f"with {borrower_name} on {self.schedule_date or 'Unscheduled'}"
        )