from django.contrib import admin
from .models import Invoice, InvoiceLineItem, InvoiceProcessingLog


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    readonly_fields = ['matched', 'matched_time_entry_id']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'client_name', 'firm', 'total_amount',
        'status', 'extraction_confidence', 'created_at'
    ]
    list_filter = ['status', 'firm', 'created_at']
    search_fields = ['invoice_number', 'client_name', 'matter_number']
    readonly_fields = ['raw_extraction', 'processed_at', 'created_at', 'updated_at']
    inlines = [InvoiceLineItemInline]
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('firm', 'uploaded_by', 'file', 'original_filename', 'status')
        }),
        ('Extracted Data', {
            'fields': (
                'client_name', 'matter_number', 'invoice_number',
                'invoice_date', 'due_date', 'billing_attorney'
            )
        }),
        ('Amounts', {
            'fields': (
                'subtotal', 'taxes', 'total_amount',
                'retainer_applied', 'amount_due'
            )
        }),
        ('Processing', {
            'fields': (
                'extraction_confidence', 'extraction_notes',
                'processing_error', 'raw_extraction', 'processed_at'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'description', 'timekeeper', 'hours', 'amount', 'matched']
    list_filter = ['item_type', 'matched']
    search_fields = ['description', 'timekeeper']


@admin.register(InvoiceProcessingLog)
class InvoiceProcessingLogAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'action', 'status', 'api_tokens_used', 'created_at']
    list_filter = ['status', 'action']
    readonly_fields = ['details', 'created_at']
