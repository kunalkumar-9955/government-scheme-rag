from django.urls import path
from .views import DashboardView, RAGMetricsView, QueryLogListView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="analytics-dashboard"),
    path("rag-metrics/", RAGMetricsView.as_view(), name="rag-metrics"),
    path("query-logs/", QueryLogListView.as_view(), name="query-logs"),
]
