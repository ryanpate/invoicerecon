from rest_framework import serializers
from .models import Reconciliation, Discrepancy


class DiscrepancySerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_discrepancy_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Discrepancy
        fields = [
            'id', 'discrepancy_type', 'type_display', 'severity',
            'description', 'expected_value', 'actual_value', 'difference',
            'status', 'status_display', 'resolution_note', 'created_at'
        ]


class ReconciliationSerializer(serializers.ModelSerializer):
    discrepancies = DiscrepancySerializer(many=True, read_only=True)
    match_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Reconciliation
        fields = [
            'id', 'name', 'start_date', 'end_date', 'status',
            'invoices_count', 'line_items_count', 'matched_count',
            'discrepancy_count', 'match_rate', 'total_invoice_amount',
            'total_discrepancy_amount', 'discrepancies',
            'created_at', 'completed_at'
        ]


class ReconciliationListSerializer(serializers.ModelSerializer):
    match_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Reconciliation
        fields = [
            'id', 'name', 'status', 'invoices_count', 'discrepancy_count',
            'match_rate', 'total_discrepancy_amount', 'created_at'
        ]
