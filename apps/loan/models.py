from typing import Any

from django.db import models
from apps.common.models import BaseModel
from apps.account.models import User


class Loan(BaseModel):
    class EmploymentStatus(models.TextChoices):
        EMPLOYED = 'EMP'
        UNEMPLOYED = 'UNEMP'

    class ApplicationStatus(models.TextChoices):
        SUBMITTED = 'SUB'
        VERIFYING = 'VF'
        UNDER_REVIEW = 'UNDR'
        SCHEDULED = 'SCH'
        APPROVED = 'AP'
        REJECTED = 'REJ'
        DISBURSED = 'DIS'

    borrower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_loans')
    loan_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='managed_loans')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField()
    tenure_months = models.IntegerField()

    employment_status = models.CharField(max_length=10, choices=EmploymentStatus.choices)
    employer_name = models.CharField(max_length=100, blank=True, null=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2)
    existing_loans = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    passport_picture = models.ImageField(upload_to='loan/passport_pictures/')

    application_status = models.CharField(max_length=10, choices=ApplicationStatus.choices,
                                         default=ApplicationStatus.SUBMITTED)

    risk_score = models.IntegerField(null=True, blank=True)
    risk_tier = models.IntegerField(null=True, blank=True)
    decision_notes = models.TextField(blank=True, null=True)

    submission_date = models.DateTimeField(auto_now_add=True)
    decision_date = models.DateTimeField(null=True, blank=True)

    @property
    def outstanding_balance(self):
        from decimal import Decimal
        from django.db.models import Sum
        repaid = self.payments.filter(
            payment_type="REPAYMENT",
            status="SUCCESS"
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        return max(Decimal('0.00'), self.amount - repaid)
    def __str__(self):
        return f"Loan #{self.id} - {self.borrower.email} ({self.amount})"


class SupportingDocuments(BaseModel):
    class DocumentType(models.TextChoices):
        GHANA_CARD = 'GHANA'
        NATIONAL_ID = 'NATIONAL'
        FINANCIAL_STATEMENT = 'FIN'
        OTHER = 'OT'

    loan_application = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=10, choices=DocumentType.choices)
    document = models.FileField(upload_to='loan/documents/')
    verification_status = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_document_type_display()} for Loan #{self.loan_application.id}"


class LoanNote(BaseModel):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_notes')
    content = models.TextField()

    def __str__(self):
        return f"Note by {self.author.email} on Loan #{self.loan.id}"