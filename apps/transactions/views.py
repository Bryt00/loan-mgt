import json
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from apps.loan.models import Loan
from apps.transactions.forms import LoanDisbursementForm, LoanRepaymentForm
from apps.transactions.models import Payment, Transaction
from apps.transactions.tasks import process_paystack_webhook_event
from apps.transactions.utils import PaystackService


def is_loan_officer(user):
    """
    Verify that the user is authenticated and is a loan officer.
    """
    return user.is_authenticated and getattr(user, 'role', None) == user.Role.LOAN_OFFICER


@login_required
def borrower_pay_loan_view(request, loan_id):
    """
    Allows a borrower to initiate a payment/repayment for their due loan via Paystack.
    Uses borrower_app/borrower_base.html layout.
    """
    loan = get_object_or_404(Loan, id=loan_id, borrower=request.user)

    if request.method == "POST":
        form = LoanRepaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            reference = f"REP-{uuid.uuid4().hex[:12].upper()}"


            payment = Payment.objects.create(
                user=request.user,
                loan=loan,
                amount=amount,
                reference=reference,
                payment_type=Payment.PaymentType.REPAYMENT,
                status=Payment.PaymentStatus.PENDING,
            )

            # Initialize Paystack Checkout
            callback_url = request.build_absolute_uri(f"/transactions/verify/?reference={reference}")
            response = PaystackService.initialize_payment(
                email=request.user.email,
                amount=amount,
                reference=reference,
                callback_url=callback_url,
                metadata={"loan_id": str(loan.id), "payment_id": str(payment.id)}
            )

            if response["success"]:
                return redirect(response["authorization_url"])
            else:
                payment.status = Payment.PaymentStatus.FAILED
                payment.save()
                messages.error(request, f"Payment initialization failed: {response.get('message')}")
    else:
        form = LoanRepaymentForm(initial={'amount': loan.amount})

    context = {
        "loan": loan,
        "form": form,
        "base_template": "borrower_app/borrower_base.html",
        "title": f"Pay Loan #{loan.id}"
    }
    return render(request, "transactions/borrower_pay_loan.html", context)


@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def loan_officer_disburse_loan_view(request, loan_id):
    """
    Allows a loan officer to disburse an approved loan to the borrower via Paystack Transfer.
    On GET: fetches live Ghana bank / MoMo provider list from Paystack for the form.
    On POST: auto-creates a Paystack Transfer Recipient from the submitted account details,
             then immediately initiates the transfer — no manual recipient code needed.
    """
    loan = get_object_or_404(Loan, id=loan_id, application_status=Loan.ApplicationStatus.APPROVED)

    # Fetch live Ghana banks / MoMo providers from Paystack for the form dropdown
    bank_choices = None
    try:
        banks_result = PaystackService.list_banks(country="ghana")
        if banks_result["success"] and banks_result["banks"]:
            bank_choices = [
                (b["code"], b["name"])
                for b in banks_result["banks"]
                if b.get("code") and b.get("name")
            ]
    except Exception:
        pass  # Fall back to hardcoded defaults in the form

    if request.method == "POST":
        form = LoanDisbursementForm(request.POST, bank_choices=bank_choices)
        if form.is_valid():
            transfer_type = form.cleaned_data["transfer_type"]
            account_name = form.cleaned_data["account_name"]
            account_number = form.cleaned_data["account_number"]
            bank_code = form.cleaned_data["bank_code"]
            amount = loan.amount
            reference = f"DISB-{uuid.uuid4().hex[:12].upper()}"

            # Step 1: Auto-create a Paystack Transfer Recipient
            recipient_result = PaystackService.create_transfer_recipient(
                transfer_type=transfer_type,
                name=account_name,
                account_number=account_number,
                bank_code=bank_code,
                currency="GHS",
            )

            if not recipient_result["success"]:
                messages.error(
                    request,
                    f"Could not register recipient with Paystack: {recipient_result.get('message')}. "
                    "Please check the account details and try again."
                )
                context = {
                    "loan": loan, "form": form,
                    "base_template": "loan_officer_app/loan_officer_base.html",
                    "title": f"Disburse Loan #{loan.id}",
                }
                return render(request, "transactions/loan_officer_disburse.html", context)

            recipient_code = recipient_result["recipient_code"]

            # Step 2: Record the pending disbursement payment
            payment = Payment.objects.create(
                user=loan.borrower,
                loan=loan,
                amount=amount,
                reference=reference,
                payment_type=Payment.PaymentType.DISBURSEMENT,
                status=Payment.PaymentStatus.PENDING,
            )

            # Step 3: Initiate the Paystack Transfer
            transfer_result = PaystackService.initiate_transfer(
                amount=amount,
                recipient_code=recipient_code,
                reference=reference,
                reason=f"Loan disbursement #{loan.id} — {account_name}",
            )

            if transfer_result["success"]:
                loan.application_status = Loan.ApplicationStatus.DISBURSED
                loan.save()
                messages.success(
                    request,
                    f"✅ Disbursement of GH¢{amount:,.2f} initiated successfully to {account_name} "
                    f"({account_number}). Transfer status: {transfer_result.get('status', 'pending').upper()}."
                )
                return redirect("loan_officer_app:loan_officer_dashboard")
            else:
                payment.status = Payment.PaymentStatus.FAILED
                payment.save()
                messages.error(
                    request,
                    f"Transfer failed after recipient was created: {transfer_result.get('message')}. "
                    "Contact Paystack support if funds were deducted."
                )
    else:
        # Pre-fill account name with borrower's full name as a convenience
        borrower_name = loan.borrower.full_name or loan.borrower.email
        form = LoanDisbursementForm(
            initial={"account_name": borrower_name},
            bank_choices=bank_choices,
        )

    context = {
        "loan": loan,
        "form": form,
        "base_template": "loan_officer_app/loan_officer_base.html",
        "title": f"Disburse Loan #{loan.id}",
    }
    return render(request, "transactions/loan_officer_disburse.html", context)


