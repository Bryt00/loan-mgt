from django import forms
from decimal import Decimal


class LoanRepaymentForm(forms.Form):
    """
    Form for borrowers to input the repayment amount towards their active loan.
    """
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm text-slate-900 bg-slate-50 focus:bg-white focus:outline-none focus:border-emerald-700 transition',
            'placeholder': 'Enter amount to pay (e.g. 500.00)',
        })
    )


class LoanDisbursementForm(forms.Form):
    """
    Form for loan officers to confirm disbursement of an approved loan.
    Collects the borrower's bank/mobile money details. The view auto-creates
    a Paystack Transfer Recipient and initiates the transfer — no manual
    recipient code required.
    """

    TRANSFER_TYPE_CHOICES = [
        ('mobile_money', 'Mobile Money (MoMo)'),
        ('ghipss', 'Bank Account'),
    ]

    # Fallback Ghana MoMo providers — view tries to fetch live list from Paystack
    MOMO_PROVIDER_CHOICES = [
        ('MTN', 'MTN Mobile Money'),
        ('VOD', 'Vodafone Cash'),
        ('ATL', 'AirtelTigo Money'),
    ]

    transfer_type = forms.ChoiceField(
        choices=TRANSFER_TYPE_CHOICES,
        label='Transfer Method',
        initial='mobile_money',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm text-slate-900 bg-slate-50 focus:bg-white focus:outline-none focus:border-emerald-700 transition',
            'id': 'id_transfer_type',
        }),
    )

    account_name = forms.CharField(
        max_length=200,
        label='Account Holder Name',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm text-slate-900 bg-slate-50 focus:bg-white focus:outline-none focus:border-emerald-700 transition',
            'placeholder': 'e.g. Kwame Mensah',
        }),
        help_text='Full name as it appears on the bank or MoMo account.',
    )

    account_number = forms.CharField(
        max_length=30,
        label='Account / Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm text-slate-900 bg-slate-50 focus:bg-white focus:outline-none focus:border-emerald-700 transition',
            'placeholder': 'e.g. 0241234567',
        }),
        help_text='Mobile number for MoMo transfers; bank account number for bank transfers.',
    )

    bank_code = forms.ChoiceField(
        choices=MOMO_PROVIDER_CHOICES,
        label='Provider / Bank',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm text-slate-900 bg-slate-50 focus:bg-white focus:outline-none focus:border-emerald-700 transition',
            'id': 'id_bank_code',
        }),
        help_text='Select the mobile money network or bank.',
    )

    def __init__(self, *args, bank_choices=None, **kwargs):
        """Allow the view to inject a live bank list fetched from Paystack."""
        super().__init__(*args, **kwargs)
        if bank_choices:
            self.fields['bank_code'].choices = bank_choices