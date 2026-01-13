from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
import uuid


class User(AbstractUser):
    """Custom user model for InvoiceRecon."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    firm = models.ForeignKey(
        'Firm',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users'
    )
    is_firm_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class Firm(models.Model):
    """Law firm account."""
    TIER_CHOICES = [
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_firms'
    )

    # Subscription
    subscription_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default='starter'
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    subscription_status = models.CharField(max_length=50, default='trialing')

    # Limits based on tier
    monthly_invoice_limit = models.IntegerField(default=50)
    invoices_processed_this_month = models.IntegerField(default=0)

    # Timestamps
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Firm.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.subscription_status in ['active', 'trialing']

    @property
    def can_process_invoice(self):
        return self.invoices_processed_this_month < self.monthly_invoice_limit

    def get_tier_limits(self):
        limits = {
            'starter': {'invoices': 50, 'integrations': 1},
            'professional': {'invoices': 200, 'integrations': 999},
            'enterprise': {'invoices': 999999, 'integrations': 999},
        }
        return limits.get(self.subscription_tier, limits['starter'])


class FirmInvitation(models.Model):
    """Invitation to join a firm."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation to {self.email} for {self.firm.name}"
