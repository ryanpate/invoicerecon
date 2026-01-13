from django.urls import path
from . import views

urlpatterns = [
    path('auth/me/', views.CurrentUserView.as_view(), name='api_current_user'),
    path('firm/', views.FirmDetailView.as_view(), name='api_firm_detail'),
]
