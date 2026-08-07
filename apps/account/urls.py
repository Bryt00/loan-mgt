from django.urls import path
from . import views

app_name = "account"

urlpatterns = [

    path("", views.home, name="home"),
    path("/work", views.work, name="work"),
    path("features/", views.features, name="features"),
    path("about/", views.about, name="about"),
    # Registration & Activation
    path("register/", views.RegisterView.as_view(), name="register"),
    path("activation-sent/", views.ActivationSentView.as_view(), name="activation_sent"),
    path("activate/<uidb64>/<token>/", views.ActivateAccountView.as_view(), name="activate"),
    path("resend-activation/", views.ResendActivationEmailView.as_view(), name="resend_activation"),

    # Authentication
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),

    # Password Reset
    path("password-reset/", views.ForgotPasswordView.as_view(), name="password_reset"),
    path("password-reset/done/", views.PasswordResetSentView.as_view(), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", views.ResetPasswordConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset-complete/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),

    # Profile & Account Management
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/edit/", views.UpdateProfileView.as_view(), name="profile_edit"),
    path("account/edit/", views.UpdateAccountView.as_view(), name="account_edit"),
    path("account/delete/", views.DeleteAccountView.as_view(), name="account_delete"),
    path("password-change/", views.ChangePasswordView.as_view(), name="password_change"),
]