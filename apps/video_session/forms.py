from django import forms
from .models import VideoSession


class VideoSessionForm(forms.ModelForm):
    class Meta:
        model = VideoSession
        fields = [
            "loan",
            "borrower",
            "loan_officer",
            "schedule_date",
            "schedule_time",
            "duration_minutes",
            "comments",
        ]
        widgets = {
            "loan": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-700 text-sm text-slate-800 bg-white"
                }
            ),
            "borrower": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-700 text-sm text-slate-800 bg-white"
                }
            ),
            "loan_officer": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-100 text-sm text-slate-700 cursor-not-allowed",
                }
            ),
            "schedule_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-700 text-sm text-slate-800 bg-white",
                },
                format="%Y-%m-%d",
            ),
            "schedule_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-700 text-sm text-slate-800 bg-white",
                },
                format="%H:%M",
            ),
            "duration_minutes": forms.NumberInput(
                attrs={
                    "placeholder": "e.g. 30",
                    "class": "w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-700 text-sm text-slate-800 bg-white",
                }
            ),
            "comments": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Add any notes or agenda for this session...",
                    "class": "w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-700 text-sm text-slate-800 bg-white",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        # Extract the user passed from the view
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.user:
            # Restrict queryset to just this user (defense in depth)
            self.fields["loan_officer"].queryset = self.fields[
                "loan_officer"
            ].queryset.filter(pk=self.user.pk)

            # Pre-select the logged-in user for new sessions
            if not self.instance.pk:
                self.fields["loan_officer"].initial = self.user
            else:
                # On update, always force it back to the logged-in officer,
                # regardless of who's on the existing instance
                self.fields["loan_officer"].initial = self.user

            # Lock the field: Django will ignore any POSTed value for this
            # field and always use `initial` above, no matter what the
            # client sends. This is a real server-side restriction, not
            # just a UI restriction.
            self.fields["loan_officer"].disabled = True

        # Ensure date and time inputs correctly display existing values when updating
        if self.instance and self.instance.pk:
            if self.instance.schedule_date:
                self.initial["schedule_date"] = self.instance.schedule_date.strftime(
                    "%Y-%m-%d"
                )
            if self.instance.schedule_time:
                self.initial["schedule_time"] = self.instance.schedule_time.strftime(
                    "%H:%M"
                )