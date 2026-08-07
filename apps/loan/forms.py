from django import forms
from .models import Loan, SupportingDocuments, LoanNote

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class LoanApplicationForm(forms.ModelForm):
    passport_picture = forms.ImageField(
        required=True,
        label="Passport Picture",
        widget=forms.ClearableFileInput(attrs={
            'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 transition'
        })
    )
    document = forms.FileField(
        required=False,
        label="Supporting Documents (Ghana Card, Financial Statements, etc.)",
        widget=MultipleFileInput(attrs={
            'multiple': True,
            'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 transition'
        })
    )
    document_type = forms.ChoiceField(
        choices=SupportingDocuments.DocumentType.choices,
        required=False,
        label="Document Type",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition'
        })
    )

    class Meta:
        model = Loan
        fields = [
            'amount',
            'purpose',
            'tenure_months',
            'employment_status',
            'employer_name',
            'monthly_salary',
            'existing_loans',
            'passport_picture',
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={
                'placeholder': 'e.g., 5000.00',
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition'
            }),
            'purpose': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Briefly describe what this loan will be used for...',
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition'
            }),
            'tenure_months': forms.NumberInput(attrs={
                'placeholder': 'e.g., 12',
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition'
            }),
            'employment_status': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition'
            }),
            'employer_name': forms.TextInput(attrs={
                'placeholder': 'e.g., Enterprise Group / Self-Employed',
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition'
            }),
            'monthly_salary': forms.NumberInput(attrs={
                'placeholder': 'e.g., 3500.00',
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition'
            }),
            'existing_loans': forms.NumberInput(attrs={
                'placeholder': 'e.g., 0.00',
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition'
            }),
        }

    def save(self, commit=True, borrower=None):
        loan = super().save(commit=False)
        if borrower:
            loan.borrower = borrower

        if commit:
            loan.save()
            
            # Note: We won't save documents here anymore, we will process request.FILES.getlist('document') 
            # in the view to handle multiple files.
            
        return loan


class LoanNoteForm(forms.ModelForm):
    class Meta:
        model = LoanNote
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add an internal note regarding this loan application...',
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white transition resize-none'
            })
        }