from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='list'),
    path('upload/', views.InvoiceUploadView.as_view(), name='upload'),
    path('<uuid:pk>/', views.InvoiceDetailView.as_view(), name='detail'),
    path('<uuid:pk>/reprocess/', views.InvoiceReprocessView.as_view(), name='reprocess'),
]
