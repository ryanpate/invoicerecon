from django.contrib import admin
from .models import SubscriptionEvent, UsageRecord


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'firm', 'processed', 'created_at']
    list_filter = ['event_type', 'processed']
    search_fields = ['stripe_event_id', 'firm__name']
    readonly_fields = ['data', 'created_at']


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ['firm', 'month', 'invoices_processed', 'api_calls']
    list_filter = ['month']
    search_fields = ['firm__name']
