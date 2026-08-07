from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from apps.common.models import BaseModel
from .manager import UserManager


class User(BaseModel, AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        BORROWER = "BORROWER", "Borrower"
        LOAN_OFFICER = "LOAN_OFFICER", "Loan Officer"
        ADMIN = "ADMIN", "Administrator"

    email = models.EmailField(
        unique=True,
        db_index=True,
    )

    full_name = models.CharField(max_length=150)

    phone_number = models.CharField(
        max_length=20,
        unique=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.BORROWER,
        db_index=True,
    )

    email_verified = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    last_seen = models.DateTimeField(blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "phone_number"]

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_verified"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ""

    @property
    def initials(self):
        names = self.full_name.split()
        return "".join(name[0] for name in names[:2]).upper()

    @property
    def is_officer(self):
        return self.role == self.Role.LOAN_OFFICER

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN


class Profile(BaseModel):

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    profile_photo = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True,
    )

    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
    )

    address = models.TextField(blank=True)

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    region = models.CharField(
        max_length=100,
        blank=True,
    )

    occupation = models.CharField(
        max_length=150,
        blank=True,
    )

    national_id_number = models.CharField(
        max_length=50,
        blank=True,
    )

    emergency_contact_name = models.CharField(
        max_length=150,
        blank=True,
    )

    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
    )

    bio = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.full_name}'s Profile"