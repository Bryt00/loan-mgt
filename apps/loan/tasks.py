# apps/loan/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from apps.account.models import User
from apps.loan.models import Loan


@shared_task
def send_new_loan_assignment_email_task(loan_id, officer_id):
    """
    Background task to send email notification.
    We pass IDs instead of objects because Celery serializes data to JSON.
    """
    try:
        officer = User.objects.get(id=officer_id)
        loan = Loan.objects.get(id=loan_id)  # Need to import Loan model

        subject = f"New Loan Application Assigned: #{loan.id} - {loan.borrower.full_name}"
        message = f"""
        Hello {officer.full_name},

        A new loan application has been automatically assigned to you for review.

        Borrower: {loan.borrower.full_name}
        Amount: GHS {loan.amount}
        Purpose: {loan.purpose}

        Please log in to the dashboard to review details.

        Best regards,
        SmartLoan System
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [officer.email],
            fail_silently=False,
        )
    except Exception as e:
        # Log the error appropriately in production
        print(f"Failed to send email task: {e}")