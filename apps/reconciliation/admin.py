from django.contrib import admin
from .models import Reconciliation, ReconciliationInvoice, Discrepancy


class DiscrepancyInline(admin.TabularInline):
    model = Discrepancy
    extra = 0
    readonly_fields = ['discrepancy_type', 'severity', 'description', 'difference', 'status']


@admin.register(Reconciliation)
class ReconciliationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'firm', 'status', 'invoices_count', 'discrepancy_count',
        'match_rate', 'created_at'
    ]
    list_filter = ['status', 'firm', 'created_at']
    search_fields = ['name', 'firm__name']
    readonly_fields = ['completed_at', 'created_at', 'updated_at']
    inlines = [DiscrepancyInline]

    def match_rate(self, obj):
        return f"{obj.match_rate}%"


@admin.register(Discrepancy)
class DiscrepancyAdmin(admin.ModelAdmin):
    list_display = [
        'discrepancy_type', 'severity', 'status', 'difference',
        'reconciliation', 'created_at'
    ]
    list_filter = ['discrepancy_type', 'severity', 'status']
    search_fields = ['description']
    readonly_fields = ['resolved_at', 'created_at', 'updated_at']
