from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.account.models import User
from apps.loan.models import Loan, SupportingDocuments
from apps.video_session.models import VideoSession


@login_required
def borrower_dashboard(request):
    if request.user.role != request.user.Role.BORROWER:
        messages.error(request, "You are not authorized to view this page.")
        return redirect("account:home")

    # Cache key is versioned ("v2") so a stale entry written under the old
    # shape (which stored model instances directly) can never be read back
    # here. Bump this tag whenever the cached payload's shape changes.
    cache_key = f"borrower_dashboard_metrics_v2_{request.user.id}"
    metrics = cache.get(cache_key)

    # Loans are ALWAYS fetched fresh, never cached. Caching real model
    # instances was the root cause of the original bug: a stale/mismatched
    # cache entry served objects that weren't proper Loan instances, so
    # `loan.id` in the template resolved to a whole row-tuple instead of a
    # UUID and blew up `{% url %}`. Live status also matters here, so this
    # data shouldn't be cached anyway.
    borrower_loans = Loan.objects.filter(borrower=request.user).order_by(
        "-submission_date"
    )
    loans = list(borrower_loans[:5])

    if metrics is None:
        total_borrowed = (
            borrower_loans.filter(
                application_status=Loan.ApplicationStatus.DISBURSED
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        max_limit = getattr(
            request.user,
            "max_credit_limit",
            Decimal("40000.00"),
        )

        active_loans = borrower_loans.filter(
            application_status__in=[
                Loan.ApplicationStatus.APPROVED,
                Loan.ApplicationStatus.DISBURSED,
            ]
        )

        active_balance_sum = (
            active_loans.aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        available_credit_limit = max_limit - active_balance_sum

        next_payment = (
            borrower_loans.filter(
                application_status=Loan.ApplicationStatus.DISBURSED
            )
            .order_by("submission_date")
            .first()
        )

        next_payment_amount = (
            getattr(next_payment, "amount", Decimal("980.00"))
            if next_payment
            else Decimal("0.00")
        )

        next_payment_date = (
            getattr(next_payment, "decision_date", None)
            if next_payment
            else None
        )

        latest_loan = borrower_loans.first()
        risk_score = getattr(latest_loan, "risk_score", None) or 720

        raw_risk_tier = getattr(latest_loan, "risk_tier", None)

        if raw_risk_tier is not None:
            risk_tier = f"Tier {raw_risk_tier}"
        else:
            risk_tier = "Tier 1"

        # Only plain, cache-safe values live in here — Decimals, ints,
        # dates, strings. No model instances, no querysets, ever.
        metrics = {
            "total_borrowed": total_borrowed,
            "active_loans_count": active_loans.count(),
            "available_credit_limit": available_credit_limit,
            "max_limit": max_limit,
            "credit_score": risk_score,
            "risk_tier": risk_tier,
            "next_payment_amount": next_payment_amount,
            "next_payment_date": next_payment_date,
        }

        cache.set(cache_key, metrics, timeout=300)

    context = {
        "loans": loans,
        "total_borrowed": metrics["total_borrowed"],
        "active_loans_count": metrics["active_loans_count"],
        "available_credit_limit": metrics["available_credit_limit"],
        "max_limit": metrics["max_limit"],
        "credit_score": metrics["credit_score"],
        "risk_tier": metrics["risk_tier"],
        "next_payment_amount": metrics["next_payment_amount"],
        "next_payment_date": metrics["next_payment_date"],
        "active_loan": borrower_loans.filter(
            application_status__in=[
                Loan.ApplicationStatus.APPROVED,
                Loan.ApplicationStatus.DISBURSED,
            ]
        ).first(),
        "title": "Borrower Dashboard",
    }

    return render(request, "borrower_app/dashboard.html", context)


@login_required
def borrower_loans_list(request):
    if request.user.role != request.user.Role.BORROWER:
        messages.error(request, "You are not authorized to view this page.")
        return redirect("account:home")

    borrower_loans = Loan.objects.filter(borrower=request.user).order_by(
        "-submission_date"
    )

    paginator = Paginator(borrower_loans, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "loans": page_obj,
        "page_obj": page_obj,
        "title": "My Loan Applications",
    }

    return render(request, "borrower_app/loans_list.html", context)


@login_required
def borrower_loan_detail(request, loan_id):
    if request.user.role != request.user.Role.BORROWER:
        messages.error(request, "You are not authorized to view this page.")
        return redirect("account:home")

    loan = get_object_or_404(Loan, id=loan_id, borrower=request.user)
    documents = loan.documents.all()

    context = {
        "loan": loan,
        "documents": documents,
        "title": f"Loan Application #{loan.id}",
    }

    return render(request, "borrower_app/loan_detail.html", context)


@login_required
def borrower_documents_list(request):
    if request.user.role != request.user.Role.BORROWER:
        messages.error(request, "You are not authorized to view this page.")
        return redirect("account:home")

    documents = SupportingDocuments.objects.filter(
        loan_application__borrower=request.user
    ).order_by("-created_at")

    context = {
        "title": "My Documents",
        "documents": documents,
    }

    return render(
        request,
        "borrower_app/borrower_documents_list.html",
        context,
    )


@login_required
def borrower_document_detail(request, document_id):
    if request.user.role != request.user.Role.BORROWER:
        messages.error(request, "You are not authorized to view this page.")
        return redirect("account:home")

    document = get_object_or_404(
        SupportingDocuments,
        id=document_id,
        loan_application__borrower=request.user,
    )

    context = {
        "title": "Document Details",
        "document": document,
    }

    return render(request, "borrower_app/document_detail.html", context)


@login_required
def borrower_video_sessions_list(request, borrower_id=None):
    """Display a cached list of video sessions for a specific borrower.
    If no borrower_id is provided, defaults to the currently logged-in user.
    """
    if borrower_id is None:
        borrower = request.user
    else:
        borrower = get_object_or_404(User, id=borrower_id)

    # Optional security check: Ensure only officers or the borrower themselves can view this
    if (
        not getattr(request.user, "is_officer", False)
        and request.user != borrower
    ):
        messages.error(
            request, "You do not have permission to view these video sessions."
        )
        return redirect("borrower_app:borrower_dashboard")

    # NOTE: same class of bug as the old dashboard view lived here too —
    # caching real VideoSession instances under an unversioned key. Fetching
    # fresh each time is cheap (it's a single select_related'd query) and
    # avoids ever serving stale/mismatched objects to the template.
    sessions = (
        VideoSession.objects.filter(borrower=borrower)
        .select_related("loan", "borrower", "loan_officer")
        .order_by("-schedule_date", "-schedule_time")
    )

    context = {
        "title": f"Video Sessions for {getattr(borrower, 'full_name', None) or getattr(borrower, 'email', 'Borrower')}",
        "borrower": borrower,
        "sessions": sessions,
    }
    return render(request, "borrower_app/borrower_video_sessions_list.html", context)

# @login_required
# def video_session_detail(request, pk):
#     cache_key = f"video_session_detail_{pk}"
#     session = cache.get(cache_key)
#
#     if session is None:
#         session = get_object_or_404(
#             VideoSession.objects.select_related(
#                 "loan",
#                 "borrower",
#                 "loan_officer",
#             ),
#             pk=pk,
#         )
#
#         cache.set(cache_key, session, timeout=300)
#
#     if (
#         request.user != session.borrower
#         and request.user != session.loan_officer
#         and not getattr(request.user, "is_staff", False)
#     ):
#         messages.error(
#             request,
#             "You do not have permission to view this video session.",
#         )
#         return redirect("borrower_app:video_session_list")
#
#     context = {
#         "title": f"Video Session Details - #{session.pk}",
#         "session": session,
#     }
#
#     return render(
#         request,
#         "borrower_app/video_session_detail.html",
#         context,
#     )