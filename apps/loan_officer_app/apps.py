from django.apps import AppConfig


class LoanOfficerAppConfig(AppConfig):
    name = 'apps.loan_officer_app'

    def ready(self):
        import apps.loan_officer_app.signals