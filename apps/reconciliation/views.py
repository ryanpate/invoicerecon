from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Reconciliation, ReconciliationInvoice, Discrepancy
from .serializers import ReconciliationSerializer, ReconciliationListSerializer
from .services.matcher import ReconciliationMatcher
from .services.reporter import ReconciliationReporter


class ReconciliationListView(LoginRequiredMixin, ListView):
    """List all reconciliations for the firm."""
    model = Reconciliation
    template_name = 'reconciliation/list.html'
    context_object_name = 'reconciliations'
    paginate_by = 20

    def get_queryset(self):
        if not self.request.user.firm:
            return Reconciliation.objects.none()
        return Reconciliation.objects.filter(firm=self.request.user.firm)


class ReconciliationCreateView(LoginRequiredMixin, View):
    """Create a new reconciliation."""
    template_name = 'reconciliation/create.html'

    def get(self, request):
        if not request.user.firm:
            messages.error(request, 'You must be part of a firm.')
            return redirect('dashboard:home')

        # Get available invoices
        from apps.invoices.models import Invoice
        invoices = Invoice.objects.filter(
            firm=request.user.firm,
            status__in=['extracted', 'confirmed']
        ).order_by('-created_at')

        return render(request, self.template_name, {'invoices': invoices})

    def post(self, request):
        if not request.user.firm:
            return JsonResponse({'error': 'No firm'}, status=400)

        name = request.POST.get('name', f"Reconciliation {timezone.now().strftime('%Y-%m-%d')}")
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        invoice_ids = request.POST.getlist('invoices')

        if not invoice_ids:
            messages.error(request, 'Please select at least one invoice.')
            return redirect('reconciliation:create')

        # Create reconciliation
        reconciliation = Reconciliation.objects.create(
            firm=request.user.firm,
            created_by=request.user,
            name=name,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
        )

        # Add invoices
        for invoice_id in invoice_ids:
            ReconciliationInvoice.objects.create(
                reconciliation=reconciliation,
                invoice_id=invoice_id
            )

        # Run matching
        matcher = ReconciliationMatcher(reconciliation)
        success = matcher.run()

        if success:
            messages.success(
                request,
                f'Reconciliation completed. Found {reconciliation.discrepancy_count} discrepancies.'
            )
        else:
            messages.warning(request, 'Reconciliation completed with errors.')

        return redirect('reconciliation:detail', pk=reconciliation.pk)


class ReconciliationDetailView(LoginRequiredMixin, DetailView):
    """View reconciliation details and discrepancies."""
    model = Reconciliation
    template_name = 'reconciliation/detail.html'
    context_object_name = 'reconciliation'

    def get_queryset(self):
        if not self.request.user.firm:
            return Reconciliation.objects.none()
        return Reconciliation.objects.filter(
            firm=self.request.user.firm
        ).prefetch_related('discrepancies')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['discrepancies'] = self.object.discrepancies.select_related(
            'invoice_line_item__invoice',
            'time_entry'
        ).order_by('-severity', '-difference')
        return context


class ReconciliationReportView(LoginRequiredMixin, View):
    """Generate HTML report."""

    def get(self, request, pk):
        reconciliation = get_object_or_404(
            Reconciliation,
            pk=pk,
            firm=request.user.firm
        )

        reporter = ReconciliationReporter(reconciliation)
        html = reporter.generate_html_report()

        return HttpResponse(html)


class ReconciliationExportView(LoginRequiredMixin, View):
    """Export reconciliation as CSV."""

    def get(self, request, pk):
        reconciliation = get_object_or_404(
            Reconciliation,
            pk=pk,
            firm=request.user.firm
        )

        reporter = ReconciliationReporter(reconciliation)
        csv_content = reporter.generate_csv_report()

        response = HttpResponse(csv_content, content_type='text/csv')
        filename = f"reconciliation_{reconciliation.name}_{timezone.now().strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response


class DiscrepancyResolveView(LoginRequiredMixin, View):
    """Resolve a discrepancy."""

    def post(self, request, pk):
        discrepancy = get_object_or_404(
            Discrepancy,
            pk=pk,
            reconciliation__firm=request.user.firm
        )

        status = request.POST.get('status', 'resolved')
        note = request.POST.get('note', '')

        discrepancy.status = status
        discrepancy.resolution_note = note
        discrepancy.resolved_by = request.user
        discrepancy.resolved_at = timezone.now()
        discrepancy.save()

        if request.headers.get('HX-Request'):
            return render(request, 'reconciliation/partials/discrepancy_row.html', {
                'discrepancy': discrepancy
            })

        messages.success(request, 'Discrepancy resolved.')
        return redirect('reconciliation:detail', pk=discrepancy.reconciliation.pk)


# API Views
class ReconciliationListAPIView(generics.ListAPIView):
    """List reconciliations via API."""
    serializer_class = ReconciliationListSerializer

    def get_queryset(self):
        if not self.request.user.firm:
            return Reconciliation.objects.none()
        return Reconciliation.objects.filter(firm=self.request.user.firm)


class ReconciliationDetailAPIView(generics.RetrieveAPIView):
    """Get reconciliation details via API."""
    serializer_class = ReconciliationSerializer

    def get_queryset(self):
        if not self.request.user.firm:
            return Reconciliation.objects.none()
        return Reconciliation.objects.filter(
            firm=self.request.user.firm
        ).prefetch_related('discrepancies')


class ReconciliationSummaryAPIView(APIView):
    """Get reconciliation summary via API."""

    def get(self, request, pk):
        reconciliation = get_object_or_404(
            Reconciliation,
            pk=pk,
            firm=request.user.firm
        )

        reporter = ReconciliationReporter(reconciliation)
        summary = reporter.generate_summary()

        return Response(summary)
