from django.contrib import admin
from .models import Loan, SupportingDocuments, LoanNote

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('id', 'borrower', 'amount', 'employment_status', 'application_status', 'submission_date')
    list_filter = ('application_status', 'employment_status', 'submission_date')
    search_fields = ('borrower__email', 'borrower__username', 'purpose', 'employer_name')
    readonly_fields = ('submission_date',)

@admin.register(SupportingDocuments)
class SupportingDocumentsAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan_application', 'document_type', 'verification_status')
    list_filter = ('document_type', 'verification_status')
    search_fields = ('loan_application__id', 'loan_application__borrower__email')

@admin.register(LoanNote)
class LoanNoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'loan', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('loan__id', 'author__email', 'content')
    readonly_fields = ('created_at', 'updated_at')