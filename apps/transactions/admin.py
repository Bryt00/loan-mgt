from django.contrib import admin
from .models import Wallet, Transaction, Payment


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "currency", "is_active", "created_at")
    search_fields = ("user__email", "currency")
    list_filter = ("is_active", "currency")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "amount", "transaction_type", "status", "created_at")
    search_fields = ("reference", "user__email", "description")
    list_filter = ("transaction_type", "status", "created_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "amount", "payment_type", "channel", "status", "created_at")
    search_fields = ("reference", "user__email", "email")
    list_filter = ("payment_type", "status", "channel", "created_at")