"""
URL configuration for InvoiceRecon project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for Railway."""
    return JsonResponse({'status': 'healthy'})


urlpatterns = [
    # Health check
    path('health/', health_check, name='health_check'),

    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('accounts/', include('allauth.urls')),

    # App URLs
    path('', include('apps.dashboard.urls')),
    path('invoices/', include('apps.invoices.urls')),
    path('integrations/', include('apps.integrations.urls')),
    path('reconciliation/', include('apps.reconciliation.urls')),
    path('billing/', include('apps.billing.urls')),

    # API
    path('api/', include('apps.accounts.api_urls')),
    path('api/invoices/', include('apps.invoices.api_urls')),
    path('api/reconciliation/', include('apps.reconciliation.api_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
