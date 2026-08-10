import csv

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q, Sum, Count
from django.http import HttpResponse
from django.shortcuts import render

from apps.loan.forms import LoanNoteForm
from apps.loan.models import Loan, LoanNote
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone


def is_loan_officer(user):
    """
    Verify that the user is authenticated and is a loan officer.
    """
    return (
            user.is_authenticated
            and user.role == user.Role.LOAN_OFFICER
    )


@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def loan_officer_dashboard(request):
    search_query = request.GET.get('q', '').strip()

    # Total Loans count
    total_loans = Loan.objects.count()

    # Status-based metrics matching the correct model field 'application_status'
    status_counts = Loan.objects.values('application_status').annotate(count=Count('id'))
    status_map = {item['application_status']: item['count'] for item in status_counts}

    # Using actual choices from model: SUB (Submitted), UNDR (Under Review), AP (Approved)
    pending_loans_count = status_map.get(Loan.ApplicationStatus.SUBMITTED, 0)
    in_review_count = status_map.get(Loan.ApplicationStatus.UNDER_REVIEW, 0)
    approved_loans_count = status_map.get(Loan.ApplicationStatus.APPROVED, 0)

    # Financial total calculation for approved loans
    total_disbursed = \
    Loan.objects.filter(application_status=Loan.ApplicationStatus.APPROVED).aggregate(total=Sum('amount'))[
        'total'] or 0.00
    total_disbursed_formatted = f"GH¢ {total_disbursed:,.2f}"

    # Base queryset for loans
    loans_queryset = Loan.objects.select_related('borrower')

    # Apply search filter across borrower and loan fields
    if search_query:
        loans_queryset = loans_queryset.filter(
            Q(borrower__full_name__icontains=search_query) |
            Q(borrower__email__icontains=search_query) |
            Q(id__icontains=search_query)
        )

    # Recent loan applications ordered by model field 'submission_date'
    recent_loans = loans_queryset.order_by('-submission_date')[:5]

    context = {
        'total_loans': total_loans,
        'pending_loans_count': pending_loans_count,
        'in_review_count': in_review_count,
        'approved_loans_count': approved_loans_count,
        'total_disbursed_formatted': total_disbursed_formatted,
        'recent_loans': recent_loans,
        'search_query': search_query,
    }

    return render(request, 'loan_officer_app/loan_officer_dashboard.html', context)


@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def loan_application_related_loan_officer(request):
    loans_applications = Loan.objects.filter(
        loan_officer=request.user,
        application_status__in=[
            Loan.ApplicationStatus.APPROVED,
            Loan.ApplicationStatus.DISBURSED
        ]
    ).select_related('borrower').prefetch_related('documents').order_by('-submission_date')

    # Paginate the list (Show 10 applications per page)
    paginator = Paginator(loans_applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'loans_applications': page_obj,
    }

    return render(
        request,
        'loan_officer_app/loan_applications_list.html',
        context,
    )

@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def pending_loan_applications(request):
    loans_applications = Loan.objects.filter(
        loan_officer=request.user,
        application_status__in=[
            Loan.ApplicationStatus.SUBMITTED,
            Loan.ApplicationStatus.VERIFYING,
            Loan.ApplicationStatus.UNDER_REVIEW,
            Loan.ApplicationStatus.SCHEDULED
        ]
    ).select_related('borrower').prefetch_related('documents').order_by('-submission_date')

    # Paginate the list (Show 10 applications per page)
    paginator = Paginator(loans_applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'loans_applications': page_obj,
    }

    return render(
        request,
        'loan_officer_app/pending_loan_applications.html',
        context,
    )

@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def review_approved_disbursed_loan(request, loan_id):
    """
    Detailed review view for a single approved or disbursed loan application
    assigned to the logged-in loan officer.
    """
    loan = get_object_or_404(
        Loan.objects.select_related('borrower').prefetch_related('documents'),
        id=loan_id,
        loan_officer=request.user,
        application_status__in=[
            Loan.ApplicationStatus.APPROVED,
            Loan.ApplicationStatus.DISBURSED
        ]
    )

    context = {
        'loan': loan,
        'documents': loan.documents.all(),
    }

    return render(
        request,
        'loan_officer_app/review_approved_disbursed_loan.html',
        context,
    )

