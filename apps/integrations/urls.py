from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    path('', views.IntegrationListView.as_view(), name='list'),
    path('clio/connect/', views.ClioConnectView.as_view(), name='clio_connect'),
    path('clio/callback/', views.ClioCallbackView.as_view(), name='clio_callback'),
    path('clio/sync/', views.ClioSyncView.as_view(), name='clio_sync'),
    path('mycase/connect/', views.MyCaseConnectView.as_view(), name='mycase_connect'),
    path('mycase/callback/', views.MyCaseCallbackView.as_view(), name='mycase_callback'),
    path('mycase/sync/', views.MyCaseSyncView.as_view(), name='mycase_sync'),
    path('<uuid:pk>/disconnect/', views.DisconnectView.as_view(), name='disconnect'),
]
