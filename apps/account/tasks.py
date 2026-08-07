import smtplib

from celery import shared_task
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User


@shared_task(
    bind=True,
    autoretry_for=(smtplib.SMTPException,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_activation_email(self, user_id):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    activation_url = (
        f"{settings.FRONTEND_URL}"
        f"{reverse('account:activate', kwargs={'uidb64': uid, 'token': token})}"
    )

    context = {
        "user": user,
        "activation_url": activation_url,
    }

    html_content = render_to_string(
        "account/emails/activation_email.html",
        context,
    )

    email = EmailMessage(
        subject="Activate your SmartLoan account",
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.content_subtype = "html"
    email.send()


@shared_task(
    bind=True,
    autoretry_for=(smtplib.SMTPException,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def send_password_reset_email(self, user_id):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    reset_url = (
        f"{settings.FRONTEND_URL}"
        f"{reverse('account:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})}"
    )

    context = {
        "user": user,
        "reset_url": reset_url,
    }

    html_content = render_to_string(
        "account/emails/password_reset_email.html",
        context,
    )

    email = EmailMessage(
        subject="Reset your SmartLoan password",
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.content_subtype = "html"
    email.send()