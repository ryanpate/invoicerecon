from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta


class HomeView(TemplateView):
    """Marketing homepage."""
    template_name = 'marketing/home.html'

    def get(self, request, *args, **kwargs):
        # Redirect logged-in users to dashboard
        if request.user.is_authenticated:
            return redirect('dashboard:dashboard')
        return super().get(request, *args, **kwargs)


class PricingView(TemplateView):
    """Pricing page."""
    template_name = 'marketing/pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tiers'] = [
            {
                'name': 'Starter',
                'price': 299,
                'features': [
                    'Up to 50 invoices/month',
                    '1 practice management integration',
                    'Email support',
                    'Basic reporting',
                    'PDF export',
                ],
                'cta': 'Start Free Trial',
                'href': '/accounts/signup/?plan=starter',
            },
            {
                'name': 'Professional',
                'price': 499,
                'popular': True,
                'features': [
                    'Up to 200 invoices/month',
                    'Unlimited integrations',
                    'Priority support',
                    'Advanced analytics',
                    'Custom report templates',
                    'API access',
                ],
                'cta': 'Start Free Trial',
                'href': '/accounts/signup/?plan=professional',
            },
            {
                'name': 'Enterprise',
                'price': 999,
                'features': [
                    'Unlimited invoices',
                    'Dedicated account manager',
                    'Custom integrations',
                    'White-label options',
                    'SLA guarantee',
                    'On-premise option',
                ],
                'cta': 'Contact Sales',
                'href': 'mailto:admin@invoicerecon.app',
            },
        ]
        return context


class FeaturesView(TemplateView):
    """Features page."""
    template_name = 'marketing/features.html'


class DashboardView(LoginRequiredMixin, View):
    """Main application dashboard."""
    template_name = 'dashboard/home.html'

    def get(self, request):
        if not request.user.firm:
            return redirect('dashboard:onboarding')

        firm = request.user.firm

        # Get recent activity
        from apps.invoices.models import Invoice
        from apps.reconciliation.models import Reconciliation, Discrepancy

        recent_invoices = Invoice.objects.filter(
            firm=firm
        ).order_by('-created_at')[:5]

        recent_reconciliations = Reconciliation.objects.filter(
            firm=firm
        ).order_by('-created_at')[:5]

        # Stats for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)

        invoices_this_month = Invoice.objects.filter(
            firm=firm,
            created_at__gte=thirty_days_ago
        ).count()

        discrepancies_found = Discrepancy.objects.filter(
            reconciliation__firm=firm,
            created_at__gte=thirty_days_ago
        ).count()

        discrepancies_resolved = Discrepancy.objects.filter(
            reconciliation__firm=firm,
            status='resolved',
            resolved_at__gte=thirty_days_ago
        ).count()

        total_savings = Discrepancy.objects.filter(
            reconciliation__firm=firm,
            status='resolved',
            created_at__gte=thirty_days_ago
        ).aggregate(total=Sum('difference'))['total'] or 0

        context = {
            'firm': firm,
            'recent_invoices': recent_invoices,
            'recent_reconciliations': recent_reconciliations,
            'stats': {
                'invoices_this_month': invoices_this_month,
                'invoices_limit': firm.monthly_invoice_limit,
                'invoices_remaining': firm.monthly_invoice_limit - firm.invoices_processed_this_month,
                'discrepancies_found': discrepancies_found,
                'discrepancies_resolved': discrepancies_resolved,
                'total_savings': abs(float(total_savings)),
            }
        }

        return render(request, self.template_name, context)


class OnboardingView(LoginRequiredMixin, View):
    """New user onboarding flow."""
    template_name = 'dashboard/onboarding.html'

    def get(self, request):
        if request.user.firm:
            return redirect('dashboard:dashboard')
        return render(request, self.template_name)

    def post(self, request):
        from apps.accounts.models import Firm
        from datetime import timedelta

        firm_name = request.POST.get('firm_name')
        if not firm_name:
            return render(request, self.template_name, {
                'error': 'Please enter your firm name.'
            })

        # Create firm
        firm = Firm.objects.create(
            name=firm_name,
            owner=request.user,
            subscription_tier='starter',
            subscription_status='trialing',
            trial_ends_at=timezone.now() + timedelta(days=14),
            monthly_invoice_limit=50,
        )

        # Associate user with firm
        request.user.firm = firm
        request.user.is_firm_admin = True
        request.user.save(update_fields=['firm', 'is_firm_admin'])

        return redirect('dashboard:dashboard')
