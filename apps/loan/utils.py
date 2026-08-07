from .tasks import send_new_loan_assignment_email_task
from django.db import models
from django.db.models import Count
from apps.account.models import User


def auto_assign_loan_officer(loan_instance):
    """
    Automatically assigns a Loan Officer to a new loan application using
    a workload-based approach (assigns to the officer with the fewest active loan).
    """
    # 1. Get all active Loan Officers
    # We filter by the role defined in your User model
    eligible_officers = User.objects.filter(
        role=User.Role.LOAN_OFFICER,
        is_active=True
    )

    if not eligible_officers.exists():
        # Handle edge case where no loan officers exist
        # In production, you might want to alert an admin instead
        return False

    # 2. Annotate officers with their current number of assigned loan
    # We use 'managed_loans' which is the related_name set in the Loan model
    officers_with_workload = eligible_officers.annotate(
        active_loan_count=Count('managed_loans', filter=models.Q(managed_loans__application_status__in=[
            'SUB', 'VF', 'UNDR', 'SCH'
        ]))
    )
    assigned_officer = officers_with_workload.order_by('active_loan_count').first()

    # 4. Assign and save
    if assigned_officer:
        loan_instance.loan_officer = assigned_officer
        # Crucial: Change status from SUBMITTED to UNDER_REVIEW automatically upon assignment
        loan_instance.application_status = loan_instance.ApplicationStatus.UNDER_REVIEW
        loan_instance.save()

        # 5. Send targeted notification email to ONLY this officer
        send_new_loan_assignment_email_task(assigned_officer, loan_instance)

        return True

    return False