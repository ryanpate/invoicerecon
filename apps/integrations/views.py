import secrets
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.views.generic import ListView
from django.utils import timezone
from .models import Integration
from .services.clio import ClioService
from .services.mycase import MyCaseService


class IntegrationListView(LoginRequiredMixin, ListView):
    """List all integrations for the firm."""
    model = Integration
    template_name = 'integrations/list.html'
    context_object_name = 'integrations'

    def get_queryset(self):
        if not self.request.user.firm:
            return Integration.objects.none()
        return Integration.objects.filter(firm=self.request.user.firm)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check which integrations are available
        existing = set(self.get_queryset().values_list('provider', flat=True))
        context['available_providers'] = [
            {'id': 'clio', 'name': 'Clio', 'connected': 'clio' in existing},
            {'id': 'mycase', 'name': 'MyCase', 'connected': 'mycase' in existing},
        ]
        return context


class ClioConnectView(LoginRequiredMixin, View):
    """Initiate Clio OAuth flow."""

    def get(self, request):
        if not request.user.firm:
            messages.error(request, 'You must be part of a firm to connect integrations.')
            return redirect('dashboard:home')

        # Generate state token for CSRF protection
        state = secrets.token_urlsafe(32)
        request.session['clio_oauth_state'] = state

        service = ClioService()
        auth_url = service.get_authorization_url(state)

        return redirect(auth_url)


class ClioCallbackView(LoginRequiredMixin, View):
    """Handle Clio OAuth callback."""

    def get(self, request):
        # Verify state
        state = request.GET.get('state')
        expected_state = request.session.pop('clio_oauth_state', None)

        if not state or state != expected_state:
            messages.error(request, 'Invalid OAuth state. Please try again.')
            return redirect('integrations:list')

        code = request.GET.get('code')
        if not code:
            error = request.GET.get('error', 'Unknown error')
            messages.error(request, f'Authorization failed: {error}')
            return redirect('integrations:list')

        try:
            service = ClioService()
            token_data = service.exchange_code_for_token(code)

            # Create or update integration
            integration, created = Integration.objects.update_or_create(
                firm=request.user.firm,
                provider='clio',
                defaults={
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token', ''),
                    'token_expires_at': timezone.now() + timedelta(
                        seconds=token_data.get('expires_in', 3600)
                    ),
                    'status': 'active',
                }
            )

            # Get user info
            service.integration = integration
            user_data = service.get_current_user()
            integration.provider_user_id = str(user_data.get('data', {}).get('id', ''))
            integration.provider_data = user_data.get('data', {})
            integration.save()

            messages.success(request, 'Successfully connected to Clio!')

        except Exception as e:
            messages.error(request, f'Failed to connect to Clio: {str(e)}')

        return redirect('integrations:list')


class ClioSyncView(LoginRequiredMixin, View):
    """Trigger Clio data sync."""

    def post(self, request):
        integration = get_object_or_404(
            Integration,
            firm=request.user.firm,
            provider='clio',
            status='active'
        )

        try:
            service = ClioService(integration)

            # Sync matters first, then time entries
            matter_count = service.sync_matters()
            entry_count = service.sync_time_entries()

            messages.success(
                request,
                f'Synced {matter_count} matters and {entry_count} time entries from Clio.'
            )
        except Exception as e:
            messages.error(request, f'Sync failed: {str(e)}')

        return redirect('integrations:list')


class MyCaseConnectView(LoginRequiredMixin, View):
    """Initiate MyCase OAuth flow."""

    def get(self, request):
        if not request.user.firm:
            messages.error(request, 'You must be part of a firm to connect integrations.')
            return redirect('dashboard:home')

        state = secrets.token_urlsafe(32)
        request.session['mycase_oauth_state'] = state

        service = MyCaseService()
        auth_url = service.get_authorization_url(state)

        return redirect(auth_url)


class MyCaseCallbackView(LoginRequiredMixin, View):
    """Handle MyCase OAuth callback."""

    def get(self, request):
        state = request.GET.get('state')
        expected_state = request.session.pop('mycase_oauth_state', None)

        if not state or state != expected_state:
            messages.error(request, 'Invalid OAuth state. Please try again.')
            return redirect('integrations:list')

        code = request.GET.get('code')
        if not code:
            error = request.GET.get('error', 'Unknown error')
            messages.error(request, f'Authorization failed: {error}')
            return redirect('integrations:list')

        try:
            service = MyCaseService()
            token_data = service.exchange_code_for_token(code)

            integration, created = Integration.objects.update_or_create(
                firm=request.user.firm,
                provider='mycase',
                defaults={
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token', ''),
                    'token_expires_at': timezone.now() + timedelta(
                        seconds=token_data.get('expires_in', 3600)
                    ),
                    'status': 'active',
                }
            )

            messages.success(request, 'Successfully connected to MyCase!')

        except Exception as e:
            messages.error(request, f'Failed to connect to MyCase: {str(e)}')

        return redirect('integrations:list')


class MyCaseSyncView(LoginRequiredMixin, View):
    """Trigger MyCase data sync."""

    def post(self, request):
        integration = get_object_or_404(
            Integration,
            firm=request.user.firm,
            provider='mycase',
            status='active'
        )

        try:
            service = MyCaseService(integration)
            matter_count = service.sync_matters()
            entry_count = service.sync_time_entries()

            messages.success(
                request,
                f'Synced {matter_count} cases and {entry_count} time entries from MyCase.'
            )
        except Exception as e:
            messages.error(request, f'Sync failed: {str(e)}')

        return redirect('integrations:list')


class DisconnectView(LoginRequiredMixin, View):
    """Disconnect an integration."""

    def post(self, request, pk):
        integration = get_object_or_404(
            Integration,
            pk=pk,
            firm=request.user.firm
        )

        provider_name = integration.get_provider_display()
        integration.delete()

        messages.success(request, f'Disconnected from {provider_name}.')
        return redirect('integrations:list')
