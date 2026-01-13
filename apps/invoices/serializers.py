from rest_framework import serializers
from .models import Invoice, InvoiceLineItem


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = [
            'id', 'date', 'description', 'timekeeper', 'hours',
            'rate', 'amount', 'item_type', 'matched', 'line_number'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    uploaded_by_email = serializers.EmailField(
        source='uploaded_by.email',
        read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            'id', 'original_filename', 'client_name', 'matter_number',
            'invoice_number', 'invoice_date', 'due_date', 'billing_attorney',
            'subtotal', 'taxes', 'total_amount', 'retainer_applied',
            'amount_due', 'status', 'extraction_confidence',
            'extraction_notes', 'line_items', 'uploaded_by_email',
            'created_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'processed_at', 'extraction_confidence'
        ]


class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    line_item_count = serializers.IntegerField(
        source='line_items.count',
        read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            'id', 'original_filename', 'client_name', 'invoice_number',
            'total_amount', 'status', 'extraction_confidence',
            'line_item_count', 'created_at'
        ]
