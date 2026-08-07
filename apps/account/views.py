from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import (
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.generic import FormView, TemplateView, UpdateView, DeleteView
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserUpdateForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm,
    CustomPasswordResetForm,
)
from .models import User, Profile
from .tasks import send_activation_email, send_password_reset_email


def invalidate_user_cache(user_id):
    cache.delete(f"user:{user_id}")
    cache.delete(f"profile:{user_id}")
    cache.delete(f"user_dashboard:{user_id}")
    cache.delete(f"user_permissions:{user_id}")


def get_user_base_template(user):
    """Helper to determine the correct layout/base template based on user role."""
    if user.is_authenticated:
        if user.role == User.Role.LOAN_OFFICER:
            return "loan_officer_app/loan_officer_base.html"  # Adjust if your base template path differs
        elif user.role == User.Role.BORROWER:
            return "borrower_app/borrower_base.html"
    return "borrower_app/borrower_base.html"


def home(request):
    return render(request, "account/index.html")


def work(request):
    return render(request, "account/work.html")


def features(request):
    return render(request, "account/features.html")


def about(request):
    return render(request, "account/about.html")


class RegisterView(FormView):
    template_name = "account/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("account:activation_sent")

    def form_valid(self, form):
        user = form.save(commit=False)
        user.email_verified = False
        user.save()

        invalidate_user_cache(user.id)
        send_activation_email.delay(str(user.id))

        messages.success(
            self.request,
            "Your account has been created successfully. Please check your email to activate your account.",
        )
        return super().form_valid(form)


class ActivationSentView(TemplateView):
    template_name = "account/activation_sent.html"


class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            user.email_verified = True
            user.save(update_fields=["email_verified"])

            invalidate_user_cache(user.id)
            messages.success(
                request,
                "Your email has been verified successfully. You can now log in.",
            )
            return redirect("account:login")

        messages.error(request, "The activation link is invalid or has expired.")
        return redirect("account:login")


class ResendActivationEmailView(FormView):
    template_name = "account/resend_activation.html"
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy("account:activation_sent")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email__iexact=email)
            if not user.email_verified:
                send_activation_email.delay(str(user.id))
        except User.DoesNotExist:
            pass

        messages.success(
            self.request,
            "If an account exists and is not yet verified, a new activation email has been sent.",
        )
        return super().form_valid(form)


class CustomLoginView(FormView):
    template_name = "account/login.html"
    form_class = UserLoginForm

    def form_valid(self, form):
        user = form.get_user()

        if not user.email_verified:
            messages.error(self.request, "Please verify your email before logging in.")
            return redirect("account:login")

        login(self.request, user)
        invalidate_user_cache(user.id)

        if form.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            self.request.session.set_expiry(0)

        messages.success(self.request, f"Welcome back, {user.first_name}!")

        if user.role == User.Role.LOAN_OFFICER:
            return redirect("loan_officer_app:loan_officer_dashboard")
        elif user.role == User.Role.BORROWER:
            return redirect("borrower_app:borrower_dashboard")
        elif user.role == User.Role.ADMIN:
            return redirect(reverse("admin:index"))

        return redirect("home")


class LogoutView(View):
    def post(self, request):
        if request.user.is_authenticated:
            invalidate_user_cache(request.user.id)
            logout(request)
            messages.success(request, "You have been logged out successfully.")
        return redirect("account:home")


class ForgotPasswordView(FormView):
    template_name = "account/password_reset.html"
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy("account:password_reset_done")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email__iexact=email)
            if user.email_verified:
                send_password_reset_email.delay(str(user.id))
        except User.DoesNotExist:
            pass

        messages.success(
            self.request,
            "If an account exists with that email address, a password reset link has been sent.",
        )
        return super().form_valid(form)


class PasswordResetSentView(TemplateView):
    template_name = "account/password_reset_sent.html"


class ResetPasswordConfirmView(PasswordResetConfirmView):
    template_name = "account/password_reset_confirm.html"
    success_url = reverse_lazy("account:password_reset_complete")

    def form_valid(self, form):
        user = form.user
        invalidate_user_cache(user.id)
        messages.success(self.request, "Your password has been reset successfully.")
        return super().form_valid(form)


class PasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "account/password_reset_complete.html"


class ChangePasswordView(LoginRequiredMixin, FormView):
    template_name = "account/change_password.html"
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy("account:profile")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_template"] = get_user_base_template(self.request.user)
        return context

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        invalidate_user_cache(user.id)
        messages.success(self.request, "Your password has been changed successfully.")
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "account/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        context["profile"] = self.request.user.profile
        context["base_template"] = get_user_base_template(self.request.user)
        return context


class UpdateAccountView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "account/account_edit.html"
    success_url = reverse_lazy("account:profile")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_template"] = get_user_base_template(self.request.user)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        invalidate_user_cache(self.request.user.id)
        messages.success(self.request, "Your account has been updated successfully.")
        return response


class UpdateProfileView(LoginRequiredMixin, View):
    template_name = "account/profile_edit.html"
    success_url = reverse_lazy("account:profile")

    def get(self, request, *args, **kwargs):
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

        return render(request, self.template_name, {
            "user_form": user_form,
            "profile_form": profile_form,
            "base_template": get_user_base_template(request.user),
        })

    def post(self, request, *args, **kwargs):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user.profile,
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            invalidate_user_cache(request.user.id)
            messages.success(request, "Your settings have been updated successfully.")
            return redirect(self.success_url)

        messages.error(request, "Please correct the errors below.")
        return render(request, self.template_name, {
            "user_form": user_form,
            "profile_form": profile_form,
            "base_template": get_user_base_template(request.user),
        })


class DeleteAccountView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = "account/account_delete.html"
    success_url = reverse_lazy("account:login")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_template"] = get_user_base_template(self.request.user)
        return context

    def delete(self, request, *args, **kwargs):
        user_id = request.user.id
        response = super().delete(request, *args, **kwargs)
        invalidate_user_cache(user_id)
        messages.success(request, "Your account has been deleted successfully.")
        return response