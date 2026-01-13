from django.db import models
import uuid


class Integration(models.Model):
    """Third-party integration connection."""
    PROVIDER_CHOICES = [
        ('clio', 'Clio'),
        ('mycase', 'MyCase'),
        ('quickbooks', 'QuickBooks'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Token Expired'),
        ('revoked', 'Revoked'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        'accounts.Firm',
        on_delete=models.CASCADE,
        related_name='integrations'
    )
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # OAuth tokens (encrypted in production)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # Provider-specific data
    provider_user_id = models.CharField(max_length=255, blank=True)
    provider_account_id = models.CharField(max_length=255, blank=True)
    provider_data = models.JSONField(default=dict, blank=True)

    # Sync tracking
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['firm', 'provider']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.firm.name} - {self.get_provider_display()}"

    @property
    def is_active(self):
        return self.status == 'active'


class Matter(models.Model):
    """Legal matter/case from practice management software."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='matters'
    )
    firm = models.ForeignKey(
        'accounts.Firm',
        on_delete=models.CASCADE,
        related_name='matters'
    )

    # External IDs
    external_id = models.CharField(max_length=255)
    display_number = models.CharField(max_length=100, blank=True)

    # Matter details
    description = models.CharField(max_length=500, blank=True)
    client_name = models.CharField(max_length=255)
    client_external_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=50, default='open')
    practice_area = models.CharField(max_length=100, blank=True)

    # Billing info
    billing_method = models.CharField(max_length=50, blank=True)

    # Timestamps
    opened_at = models.DateField(null=True, blank=True)
    closed_at = models.DateField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['integration', 'external_id']
        ordering = ['client_name', 'display_number']

    def __str__(self):
        return f"{self.display_number} - {self.client_name}"


class TimeEntry(models.Model):
    """Time entry from practice management software."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        related_name='time_entries'
    )
    firm = models.ForeignKey(
        'accounts.Firm',
        on_delete=models.CASCADE,
        related_name='time_entries'
    )
    matter = models.ForeignKey(
        Matter,
        on_delete=models.SET_NULL,
        null=True,
        related_name='time_entries'
    )

    # External IDs
    external_id = models.CharField(max_length=255)

    # Entry details
    date = models.DateField()
    description = models.TextField()
    timekeeper_name = models.CharField(max_length=255)
    timekeeper_external_id = models.CharField(max_length=255, blank=True)

    # Time and billing
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status
    billed = models.BooleanField(default=False)
    billable = models.BooleanField(default=True)

    # Sync tracking
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['integration', 'external_id']
        ordering = ['-date', 'timekeeper_name']

    def __str__(self):
        return f"{self.date} - {self.timekeeper_name} - {self.hours}h"
