from django.contrib import admin
from .models import Integration, Matter, TimeEntry


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ['firm', 'provider', 'status', 'last_sync_at', 'created_at']
    list_filter = ['provider', 'status']
    search_fields = ['firm__name']
    readonly_fields = ['access_token', 'refresh_token', 'created_at', 'updated_at']


@admin.register(Matter)
class MatterAdmin(admin.ModelAdmin):
    list_display = ['display_number', 'client_name', 'firm', 'status', 'synced_at']
    list_filter = ['status', 'firm']
    search_fields = ['display_number', 'client_name', 'description']


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'timekeeper_name', 'hours', 'rate', 'total',
        'billed', 'firm', 'synced_at'
    ]
    list_filter = ['billed', 'billable', 'firm']
    search_fields = ['description', 'timekeeper_name']
    date_hierarchy = 'date'
