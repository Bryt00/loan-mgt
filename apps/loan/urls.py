# apps/loan/urls.py
from django.urls import path
from . import views

app_name = 'loan'

urlpatterns = [
    path('apply/', views.apply_for_loan, name='apply_loan'),
    path('status/<uuid:loan_id>/', views.loan_application_status, name='application_status'),
    path('update/<uuid:loan_id>/', views.update_loan_application, name='update_application'),
    path('delete/<uuid:loan_id>/', views.delete_loan_application, name='delete_application'),
]