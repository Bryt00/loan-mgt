from django.urls import path
from . import views

app_name = 'loan_officer_app'

urlpatterns = [
    path("loan_officer_dashboard/", views.loan_officer_dashboard, name="loan_officer_dashboard"),
    path("loan_list_related_officer", views.loan_application_related_loan_officer, name="loan_list_related_officer"),
    path("pending_loan_applications/", views.pending_loan_applications, name="pending_loan_applications"),
    path("approved_disbursed_loans/<uuid:loan_id>/review/", views.review_approved_disbursed_loan, name="review_approved_disbursed_loan"),
    path("pending_loans/<uuid:loan_id>/review/", views.review_pending_loan, name="review_pending_loan"),
    path("borrowers/", views.loan_officer_borrowers, name="loan_officer_borrowers"),
    path("officer/loans/<uuid:loan_id>/documents/", views.loan_officer_borrower_documents_view, name="loan_officer_borrower_documents"),
    path('officer/documents/', views.loan_officer_documents_list, name='loan_officer_documents_list'),
    path('reports/', views.generate_reports_view, name='loan_reports'),
    path('calculator/', views.loan_officer_calculator_view, name='loan_officer_calculator'),
    path('loans/<uuid:loan_id>/notes/', views.loan_officer_notes_view, name='loan_officer_notes'),
]