from django.urls import path
from apps.transactions.views import (
    borrower_pay_loan_view,
    loan_officer_disburse_loan_view,
    approved_loans_disbursement_list_view,
    payment_verification_callback_view,
    paystack_webhook_view,
    loan_officer_transactions_list_view,
    borrower_transactions_list_view,
    initiate_loan_repayment_view,
    verify_loan_repayment_view,
)

app_name = "transactions"

urlpatterns = [
    # Borrower URLs
    path("pay/loan/<uuid:loan_id>/", borrower_pay_loan_view, name="borrower_pay_loan"),
    path("my/history/", borrower_transactions_list_view, name="borrower_transactions"),
    path("repay/<uuid:loan_id>/", initiate_loan_repayment_view, name="initiate_repayment"),
    path("repay/verify/<str:reference>/", verify_loan_repayment_view, name="verify_repayment"),

    # Loan Officer URLs
    path("disburse/", approved_loans_disbursement_list_view, name="loan_officer_disburse_select"),
    path("disburse/loan/<uuid:loan_id>/", loan_officer_disburse_loan_view, name="loan_officer_disburse"),
    path("officer/history/", loan_officer_transactions_list_view, name="loan_officer_transactions"),

    # Gateway Callbacks & Webhooks
    path("verify/", payment_verification_callback_view, name="payment_verification"),
    path("webhook/", paystack_webhook_view, name="paystack_webhook"),
]