from django.db import models
from django.conf import settings
import uuid


class Invoice(models.Model):
    """Uploaded invoice document."""
    STATUS_CHOICES = [
        ('pending', 'Pending Processing'),
        ('processing', 'Processing'),
        ('extracted', 'Data Extracted'),
        ('review', 'Needs Review'),
        ('confirmed', 'Confirmed'),
        ('error', 'Processing Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(
        'accounts.Firm',
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_invoices'
    )

    # File
    file = models.FileField(upload_to='invoices/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField(default=0)
    page_count = models.IntegerField(default=1)

    # Extracted data
    client_name = models.CharField(max_length=255, blank=True)
    matter_number = models.CharField(max_length=100, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    billing_attorney = models.CharField(max_length=255, blank=True)

    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    retainer_applied = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Processing metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    extraction_confidence = models.FloatField(default=0.0)
    raw_extraction = models.JSONField(default=dict, blank=True)
    extraction_notes = models.TextField(blank=True)
    processing_error = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number or 'Unnamed'} - {self.client_name or 'Unknown Client'}"


class InvoiceLineItem(models.Model):
    """Individual line item from an invoice."""
    TYPE_CHOICES = [
        ('time', 'Time Entry'),
        ('expense', 'Expense'),
        ('flat_fee', 'Flat Fee'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='line_items'
    )

    # Line item data
    date = models.DateField(null=True, blank=True)
    description = models.TextField()
    timekeeper = models.CharField(max_length=255, blank=True)
    hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    item_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='time')

    # Matching status
    matched = models.BooleanField(default=False)
    matched_time_entry_id = models.CharField(max_length=100, blank=True)

    # Order in invoice
    line_number = models.IntegerField(default=0)

    class Meta:
        ordering = ['invoice', 'line_number']

    def __str__(self):
        return f"{self.description[:50]}... - ${self.amount}"


class InvoiceProcessingLog(models.Model):
    """Log of invoice processing attempts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='processing_logs'
    )
    action = models.CharField(max_length=100)
    status = models.CharField(max_length=50)
    details = models.JSONField(default=dict)
    api_tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.action} - {self.status}"