@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def review_pending_loan(request, loan_id):
    """
    Detailed review view for a single pending loan application
    assigned to the logged-in loan officer.
    """
    loan = get_object_or_404(
        Loan.objects.select_related('borrower').prefetch_related('documents'),
        id=loan_id,
        loan_officer=request.user,
        application_status__in=[
            Loan.ApplicationStatus.SUBMITTED,
            Loan.ApplicationStatus.VERIFYING,
            Loan.ApplicationStatus.UNDER_REVIEW,
            Loan.ApplicationStatus.SCHEDULED
        ]
    )

    if request.method == "POST":
        action = request.POST.get("action")
        decision_notes = request.POST.get("decision_notes", "").strip()

        if action == "approve":
            loan.application_status = Loan.ApplicationStatus.APPROVED
            loan.decision_date = timezone.now()
            if decision_notes:
                loan.decision_notes = decision_notes
            loan.save()

            # Cache clearing removed as lists are no longer cached

            messages.success(request, f"Loan #{loan.id} has been APPROVED! You can now disburse funds.")
            return redirect("transactions:loan_officer_disburse", loan_id=loan.id)

        elif action == "reject":
            loan.application_status = Loan.ApplicationStatus.REJECTED
            loan.decision_date = timezone.now()
            if decision_notes:
                loan.decision_notes = decision_notes
            loan.save()

            # Cache clearing removed as lists are no longer cached

            messages.info(request, f"Loan #{loan.id} has been REJECTED.")
            return redirect("loan_officer_app:pending_loan_applications")

    context = {
        'loan': loan,
        'documents': loan.documents.all(),
    }

    return render(
        request,
        'loan_officer_app/review_pending_loan.html',
        context,
    )


@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def loan_officer_borrowers(request):
    """
    Fetch all unique borrowers associated with the logged-in loan officer,
    along with a complete prefetch of all their related loans and supporting documents,
    utilizing Redis/Memcached caching.
    """
    # Fetch unique borrowers who have at least one loan assigned to this loan officer,
    # and prefetch all loans and their related documents for each borrower using 'borrowed_loans'.
    borrowers = get_user_model().objects.filter(
        borrowed_loans__loan_officer=request.user
    ).prefetch_related(
        Prefetch(
            'borrowed_loans',
            queryset=Loan.objects.filter(loan_officer=request.user)
            .prefetch_related('documents')
            .order_by('-submission_date')
        )
    ).distinct()

    # Paginate the borrowers list (Show 10 borrowers per page)
    paginator = Paginator(borrowers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'borrowers': page_obj,
    }

    return render(
        request,
        'loan_officer_app/loan_officer_borrowers.html',
        context,
    )

@login_required
@user_passes_test(is_loan_officer, login_url="account:login")
def loan_officer_borrower_documents_view(request, loan_id):
    """View for a loan officer to fetch all supporting documents

    for a specific loan application of a borrower they manage.
    """
    loan = get_object_or_404(
        Loan.objects.select_related("borrower", "loan_officer"),
        id=loan_id,
        loan_officer=request.user,
    )

    if request.method == "POST":
        document_id = request.POST.get("document_id")
        action = request.POST.get("action")
        notes = request.POST.get("verification_notes", "").strip()

        if document_id and action:
            from apps.loan.models import SupportingDocuments
            doc = get_object_or_404(SupportingDocuments, id=document_id, loan_application=loan)
            if action == "verify":
                doc.verification_status = True
            elif action == "unverify":
                doc.verification_status = False
            
            if notes:
                doc.verification_notes = notes
            doc.save()
            messages.success(request, f"Document '{doc.get_document_type_display()}' updated successfully.")
            return redirect("loan_officer_app:loan_officer_borrower_documents", loan_id=loan.id)

    documents = loan.documents.all()

    pending_count = documents.filter(verification_status=False).count()
    verified_count = documents.filter(verification_status=True).count()
    rejected_count = 0

    context = {
        "title": f"Documents for Loan #{loan.id}",
        "loan": loan,
        "borrower": loan.borrower,
        "documents": documents,
        "pending_count": pending_count,
        "verified_count": verified_count,
        "rejected_count": rejected_count,
    }

    return render(
        request, "loan_officer_app/loan_officer_documents.html", context
    )

@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def loan_officer_documents_list(request):
    """Lists all supporting documents for loans managed by the logged-in officer."""
    from apps.loan.models import SupportingDocuments
    search_query = request.GET.get('q', '').strip()

    documents = SupportingDocuments.objects.select_related(
        'loan_application', 'loan_application__borrower'
    ).filter(
        loan_application__loan_officer=request.user
    )

    if search_query:
        documents = documents.filter(
            Q(loan_application__borrower__email__icontains=search_query)
            | Q(loan_application__borrower__full_name__icontains=search_query)
            | Q(document_type__icontains=search_query)
        )

    documents = documents.order_by('-created_at')

    pending_count = documents.filter(verification_status=False).count()
    verified_count = documents.filter(verification_status=True).count()

    context = {
        'title': 'Documents',
        'documents': documents,
        'pending_count': pending_count,
        'verified_count': verified_count,
        'rejected_count': 0,
        'search_query': search_query,
    }
    return render(
        request, 'loan_officer_app/loan_officer_documents_list.html', context
    )



