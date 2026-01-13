from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.BillingOverviewView.as_view(), name='overview'),
    path('subscribe/<str:tier>/', views.SubscribeView.as_view(), name='subscribe'),
    path('portal/', views.CustomerPortalView.as_view(), name='portal'),
    path('webhook/', views.StripeWebhookView.as_view(), name='webhook'),
]
