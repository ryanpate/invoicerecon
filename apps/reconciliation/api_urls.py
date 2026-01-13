from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReconciliationListAPIView.as_view(), name='api_reconciliation_list'),
    path('<uuid:pk>/', views.ReconciliationDetailAPIView.as_view(), name='api_reconciliation_detail'),
    path('<uuid:pk>/summary/', views.ReconciliationSummaryAPIView.as_view(), name='api_reconciliation_summary'),
]
