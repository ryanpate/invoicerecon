from django.urls import path
from . import views

urlpatterns = [
    path('', views.InvoiceListAPIView.as_view(), name='api_invoice_list'),
    path('upload/', views.InvoiceUploadAPIView.as_view(), name='api_invoice_upload'),
    path('<uuid:pk>/', views.InvoiceDetailAPIView.as_view(), name='api_invoice_detail'),
]
