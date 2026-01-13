from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Marketing pages
    path('', views.HomeView.as_view(), name='home'),
    path('pricing/', views.PricingView.as_view(), name='pricing'),
    path('features/', views.FeaturesView.as_view(), name='features'),

    # App dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('onboarding/', views.OnboardingView.as_view(), name='onboarding'),
]
