from django.db import models
import uuid


class SubscriptionEvent(models.Model):
    """Log of subscription-related events from Stripe webhooks."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        'accounts.Firm',
        on_delete=models.CASCADE,
        related_name='subscription_events',
        null=True
    )
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    data = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"


class UsageRecord(models.Model):
    """Track monthly usage for billing purposes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        'accounts.Firm',
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    month = models.DateField()  # First day of the month
    invoices_processed = models.IntegerField(default=0)
    api_calls = models.IntegerField(default=0)
    storage_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['firm', 'month']
        ordering = ['-month']

    def __str__(self):
        return f"{self.firm.name} - {self.month.strftime('%Y-%m')}"