@login_required
def generate_reports_view(request):
    """View to handle report filtering, analytics summaries, and CSV data exports using the Loan model."""
    report_type = request.GET.get('type', 'summary')
    format_type = request.GET.get('format', 'html')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status_filter = request.GET.get('status')
    employment_filter = request.GET.get('employment')
    search_query = request.GET.get('q', '').strip()


    loans = Loan.objects.all()

    if date_from:
        loans = loans.filter(submission_date__gte=date_from)
    if date_to:
        loans = loans.filter(submission_date__lte=date_to)

    if status_filter:
        loans = loans.filter(application_status=status_filter)

    if employment_filter:
        loans = loans.filter(employment_status=employment_filter)


    if search_query:
        loans = loans.filter(
            Q(borrower__email__icontains=search_query)
            | Q(employer_name__icontains=search_query)
            | Q(purpose__icontains=search_query)
        )

    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="smartloan_report.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                'Loan ID',
                'Borrower Email',
                'Amount',
                'Employment Status',
                'Employer Name',
                'Application Status',
                'Submission Date',
            ]
        )

        for loan in loans.select_related('borrower'):
            writer.writerow([
                str(loan.id),
                loan.borrower.email if loan.borrower else 'N/A',
                loan.amount,
                loan.get_employment_status_display(),
                loan.employer_name or 'N/A',
                loan.get_application_status_display(),
                (
                    loan.submission_date.strftime('%Y-%m-%d %H:%M')
                    if loan.submission_date
                    else ''
                ),
            ])
        return response

    # Aggregate Metrics for HTML Dashboard Report
    total_loans = loans.count()
    approved_loans = loans.filter(
        application_status=Loan.ApplicationStatus.APPROVED
    ).count()
    pending_loans = loans.filter(
        application_status=Loan.ApplicationStatus.SUBMITTED
    ).count()
    disbursed_loans = loans.filter(
        application_status=Loan.ApplicationStatus.DISBURSED
    ).count()

    context = {
        'total_loans': total_loans,
        'approved_loans': approved_loans,
        'pending_loans': pending_loans,
        'disbursed_loans': disbursed_loans,
        'loans': loans.select_related('borrower')[
            :50
        ],
        'report_type': report_type,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'employment_filter': employment_filter,
        'search_query': search_query,
        'application_statuses': Loan.ApplicationStatus.choices,
        'employment_statuses': Loan.EmploymentStatus.choices,
    }

    return render(
        request, 'loan_officer_app/loan_officer_reports.html', context
    )

@login_required
@user_passes_test(is_loan_officer, login_url="account:login")
def loan_officer_calculator_view(request):
    """View for loan officers to access the interactive loan repayment

    and amortization calculator.
    """
    context = {
        "title": "Loan Calculator",
    }
    return render(
        request, "loan_officer_app/loan_officer_calculator.html", context
    )

@login_required
@user_passes_test(is_loan_officer, login_url="account:login")
def loan_officer_notes_view(request, loan_id):
    """View to list, create, update, and delete internal notes for a specific loan application."""
    loan = get_object_or_404(
        Loan.objects.select_related("borrower", "loan_officer"),
        id=loan_id,
        loan_officer=request.user,
    )

    note_id = request.GET.get("edit_note_id")
    note_instance = None
    if note_id:
        note_instance = get_object_or_404(LoanNote, id=note_id, loan=loan)

    if request.method == "POST":
        action = request.POST.get("action")


        if action == "delete":
            del_note_id = request.POST.get("note_id")
            note_to_delete = get_object_or_404(LoanNote, id=del_note_id, loan=loan)

            note_to_delete.delete()
            return redirect("loan_officer_app:loan_officer_notes", loan_id=loan.id)


        form = LoanNoteForm(request.POST, instance=note_instance)
        if form.is_valid():
            note = form.save(commit=False)
            note.loan = loan
            if not note.pk:
                note.author = request.user
            note.save()
            return redirect("loan_officer_app:loan_officer_notes", loan_id=loan.id)
    else:
        form = LoanNoteForm(instance=note_instance)

    notes = loan.notes.select_related("author").order_by("-created_at")

    context = {
        "title": f"Notes for Loan #{loan.id}",
        "loan": loan,
        "borrower": loan.borrower,
        "notes": notes,
        "form": form,
        "editing_note": note_instance,
    }
    return render(request, "loan_officer_app/loan_officer_notes.html", context)