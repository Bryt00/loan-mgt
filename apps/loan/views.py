from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponseForbidden

from .forms import LoanApplicationForm
from .models import Loan, SupportingDocuments
from .utils import auto_assign_loan_officer



def invalidate_loan_cache(loan_id, borrower_id):
    """Removes cached loan data when changes occur."""
    cache.delete(f'loan_detail_{loan_id}')
    cache.delete(f'borrower_active_loans_{borrower_id}')


@login_required
def apply_for_loan(request):
    """
    Allows a BORROWER to submit a new loan application.
    Implements caching to check for active loan and invalidates it on creation.
    """
    if request.user.role != request.user.Role.BORROWER:
        messages.warning(request, "Only authorized borrowers can submit applications.")
        return redirect('account:dashboard')

    cache_key = f'borrower_active_loans_{request.user.id}'
    has_active_loan_cache = cache.get(cache_key)

    if has_active_loan_cache is None:

        has_active_loan = Loan.objects.filter(
            borrower=request.user,
            application_status__in=[
                Loan.ApplicationStatus.SUBMITTED,
                Loan.ApplicationStatus.UNDER_REVIEW,
                Loan.ApplicationStatus.SCHEDULED
            ]
        ).exists()

        cache.set(cache_key, has_active_loan, 60 * 15)
    else:
        has_active_loan = has_active_loan_cache

    if has_active_loan:
        messages.info(request, "You already have an active loan application being processed.")
        return redirect('borrower_app:borrower_dashboard')

    if request.method == 'POST':
        form = LoanApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            loan_application = form.save(commit=True, borrower=request.user)

            # Process multiple documents explicitly
            if request.FILES.get('ghana_card'):
                SupportingDocuments.objects.create(
                    loan_application=loan_application,
                    document_type=SupportingDocuments.DocumentType.GHANA_CARD,
                    document=request.FILES.get('ghana_card')
                )
            if request.FILES.get('national_id'):
                SupportingDocuments.objects.create(
                    loan_application=loan_application,
                    document_type=SupportingDocuments.DocumentType.NATIONAL_ID,
                    document=request.FILES.get('national_id')
                )
            if request.FILES.get('financial_statement'):
                SupportingDocuments.objects.create(
                    loan_application=loan_application,
                    document_type=SupportingDocuments.DocumentType.FINANCIAL_STATEMENT,
                    document=request.FILES.get('financial_statement')
                )
            if request.FILES.get('other_document'):
                SupportingDocuments.objects.create(
                    loan_application=loan_application,
                    document_type=SupportingDocuments.DocumentType.OTHER,
                    document=request.FILES.get('other_document')
                )

            # 2. Trigger Auto-Assignment & Background Email Task
            auto_assign_loan_officer(loan_application)

            cache.delete(f'borrower_active_loans_{request.user.id}')

            messages.success(request, "Loan application submitted successfully!")
            return redirect('loan:application_status', loan_id=loan_application.id)
    else:
        form = LoanApplicationForm()

    return render(request, 'loan/apply_loan.html', {'form': form, 'title': 'Apply for SmartLoan'})


@login_required
def loan_application_status(request, loan_id):
    """
    Displays loan status with caching enabled for the detail view.
    """
    cache_key = f'loan_detail_{loan_id}'

    loan_data = cache.get(cache_key)

    if loan_data is None:
        loan = get_object_or_404(Loan, id=loan_id, borrower=request.user)
        documents = loan.documents.select_related('loan_application').all()

        loan_data = {
            'loan': loan,
            'documents': list(documents),
        }

        cache.set(cache_key, loan_data, 60 * 10)
    else:

        loan = loan_data['loan']
        documents = loan_data['documents']


    if loan.borrower != request.user and not request.user.is_staff:
        return HttpResponseForbidden("You are not authorized to view this loan.")

    context = {
        'loan': loan,
        'documents': documents,
        'title': f'Loan Application #{loan.id} Status'
    }
    return render(request, 'loan/status.html', context)


@login_required
def update_loan_application(request, loan_id):
    """
    Allows borrower to update application if status permits.
    Handles cache invalidation.
    """
    loan = get_object_or_404(Loan, id=loan_id, borrower=request.user)

    # Business logic: only allow updates if not yet reviewed by officer
    if loan.application_status != Loan.ApplicationStatus.SUBMITTED:
        messages.warning(request, "This application is already under review and cannot be edited.")
        return redirect('loan:application_status', loan_id=loan.id)

    if request.method == 'POST':
        # Pass instance to update existing record
        form = LoanApplicationForm(request.POST, request.FILES, instance=loan)
        if form.is_valid():
            form.save(commit=True, borrower=request.user)

            # Process multiple documents (appends to existing) explicitly
            if request.FILES.get('ghana_card'):
                SupportingDocuments.objects.create(
                    loan_application=loan,
                    document_type=SupportingDocuments.DocumentType.GHANA_CARD,
                    document=request.FILES.get('ghana_card')
                )
            if request.FILES.get('national_id'):
                SupportingDocuments.objects.create(
                    loan_application=loan,
                    document_type=SupportingDocuments.DocumentType.NATIONAL_ID,
                    document=request.FILES.get('national_id')
                )
            if request.FILES.get('financial_statement'):
                SupportingDocuments.objects.create(
                    loan_application=loan,
                    document_type=SupportingDocuments.DocumentType.FINANCIAL_STATEMENT,
                    document=request.FILES.get('financial_statement')
                )
            if request.FILES.get('other_document'):
                SupportingDocuments.objects.create(
                    loan_application=loan,
                    document_type=SupportingDocuments.DocumentType.OTHER,
                    document=request.FILES.get('other_document')
                )

            # --- CACHE INVALIDATION ---
            # Data changed, wipe specific detail cache and active list cache
            invalidate_loan_cache(loan.id, request.user.id)

            messages.success(request, "Loan application updated successfully.")
            return redirect('loan:application_status', loan_id=loan.id)
    else:
        form = LoanApplicationForm(instance=loan)

    context = {'form': form, 'loan': loan, 'title': 'Update Loan Application'}
    return render(request, 'loan/apply.html', context)  # Reusing apply template


@login_required
def delete_loan_application(request, loan_id):

    if request.user.role != "loan_officer":
        messages.warning(request, "You are not authorized to view this loan.")
        return redirect('loan:application_status', loan_id=loan_id)

    """
    Allows borrower to delete a SUBMITTED application.
    Handles cache invalidation.
    """
    loan = get_object_or_404(Loan, id=loan_id, borrower=request.user)


    if loan.application_status != Loan.ApplicationStatus.SUBMITTED:
        messages.error(request, "Cannot delete an application that is actively being verified.")
        return redirect('loan:application_status', loan_id=loan.id)

    if request.method == 'POST':
        borrower_id = loan.borrower.id
        loan.delete()

        invalidate_loan_cache(loan_id, borrower_id)

        messages.success(request, "Loan application deleted permanently.")
        return redirect('account:dashboard')

    context = {'loan': loan, 'title': 'Delete Application'}
    return render(request, 'loan/delete_confirm.html', context)

