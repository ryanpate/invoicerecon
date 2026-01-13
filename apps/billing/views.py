import logging
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
import stripe

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

TIER_PRICES = {
    'starter': settings.STRIPE_PRICE_STARTER,
    'professional': settings.STRIPE_PRICE_PROFESSIONAL,
    'enterprise': settings.STRIPE_PRICE_ENTERPRISE,
}

TIER_LIMITS = {
    'starter': 50,
    'professional': 200,
    'enterprise': 999999,
}


class BillingOverviewView(LoginRequiredMixin, View):
    """View billing information and subscription status."""
    template_name = 'billing/overview.html'

    def get(self, request):
        if not request.user.firm:
            messages.error(request, 'You must be part of a firm.')
            return redirect('dashboard:home')

        firm = request.user.firm
        subscription = None

        if firm.stripe_subscription_id:
            try:
                subscription = stripe.Subscription.retrieve(firm.stripe_subscription_id)
            except stripe.error.StripeError as e:
                logger.error(f"Error retrieving subscription: {e}")

        context = {
            'firm': firm,
            'subscription': subscription,
            'tiers': [
                {
                    'id': 'starter',
                    'name': 'Starter',
                    'price': 299,
                    'invoices': 50,
                    'integrations': 1,
                    'current': firm.subscription_tier == 'starter'
                },
                {
                    'id': 'professional',
                    'name': 'Professional',
                    'price': 499,
                    'invoices': 200,
                    'integrations': 'Unlimited',
                    'current': firm.subscription_tier == 'professional',
                    'popular': True
                },
                {
                    'id': 'enterprise',
                    'name': 'Enterprise',
                    'price': 999,
                    'invoices': 'Unlimited',
                    'integrations': 'Unlimited',
                    'current': firm.subscription_tier == 'enterprise'
                },
            ]
        }

        return render(request, self.template_name, context)


class SubscribeView(LoginRequiredMixin, View):
    """Create a Stripe checkout session for subscription."""

    def post(self, request, tier):
        if not request.user.firm:
            return JsonResponse({'error': 'No firm'}, status=400)

        if tier not in TIER_PRICES:
            return JsonResponse({'error': 'Invalid tier'}, status=400)

        firm = request.user.firm
        price_id = TIER_PRICES[tier]

        if not price_id:
            messages.error(request, 'Stripe pricing not configured.')
            return redirect('billing:overview')

        try:
            # Create or get Stripe customer
            if not firm.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    name=firm.name,
                    metadata={'firm_id': str(firm.id)}
                )
                firm.stripe_customer_id = customer.id
                firm.save(update_fields=['stripe_customer_id'])

            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=firm.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{settings.SITE_URL}/billing/?success=true",
                cancel_url=f"{settings.SITE_URL}/billing/?canceled=true",
                metadata={
                    'firm_id': str(firm.id),
                    'tier': tier,
                }
            )

            return redirect(checkout_session.url)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            messages.error(request, f"Payment error: {str(e)}")
            return redirect('billing:overview')


class CustomerPortalView(LoginRequiredMixin, View):
    """Redirect to Stripe customer portal for subscription management."""

    def get(self, request):
        if not request.user.firm or not request.user.firm.stripe_customer_id:
            messages.error(request, 'No billing account found.')
            return redirect('billing:overview')

        try:
            session = stripe.billing_portal.Session.create(
                customer=request.user.firm.stripe_customer_id,
                return_url=f"{settings.SITE_URL}/billing/"
            )
            return redirect(session.url)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe portal error: {e}")
            messages.error(request, 'Unable to access billing portal.')
            return redirect('billing:overview')


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """Handle Stripe webhook events."""

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)

        # Log the event
        from apps.billing.models import SubscriptionEvent
        from apps.accounts.models import Firm

        event_record = SubscriptionEvent.objects.create(
            stripe_event_id=event.id,
            event_type=event.type,
            data=event.data
        )

        # Handle specific events
        if event.type == 'checkout.session.completed':
            session = event.data.object
            firm_id = session.metadata.get('firm_id')
            tier = session.metadata.get('tier')

            if firm_id:
                try:
                    firm = Firm.objects.get(id=firm_id)
                    firm.stripe_subscription_id = session.subscription
                    firm.subscription_tier = tier
                    firm.subscription_status = 'active'
                    firm.monthly_invoice_limit = TIER_LIMITS.get(tier, 50)
                    firm.save()
                    event_record.firm = firm
                    event_record.processed = True
                    event_record.save()
                except Firm.DoesNotExist:
                    logger.error(f"Firm {firm_id} not found for checkout")

        elif event.type == 'customer.subscription.updated':
            subscription = event.data.object
            customer_id = subscription.customer

            try:
                firm = Firm.objects.get(stripe_customer_id=customer_id)
                firm.subscription_status = subscription.status
                firm.save(update_fields=['subscription_status'])
                event_record.firm = firm
                event_record.processed = True
                event_record.save()
            except Firm.DoesNotExist:
                pass

        elif event.type == 'customer.subscription.deleted':
            subscription = event.data.object
            customer_id = subscription.customer

            try:
                firm = Firm.objects.get(stripe_customer_id=customer_id)
                firm.subscription_status = 'canceled'
                firm.subscription_tier = 'starter'
                firm.monthly_invoice_limit = 50
                firm.save()
                event_record.firm = firm
                event_record.processed = True
                event_record.save()
            except Firm.DoesNotExist:
                pass

        elif event.type == 'invoice.payment_failed':
            invoice = event.data.object
            customer_id = invoice.customer

            try:
                firm = Firm.objects.get(stripe_customer_id=customer_id)
                firm.subscription_status = 'past_due'
                firm.save(update_fields=['subscription_status'])
                event_record.firm = firm
                event_record.processed = True
                event_record.save()
            except Firm.DoesNotExist:
                pass

        return HttpResponse(status=200)
