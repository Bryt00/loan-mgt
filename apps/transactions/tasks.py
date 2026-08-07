from decimal import Decimal
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from apps.transactions.models import Payment, Transaction, Wallet
from apps.transactions.utils import PaystackService
from apps.loan.models import Loan


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_paystack_webhook_event(self, event_data):
    """
    Background task to process verified Paystack webhook events asynchronously
    ensuring idempotency, wallet updates, and email notifications.
    """
    event = event_data.get("event")
    data = event_data.get("data", {})
    reference = data.get("reference")

    if not reference:
        return {"status": "ignored", "reason": "No reference found in event data"}

    try:
        if event == "charge.success":
            # Handle Loan Repayments or Wallet Top-ups
            with transaction.atomic():
                payment = Payment.objects.select_for_update().filter(reference=reference).first()

                if not payment or payment.status == Payment.PaymentStatus.SUCCESS:
                    return {"status": "skipped", "reason": "Payment not found or already processed (Idempotent)"}

                # Update Payment record
                payment.status = Payment.PaymentStatus.SUCCESS
                payment.channel = data.get("channel")
                payment.paystack_response = event_data
                payment.save()

                amount = payment.amount
                user = payment.user

                # Create Ledger Transaction Record
                Transaction.objects.create(
                    user=user,
                    wallet=getattr(user, "wallet", None),
                    reference=reference,
                    amount=amount,
                    transaction_type=Transaction.TransactionType.CREDIT,
                    status=Transaction.TransactionStatus.SUCCESS,
                    description=f"Successful {payment.get_payment_type_display()} via Paystack"
                )

                # Handle specific payment types
                if payment.payment_type == Payment.PaymentType.WALLET_TOPUP:
                    wallet, _ = Wallet.objects.get_or_create(user=user)
                    wallet.balance += amount
                    wallet.save()

                elif payment.payment_type == Payment.PaymentType.REPAYMENT and payment.loan:
                    loan = payment.loan
                    # Reduce loan balance / check completion here if applicable
                    # e.g., loan.amount_paid += amount; loan.save()

            # Send Email Notification asynchronously
            send_transaction_email.delay(
                user_email=user.email,
                subject="Payment Successful - SmartLoan",
                message=f"Hello {user.first_name},\n\nYour payment of GH¢ {amount:,.2f} (Ref: {reference}) was successfully received and processed.\n\nThank you for choosing SmartLoan."
            )
            return {"status": "success", "reference": reference}

        elif event == "transfer.success":
            # Handle successful Loan Disbursements sent to borrower
            with transaction.atomic():
                payment = Payment.objects.select_for_update().filter(reference=reference).first()

                if not payment or payment.status == Payment.PaymentStatus.SUCCESS:
                    return {"status": "skipped", "reason": "Disbursement payment not found or already processed"}

                payment.status = Payment.PaymentStatus.SUCCESS
                payment.paystack_response = event_data
                payment.save()

                user = payment.user
                amount = payment.amount

                # Log Debit Transaction
                Transaction.objects.create(
                    user=user,
                    wallet=getattr(user, "wallet", None),
                    reference=reference,
                    amount=amount,
                    transaction_type=Transaction.TransactionType.DEBIT,
                    status=Transaction.TransactionStatus.SUCCESS,
                    description=f"Loan Disbursement for Loan #{payment.loan_id if payment.loan else 'N/A'}"
                )

                # Update Loan status to DISBURSED if linked
                if payment.loan:
                    loan = payment.loan
                    loan.application_status = Loan.ApplicationStatus.DISBURSED
                    loan.save()

            send_transaction_email.delay(
                user_email=user.email,
                subject="Loan Disbursed - SmartLoan",
                message=f"Hello {user.first_name},\n\nYour loan disbursement of GH¢ {amount:,.2f} has been successfully sent to your account/wallet.\n\nReference: {reference}"
            )
            return {"status": "disbursement_success", "reference": reference}

    except Exception as exc:
        # Retry task if transient DB or network failure occurs
        raise self.retry(exc=exc)


@shared_task
def send_transaction_email(user_email, subject, message):
    """
    Background task to dispatch transactional emails securely.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        return {"status": "email_sent", "recipient": user_email}
    except Exception as e:
        return {"status": "email_failed", "error": str(e)}