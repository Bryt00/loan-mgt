from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from apps.loan.models import Loan, SupportingDocuments, LoanNote


def safe_cache_delete(*keys):
    try:
        for key in keys:
            cache.delete(key)
    except Exception:
        pass


@receiver(post_save, sender=Loan)
def invalidate_cache_on_loan_save(sender, instance, created, **kwargs):
    """
    Invalidate all loan officer cache keys (including borrowers list) when a loan is created or updated.
    """
    if instance.loan_officer_id:
        safe_cache_delete(
            f'loan_officer_applications_{instance.loan_officer_id}',
            f'loan_officer_pending_applications_{instance.loan_officer_id}',
            f'loan_officer_approved_disbursed_applications_{instance.loan_officer_id}',
            f'loan_officer_borrowers_with_loans_{instance.loan_officer_id}'
        )


@receiver(post_delete, sender=Loan)
def invalidate_cache_on_loan_delete(sender, instance, **kwargs):
    """
    Invalidate all loan officer cache keys (including borrowers list) when a loan is deleted.
    """
    if instance.loan_officer_id:
        safe_cache_delete(
            f'loan_officer_applications_{instance.loan_officer_id}',
            f'loan_officer_pending_applications_{instance.loan_officer_id}',
            f'loan_officer_approved_disbursed_applications_{instance.loan_officer_id}',
            f'loan_officer_borrowers_with_loans_{instance.loan_officer_id}'
        )


@receiver(post_save, sender=SupportingDocuments)
def invalidate_cache_on_document_save(sender, instance, created, **kwargs):
    """
    Invalidate all loan officer cache keys (including borrowers list) when a related document is added or updated.
    """
    if instance.loan_application and instance.loan_application.loan_officer_id:
        officer_id = instance.loan_application.loan_officer_id
        safe_cache_delete(
            f'loan_officer_applications_{officer_id}',
            f'loan_officer_pending_applications_{officer_id}',
            f'loan_officer_approved_disbursed_applications_{officer_id}',
            f'loan_officer_borrowers_with_loans_{officer_id}'
        )


@receiver(post_delete, sender=SupportingDocuments)
def invalidate_cache_on_document_delete(sender, instance, **kwargs):
    """
    Invalidate all loan officer cache keys (including borrowers list) when a related document is deleted.
    """
    if instance.loan_application and instance.loan_application.loan_officer_id:
        officer_id = instance.loan_application.loan_officer_id
        safe_cache_delete(
            f'loan_officer_applications_{officer_id}',
            f'loan_officer_pending_applications_{officer_id}',
            f'loan_officer_approved_disbursed_applications_{officer_id}',
            f'loan_officer_borrowers_with_loans_{officer_id}'
        )


@receiver([post_save, post_delete], sender=LoanNote)
def invalidate_cache_on_note_change(sender, instance, **kwargs):
    """
    Invalidate loan officer cache keys when a loan note is created, updated, or deleted.
    """
    if instance.loan and instance.loan.loan_officer_id:
        officer_id = instance.loan.loan_officer_id
        safe_cache_delete(
            f'loan_officer_applications_{officer_id}',
            f'loan_officer_pending_applications_{officer_id}',
            f'loan_officer_approved_disbursed_applications_{officer_id}',
            f'loan_officer_borrowers_with_loans_{officer_id}'
        )