from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Firm, FirmInvitation


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'firm', 'is_firm_admin', 'is_staff', 'created_at']
    list_filter = ['is_firm_admin', 'is_staff', 'is_superuser', 'firm']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Firm', {'fields': ('firm', 'is_firm_admin')}),
    )


@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'subscription_tier', 'subscription_status', 'created_at']
    list_filter = ['subscription_tier', 'subscription_status']
    search_fields = ['name', 'owner__email']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['-created_at']


@admin.register(FirmInvitation)
class FirmInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'firm', 'invited_by', 'accepted', 'created_at']
    list_filter = ['accepted', 'firm']
    search_fields = ['email', 'firm__name']
    ordering = ['-created_at']
