"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("",include("apps.account.urls")),
    path("loan/",include("apps.loan.urls")),
    path("borrower_app/",include("apps.borrower_app.urls")),
    path("borrower_app/", include("apps.borrower_app.urls")),
    path("loan_officer_app/",include("apps.loan_officer_app.urls")),
    path("video_session/", include("apps.video_session.urls")),
    path("transactions/", include("apps.transactions.urls")),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
