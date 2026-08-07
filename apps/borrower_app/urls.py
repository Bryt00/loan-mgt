from django.urls import path

from . import views

app_name = "borrower_app"

urlpatterns = [
    path(
        "dashboard/",
        views.borrower_dashboard,
        name="borrower_dashboard",
    ),
    path(
        "loan/<uuid:loan_id>/",
        views.borrower_loan_detail,
        name="borrower_loan_detail",
    ),
    path(
        "loans/",
        views.borrower_loans_list,
        name="borrower_loans_list",
    ),
    path(
        "documents/",
        views.borrower_documents_list,
        name="borrower_documents_list",
    ),
    path(
        "document/<uuid:document_id>/",
        views.borrower_document_detail,
        name="borrower_document_detail",
    ),
    path(
        "borrower/<uuid:borrower_id>/video-sessions/",
        views.borrower_video_sessions_list,
        name="borrower_video_sessions_list",
    ),
    path(
        "video-sessions/",
        views.borrower_video_sessions_list,
        name="video_session_list",
    ),
    # path(
    #     "video-sessions/<uuid:pk>/",
    #     views.video_session_detail,
    #     name="video_session_detail",
    # ),


]