@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def approved_loans_disbursement_list_view(request):
    """
    View for a loan officer to browse all APPROVED loans ready for Paystack disbursement.
    Renders using the loan_officer_app/loan_officer_base.html layout.
    """
    approved_loans = Loan.objects.filter(application_status=Loan.ApplicationStatus.APPROVED).select_related('borrower').order_by('-submission_date')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        approved_loans = approved_loans.filter(
            Q(borrower__first_name__icontains=search_query) |
            Q(borrower__last_name__icontains=search_query) |
            Q(borrower__email__icontains=search_query) |
            Q(id__icontains=search_query)
        )

    paginator = Paginator(approved_loans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "approved_loans": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "base_template": "loan_officer_app/loan_officer_base.html",
        "title": "Disburse Approved Loans"
    }
    return render(request, "transactions/approved_loans_disbursement_list.html", context)


@login_required
def payment_verification_callback_view(request):
    """
    Handles redirect callback from Paystack after user completes checkout flow.
    Routes back to appropriate dashboard based on user role.
    """
    reference = request.GET.get("reference")
    if not reference:
        messages.error(request, "No transaction reference provided.")
        return redirect("core:dashboard")

    verification = PaystackService.verify_transaction(reference)
    if verification["success"] and verification["status"] == "success":
        messages.success(request, "Transaction verified successfully!")
    else:
        messages.warning(request, "Transaction verification is pending or failed. We will update you shortly.")

    if is_loan_officer(request.user):
        return redirect("loan_officer_app:dashboard")
    return redirect("borrower_app:dashboard")


@csrf_exempt
def paystack_webhook_view(request):
    """
    Secure endpoint that receives automated server-to-server webhook updates from Paystack.
    Delegates event execution to the Celery background task.
    """
    if not PaystackService.verify_webhook_signature(request):
        return HttpResponse(status=400)

    try:
        event_data = json.loads(request.body.decode("utf-8"))
        # Trigger background task asynchronously via Celery
        process_paystack_webhook_event.delay(event_data)
    except Exception:
        return HttpResponse(status=400)

    return HttpResponse(status=200)


