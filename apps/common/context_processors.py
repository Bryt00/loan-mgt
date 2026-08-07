from apps.loan.models import Loan
from apps.account.models import User

def notification_counts(request):
    """
    Context processor to provide notification counts globally.
    For Loan Officers: Count of SUBMITTED loans.
    For Borrowers: Could be unread messages or updates (using UNDER_REVIEW/VERIFYING as an example).
    """
    count = 0
    if request.user.is_authenticated:
        if request.user.role == User.Role.LOAN_OFFICER:
            count = Loan.objects.filter(application_status=Loan.ApplicationStatus.SUBMITTED).count()
        elif request.user.role == User.Role.BORROWER:
            count = Loan.objects.filter(
                borrower=request.user, 
                application_status__in=[
                    Loan.ApplicationStatus.UNDER_REVIEW, 
                    Loan.ApplicationStatus.VERIFYING
                ]
            ).count()
    return {'notification_count': count}
