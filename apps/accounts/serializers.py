from rest_framework import serializers
from .models import User, Firm


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_firm_admin', 'created_at']
        read_only_fields = ['id', 'created_at']


class FirmSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    tier_limits = serializers.SerializerMethodField()

    class Meta:
        model = Firm
        fields = [
            'id', 'name', 'slug', 'owner_email', 'subscription_tier',
            'subscription_status', 'monthly_invoice_limit',
            'invoices_processed_this_month', 'tier_limits', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']

    def get_tier_limits(self, obj):
        return obj.get_tier_limits()
