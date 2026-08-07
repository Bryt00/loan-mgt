from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)

from .models import User, Profile


TAILWIND_INPUT = (
    "w-full rounded-xl border border-gray-300 bg-white px-4 py-3 "
    "text-sm text-gray-900 placeholder-gray-400 shadow-sm "
    "focus:border-green-500 focus:ring-2 focus:ring-green-500/20 "
    "transition duration-200"
)


class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": TAILWIND_INPUT,
            "placeholder": "Enter password",
        }),
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": TAILWIND_INPUT,
            "placeholder": "Confirm password",
        }),
    )

    class Meta:
        model = User
        fields = (
            "full_name",
            "email",
            "phone_number",
        )

        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
                "placeholder": "Full name",
            }),
            "email": forms.EmailInput(attrs={
                "class": TAILWIND_INPUT,
                "placeholder": "Email address",
            }),
            "phone_number": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
                "placeholder": "Phone number",
            }),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                "Passwords do not match."
            )

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = user.email.lower()
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


class UserLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": TAILWIND_INPUT,
            "placeholder": "Email address",
        }),
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": TAILWIND_INPUT,
            "placeholder": "Password",
        }),
    )

    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "h-4 w-4 rounded border-gray-300 text-green-600 focus:ring-green-500",
        }),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            self.user = authenticate(
                request=self.request,
                email=email,
                password=password,
            )

            if self.user is None:
                raise forms.ValidationError(
                    "Invalid email or password."
                )

            if not self.user.is_active:
                raise forms.ValidationError(
                    "This account is inactive."
                )

        return cleaned_data

    def get_user(self):
        return self.user


class UserUpdateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = (
            "full_name",
            "email",
            "phone_number",
        )

        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
            }),
            "email": forms.EmailInput(attrs={
                "class": TAILWIND_INPUT,
            }),
            "phone_number": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get("instance")
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if (
            User.objects.exclude(pk=self.user.pk)
            .filter(email=email)
            .exists()
        ):
            raise forms.ValidationError(
                "This email is already in use."
            )

        return email

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"]

        if (
            User.objects.exclude(pk=self.user.pk)
            .filter(phone_number=phone)
            .exists()
        ):
            raise forms.ValidationError(
                "This phone number is already in use."
            )

        return phone


class ProfileUpdateForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = (
            "profile_photo",
            "date_of_birth",
            "gender",
            "address",
            "city",
            "region",
            "occupation",
            "emergency_contact_name",
            "emergency_contact_phone",
            "bio",
        )

        widgets = {
            "date_of_birth": forms.DateInput(attrs={
                "class": TAILWIND_INPUT,
                "type": "date",
            }),
            "gender": forms.Select(attrs={
                "class": TAILWIND_INPUT,
            }),
            "address": forms.Textarea(attrs={
                "class": TAILWIND_INPUT,
                "rows": 3,
            }),
            "city": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
            }),
            "region": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
            }),
            "occupation": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
            }),
            "emergency_contact_name": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
            }),
            "emergency_contact_phone": forms.TextInput(attrs={
                "class": TAILWIND_INPUT,
            }),
            "bio": forms.Textarea(attrs={
                "class": TAILWIND_INPUT,
                "rows": 4,
            }),
        }


class CustomPasswordChangeForm(PasswordChangeForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": TAILWIND_INPUT,
            })


class CustomPasswordResetForm(PasswordResetForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["email"].widget.attrs.update({
            "class": TAILWIND_INPUT,
            "placeholder": "Email address",
        })


class CustomSetPasswordForm(SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": TAILWIND_INPUT,
            })