from django.urls import path

from analytics.views import DashboardView, VisitView

urlpatterns = [
    path("api/visit/", VisitView.as_view(), name="visit"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
