from django.urls import path
from .views import (
    DocumentUploadView,
    DocumentListView,
    DocumentDetailView,
    DocumentStatusView,
    DocumentReprocessView,
    DocumentChunksView,
    GlobalChunkListView,
)

urlpatterns = [
    path("upload/", DocumentUploadView.as_view(), name="document-upload"),
    path("", DocumentListView.as_view(), name="document-list"),
    path("chunks/", GlobalChunkListView.as_view(), name="global-chunks"),
    path("<uuid:doc_id>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<uuid:doc_id>/status/", DocumentStatusView.as_view(), name="document-status"),
    path("<uuid:doc_id>/reprocess/", DocumentReprocessView.as_view(), name="document-reprocess"),
    path("<uuid:doc_id>/chunks/", DocumentChunksView.as_view(), name="document-chunks"),
]
