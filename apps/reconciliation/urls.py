from django.urls import path
from . import views

app_name = 'reconciliation'

urlpatterns = [
    path('', views.ReconciliationListView.as_view(), name='list'),
    path('new/', views.ReconciliationCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.ReconciliationDetailView.as_view(), name='detail'),
    path('<uuid:pk>/report/', views.ReconciliationReportView.as_view(), name='report'),
    path('<uuid:pk>/export/', views.ReconciliationExportView.as_view(), name='export'),
    path(
        'discrepancy/<uuid:pk>/resolve/',
        views.DiscrepancyResolveView.as_view(),
        name='resolve_discrepancy'
    ),
]