@login_required
@user_passes_test(is_loan_officer, login_url='account:login')
def loan_officer_transactions_list_view(request):
    """
    View for a loan officer to view all platform transactions with search and pagination.
    Renders using the loan_officer_app/loan_officer_base.html layout.
    """
    transactions = Transaction.objects.select_related('user', 'wallet').order_by('-created_at')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        transactions = transactions.filter(
            Q(reference__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "transactions": page_obj,
        "search_query": search_query,
        "base_template": "loan_officer_app/loan_officer_base.html",
        "title": "All Transactions (Loan Officer)"
    }
    return render(request, "transactions/loan_officer_transactions_list.html", context)


@login_required
def borrower_transactions_list_view(request):
    """
    View for a borrower to view only their own transaction history.
    Renders using the borrower_app/borrower_base.html layout.
    """
    transactions = Transaction.objects.filter(user=request.user).select_related('wallet').order_by('-created_at')

    search_query = request.GET.get('q', '').strip()
    if search_query:
        transactions = transactions.filter(
            Q(reference__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    paginator = Paginator(transactions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "transactions": page_obj,
        "search_query": search_query,
        "base_template": "borrower_app/borrower_base.html",
        "title": "My Transaction History"
    }
    return render(request, "transactions/borrower_transactions_list.html", context)


@login_required
def initiate_loan_repayment_view(request, loan_id):
    """
    Allows a borrower to initiate a payment towards an active loan.
    Validates amount against remaining balance and initializes Paystack payment.
    """
    # Restrict retrieval to active/disbursed loans belonging to the logged-in borrower
    loan = get_object_or_404(
        Loan,
        id=loan_id,
        borrower=request.user,
        application_status=Loan.ApplicationStatus.DISBURSED
    )

    remaining_balance = loan.outstanding_balance  # Assuming dynamic property or field

    if request.method == "POST":
        form = LoanRepaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]

            # 1. Custom Validation: Ensure borrower does not overpay
            if amount > remaining_balance:
                form.add_error(
                    "amount",
                    f"Repayment amount cannot exceed your remaining balance of GH¢{remaining_balance:,.2f}."
                )
            else:
                reference = f"REPAY-{uuid.uuid4().hex[:12].upper()}"
                callback_url = request.build_absolute_uri(
                    reverse("verify_repayment", kwargs={"reference": reference})
                )

                # Metadata passed to Paystack for webhooks or tracking
                metadata = {
                    "loan_id": loan.id,
                    "borrower_id": request.user.id,
                    "payment_type": "loan_repayment",
                }

                # 2. Initialize Paystack Transaction
                paystack_response = PaystackService.initialize_payment(
                    email=request.user.email,
                    amount=amount,
                    reference=reference,
                    callback_url=callback_url,
                    metadata=metadata,
                )

                if paystack_response["success"]:
                    # 3. Create Pending Payment Record
                    Payment.objects.create(
                        user=request.user,
                        loan=loan,
                        amount=amount,
                        reference=reference,
                        payment_type=Payment.PaymentType.REPAYMENT,
                        status=Payment.PaymentStatus.PENDING,
                    )

                    # Redirect user to Paystack Checkout URL
                    return redirect(paystack_response["authorization_url"])
                else:
                    messages.error(
                        request,
                        f"Could not initialize checkout: {paystack_response.get('message')}. Please try again."
                    )
    else:
        # Pre-fill form with remaining balance as default suggestion
        form = LoanRepaymentForm(initial={"amount": remaining_balance})

    context = {
        "loan": loan,
        "form": form,
        "remaining_balance": remaining_balance,
        "title": f"Repay Loan #{loan.id}",
    }
    return render(request, "transactions/borrower_repay_loan.html", context)


@login_required
def verify_loan_repayment_view(request, reference):
    """
    Callback target after Paystack redirect. Verifies the transaction
    and updates payment and loan records.
    """
    payment = get_object_or_404(
        Payment,
        reference=reference,
        user=request.user,
        payment_type=Payment.PaymentType.REPAYMENT
    )

    # Avoid processing already finalized transactions
    if payment.status == Payment.PaymentStatus.SUCCESS:
        messages.info(request, "This payment has already been verified and processed.")
        return redirect("borrower_dashboard")

    # Verify transaction with Paystack API
    verification = PaystackService.verify_transaction(reference)

    if verification["success"] and verification.get("status") == "success":
        payment.status = Payment.PaymentStatus.SUCCESS
        payment.save()

        # Update loan outstanding balance
        loan = payment.loan
        loan.outstanding_balance -= payment.amount

        # Mark loan as fully settled if balance hits 0
        if loan.outstanding_balance <= Decimal("0.00"):
            loan.outstanding_balance = Decimal("0.00")
            loan.application_status = Loan.ApplicationStatus.APPROVED  # adjust status name as needed

        loan.save()

        messages.success(
            request,
            f"✅ Payment of GH¢{payment.amount:,.2f} verified successfully! Your updated balance is GH¢{loan.outstanding_balance:,.2f}."
        )
    else:
        payment.status = Payment.PaymentStatus.FAILED
        payment.save()
        messages.error(
            request,
            "❌ Payment verification failed or transaction was cancelled. Please check your payment source and try again."
        )

    return redirect("borrower_app:borrower_dashboard")