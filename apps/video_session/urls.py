from django.urls import path
from . import views

app_name = "video_session"

urlpatterns = [
    path("list/", views.video_session_list, name="video_session_list"),
    path("create/", views.video_session_create, name="video_session_create"),
    path("<uuid:pk>/update/", views.video_session_update, name="video_session_update"),
    path("<uuid:pk>/delete/", views.video_session_delete, name="video_session_delete"),
]