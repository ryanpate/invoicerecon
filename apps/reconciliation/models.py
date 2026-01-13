from django.db import models
from django.conf import settings
import uuid


class Reconciliation(models.Model):
    """A reconciliation session comparing invoices against time entries."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        'accounts.Firm',
        on_delete=models.CASCADE,
        related_name='reconciliations'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reconciliations'
    )

    # Scope
    name = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)

    # Results summary
    invoices_count = models.IntegerField(default=0)
    line_items_count = models.IntegerField(default=0)
    matched_count = models.IntegerField(default=0)
    discrepancy_count = models.IntegerField(default=0)
    total_invoice_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )
    total_discrepancy_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Reconciliations'

    def __str__(self):
        return f"{self.name or 'Reconciliation'} - {self.created_at.strftime('%Y-%m-%d')}"

    @property
    def match_rate(self):
        if self.line_items_count == 0:
            return 0
        return round((self.matched_count / self.line_items_count) * 100, 1)


class ReconciliationInvoice(models.Model):
    """Invoice included in a reconciliation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reconciliation = models.ForeignKey(
        Reconciliation,
        on_delete=models.CASCADE,
        related_name='reconciliation_invoices'
    )
    invoice = models.ForeignKey(
        'invoices.Invoice',
        on_delete=models.CASCADE,
        related_name='reconciliations'
    )

    class Meta:
        unique_together = ['reconciliation', 'invoice']


class Discrepancy(models.Model):
    """A detected discrepancy between invoice and time entries."""
    TYPE_CHOICES = [
        ('missing_time', 'Missing Time Entry'),
        ('extra_time', 'Unbilled Time Entry'),
        ('rate_mismatch', 'Rate Mismatch'),
        ('hours_mismatch', 'Hours Mismatch'),
        ('amount_mismatch', 'Amount Mismatch'),
        ('missing_expense', 'Missing Expense'),
        ('duplicate', 'Possible Duplicate'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('ignored', 'Ignored'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reconciliation = models.ForeignKey(
        Reconciliation,
        on_delete=models.CASCADE,
        related_name='discrepancies'
    )

    # Related items
    invoice_line_item = models.ForeignKey(
        'invoices.InvoiceLineItem',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='discrepancies'
    )
    time_entry = models.ForeignKey(
        'integrations.TimeEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discrepancies'
    )

    # Discrepancy details
    discrepancy_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default='medium'
    )
    description = models.TextField()

    # Values
    expected_value = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    actual_value = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    difference = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    # Resolution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_discrepancies'
    )
    resolution_note = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-severity', '-created_at']
        verbose_name_plural = 'Discrepancies'

    def __str__(self):
        return f"{self.get_discrepancy_type_display()} - {self.difference}"
