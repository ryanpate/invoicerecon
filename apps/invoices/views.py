from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.http import JsonResponse
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Invoice, InvoiceLineItem
from .serializers import InvoiceSerializer, InvoiceListSerializer
from .services.parser import process_invoice


class InvoiceListView(LoginRequiredMixin, ListView):
    """List all invoices for the user's firm."""
    model = Invoice
    template_name = 'invoices/list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        if not self.request.user.firm:
            return Invoice.objects.none()
        return Invoice.objects.filter(
            firm=self.request.user.firm
        ).select_related('uploaded_by')


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """View invoice details and extracted data."""
    model = Invoice
    template_name = 'invoices/detail.html'
    context_object_name = 'invoice'

    def get_queryset(self):
        if not self.request.user.firm:
            return Invoice.objects.none()
        return Invoice.objects.filter(
            firm=self.request.user.firm
        ).prefetch_related('line_items')


class InvoiceUploadView(LoginRequiredMixin, View):
    """Handle invoice file uploads."""
    template_name = 'invoices/upload.html'

    def get(self, request):
        if not request.user.firm:
            messages.error(request, 'You must be part of a firm to upload invoices.')
            return redirect('dashboard:home')

        if not request.user.firm.can_process_invoice:
            messages.warning(
                request,
                'You have reached your monthly invoice limit. Please upgrade your plan.'
            )

        return render(request, self.template_name)

    def post(self, request):
        if not request.user.firm:
            return JsonResponse({'error': 'No firm associated'}, status=400)

        if not request.user.firm.can_process_invoice:
            return JsonResponse({'error': 'Invoice limit reached'}, status=403)

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'error': 'No file provided'}, status=400)

        # Validate file type
        if not uploaded_file.name.lower().endswith('.pdf'):
            return JsonResponse({'error': 'Only PDF files are accepted'}, status=400)

        # Create invoice record
        invoice = Invoice.objects.create(
            firm=request.user.firm,
            uploaded_by=request.user,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            status='pending'
        )

        # Process invoice synchronously (Celery worker not running)
        try:
            success = process_invoice(str(invoice.id))
            invoice.refresh_from_db()
        except Exception as e:
            invoice.status = 'error'
            invoice.processing_error = str(e)
            invoice.save()

        if request.headers.get('HX-Request'):
            return render(request, 'invoices/partials/upload_success.html', {
                'invoice': invoice
            })

        return JsonResponse({
            'id': str(invoice.id),
            'status': invoice.status,
            'message': 'Invoice processed' if invoice.status != 'error' else invoice.processing_error
        })


class InvoiceReprocessView(LoginRequiredMixin, View):
    """Reprocess an invoice."""

    def post(self, request, pk):
        invoice = get_object_or_404(
            Invoice,
            pk=pk,
            firm=request.user.firm
        )

        # Queue for reprocessing
        invoice.status = 'pending'
        invoice.save(update_fields=['status'])
        process_invoice_task.delay(str(invoice.id))

        messages.success(request, 'Invoice queued for reprocessing.')
        return redirect('invoices:detail', pk=pk)


# API Views
class InvoiceListAPIView(generics.ListAPIView):
    """List invoices via API."""
    serializer_class = InvoiceListSerializer

    def get_queryset(self):
        if not self.request.user.firm:
            return Invoice.objects.none()
        return Invoice.objects.filter(firm=self.request.user.firm)


class InvoiceDetailAPIView(generics.RetrieveUpdateAPIView):
    """Get or update invoice via API."""
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        if not self.request.user.firm:
            return Invoice.objects.none()
        return Invoice.objects.filter(
            firm=self.request.user.firm
        ).prefetch_related('line_items')


class InvoiceUploadAPIView(APIView):
    """Upload invoice via API."""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not request.user.firm:
            return Response(
                {'error': 'No firm associated'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.user.firm.can_process_invoice:
            return Response(
                {'error': 'Invoice limit reached'},
                status=status.HTTP_403_FORBIDDEN
            )

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not uploaded_file.name.lower().endswith('.pdf'):
            return Response(
                {'error': 'Only PDF files are accepted'},
                status=status.HTTP_400_BAD_REQUEST
            )

        invoice = Invoice.objects.create(
            firm=request.user.firm,
            uploaded_by=request.user,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            status='pending'
        )

        process_invoice_task.delay(str(invoice.id))

        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
