"""apps/evaluation/urls.py"""
from django.urls import path
from .views import (
    EvaluationDatasetListView,
    EvaluationDatasetDetailView,
    EvaluationCaseListView,
    EvaluationCaseDeleteView,
    EvaluationRunListView,
    EvaluationRunDetailView,
    EvaluationRunCompareView,
)

urlpatterns = [
    # Datasets
    path("datasets/",                           EvaluationDatasetListView.as_view(),   name="eval-dataset-list"),
    path("datasets/<uuid:id>/",                 EvaluationDatasetDetailView.as_view(), name="eval-dataset-detail"),
    path("datasets/<uuid:dataset_id>/cases/",   EvaluationCaseListView.as_view(),      name="eval-case-list"),
    path("datasets/<uuid:dataset_id>/cases/<uuid:case_id>/", EvaluationCaseDeleteView.as_view(), name="eval-case-delete"),

    # Runs
    path("runs/",                                         EvaluationRunListView.as_view(),   name="eval-run-list"),
    path("runs/<uuid:run_id>/",                           EvaluationRunDetailView.as_view(), name="eval-run-detail"),
    path("runs/<uuid:run_id>/compare/<uuid:other_id>/",   EvaluationRunCompareView.as_view(),name="eval-run-compare"),
]
