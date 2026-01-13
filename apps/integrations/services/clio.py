"""
Clio API integration service.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode
from django.conf import settings
from django.utils import timezone
import httpx

logger = logging.getLogger(__name__)

CLIO_API_BASE = 'https://app.clio.com/api/v4'
CLIO_AUTH_URL = 'https://app.clio.com/oauth/authorize'
CLIO_TOKEN_URL = 'https://app.clio.com/oauth/token'


class ClioService:
    """Service for interacting with Clio API."""

    def __init__(self, integration=None):
        self.integration = integration
        self.client = httpx.Client(timeout=30.0)

    def get_authorization_url(self, state: str) -> str:
        """Get OAuth authorization URL for Clio."""
        params = {
            'response_type': 'code',
            'client_id': settings.CLIO_CLIENT_ID,
            'redirect_uri': settings.CLIO_REDIRECT_URI,
            'state': state,
        }
        return f"{CLIO_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': settings.CLIO_CLIENT_ID,
            'client_secret': settings.CLIO_CLIENT_SECRET,
            'redirect_uri': settings.CLIO_REDIRECT_URI,
        }

        response = self.client.post(CLIO_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self.integration or not self.integration.refresh_token:
            return False

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.integration.refresh_token,
            'client_id': settings.CLIO_CLIENT_ID,
            'client_secret': settings.CLIO_CLIENT_SECRET,
        }

        try:
            response = self.client.post(CLIO_TOKEN_URL, data=data)
            response.raise_for_status()
            token_data = response.json()

            self.integration.access_token = token_data['access_token']
            if 'refresh_token' in token_data:
                self.integration.refresh_token = token_data['refresh_token']
            self.integration.token_expires_at = timezone.now() + timedelta(
                seconds=token_data.get('expires_in', 3600)
            )
            self.integration.status = 'active'
            self.integration.save()

            return True
        except Exception as e:
            logger.error(f"Failed to refresh Clio token: {e}")
            self.integration.status = 'expired'
            self.integration.save()
            return False

    def _get_headers(self) -> dict:
        """Get API request headers."""
        return {
            'Authorization': f'Bearer {self.integration.access_token}',
            'Content-Type': 'application/json',
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        """Make an API request with automatic token refresh."""
        if not self.integration:
            raise ValueError("No integration configured")

        # Check if token is expired
        if self.integration.token_expires_at:
            if timezone.now() >= self.integration.token_expires_at:
                if not self.refresh_access_token():
                    raise Exception("Failed to refresh access token")

        url = f"{CLIO_API_BASE}{endpoint}"
        headers = self._get_headers()

        try:
            response = self.client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Try refreshing token
                if self.refresh_access_token():
                    headers = self._get_headers()
                    response = self.client.request(method, url, headers=headers, **kwargs)
                    response.raise_for_status()
                    return response.json()
            raise

    def get_current_user(self) -> dict:
        """Get the current authenticated user."""
        return self._make_request('GET', '/users/who_am_i.json')

    def get_matters(self, page: int = 1, limit: int = 100) -> dict:
        """Get matters/cases."""
        params = {'page': page, 'limit': limit, 'status': 'Open'}
        return self._make_request('GET', '/matters.json', params=params)

    def get_time_entries(
        self,
        matter_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 100
    ) -> dict:
        """Get time entries."""
        params = {'page': page, 'limit': limit}

        if matter_id:
            params['matter_id'] = matter_id
        if start_date:
            params['created_since'] = start_date.isoformat()
        if end_date:
            params['created_before'] = end_date.isoformat()

        return self._make_request('GET', '/activities.json', params=params)

    def sync_matters(self) -> int:
        """Sync all matters from Clio."""
        from apps.integrations.models import Matter

        count = 0
        page = 1

        while True:
            response = self.get_matters(page=page)
            matters_data = response.get('data', [])

            if not matters_data:
                break

            for matter_data in matters_data:
                Matter.objects.update_or_create(
                    integration=self.integration,
                    external_id=str(matter_data['id']),
                    defaults={
                        'firm': self.integration.firm,
                        'display_number': matter_data.get('display_number', ''),
                        'description': matter_data.get('description', ''),
                        'client_name': matter_data.get('client', {}).get('name', ''),
                        'client_external_id': str(
                            matter_data.get('client', {}).get('id', '')
                        ),
                        'status': matter_data.get('status', 'open'),
                        'practice_area': matter_data.get('practice_area', {}).get(
                            'name', ''
                        ),
                        'billing_method': matter_data.get('billing_method', ''),
                    }
                )
                count += 1

            page += 1

        return count

    def sync_time_entries(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """Sync time entries from Clio."""
        from apps.integrations.models import TimeEntry, Matter

        count = 0
        page = 1

        # Default to last 30 days
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)

        while True:
            response = self.get_time_entries(
                start_date=start_date,
                end_date=end_date,
                page=page
            )
            entries_data = response.get('data', [])

            if not entries_data:
                break

            for entry_data in entries_data:
                matter = None
                if entry_data.get('matter'):
                    matter = Matter.objects.filter(
                        integration=self.integration,
                        external_id=str(entry_data['matter']['id'])
                    ).first()

                TimeEntry.objects.update_or_create(
                    integration=self.integration,
                    external_id=str(entry_data['id']),
                    defaults={
                        'firm': self.integration.firm,
                        'matter': matter,
                        'date': entry_data.get('date'),
                        'description': entry_data.get('note', ''),
                        'timekeeper_name': entry_data.get('user', {}).get('name', ''),
                        'timekeeper_external_id': str(
                            entry_data.get('user', {}).get('id', '')
                        ),
                        'hours': entry_data.get('quantity', 0),
                        'rate': entry_data.get('rate', 0),
                        'total': entry_data.get('total', 0),
                        'billed': entry_data.get('billed', False),
                        'billable': entry_data.get('billable', True),
                    }
                )
                count += 1

            page += 1

        self.integration.last_sync_at = timezone.now()
        self.integration.save(update_fields=['last_sync_at'])

        return count
