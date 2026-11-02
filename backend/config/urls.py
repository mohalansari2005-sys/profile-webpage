from django.urls import include, path

urlpatterns = [
    path("api/chat/", include("chat.urls")),
    # /api/visit/ (the page-view beacon) and /dashboard/; see analytics/urls.py.
    path("", include("analytics.urls")),
]
