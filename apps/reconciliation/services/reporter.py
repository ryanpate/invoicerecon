"""
Reconciliation report generation.
"""
import io
from decimal import Decimal
from django.template.loader import render_to_string
from django.utils import timezone


class ReconciliationReporter:
    """Generate reports from reconciliation results."""

    def __init__(self, reconciliation):
        self.reconciliation = reconciliation

    def generate_summary(self) -> dict:
        """Generate a summary of reconciliation results."""
        discrepancies = self.reconciliation.discrepancies.all()

        # Group discrepancies by type
        by_type = {}
        for disc in discrepancies:
            disc_type = disc.get_discrepancy_type_display()
            if disc_type not in by_type:
                by_type[disc_type] = {'count': 0, 'amount': Decimal('0')}
            by_type[disc_type]['count'] += 1
            if disc.difference:
                by_type[disc_type]['amount'] += abs(disc.difference)

        # Group by severity
        by_severity = {
            'high': discrepancies.filter(severity='high').count(),
            'medium': discrepancies.filter(severity='medium').count(),
            'low': discrepancies.filter(severity='low').count(),
        }

        # Resolution status
        resolution_status = {
            'pending': discrepancies.filter(status='pending').count(),
            'resolved': discrepancies.filter(status='resolved').count(),
            'ignored': discrepancies.filter(status='ignored').count(),
        }

        return {
            'reconciliation_id': str(self.reconciliation.id),
            'name': self.reconciliation.name,
            'date_range': {
                'start': self.reconciliation.start_date,
                'end': self.reconciliation.end_date,
            },
            'summary': {
                'invoices_processed': self.reconciliation.invoices_count,
                'line_items_processed': self.reconciliation.line_items_count,
                'matched_items': self.reconciliation.matched_count,
                'match_rate': self.reconciliation.match_rate,
                'total_discrepancies': self.reconciliation.discrepancy_count,
                'total_invoice_amount': float(self.reconciliation.total_invoice_amount),
                'total_discrepancy_amount': float(
                    self.reconciliation.total_discrepancy_amount
                ),
            },
            'discrepancies_by_type': by_type,
            'discrepancies_by_severity': by_severity,
            'resolution_status': resolution_status,
            'generated_at': timezone.now().isoformat(),
        }

    def generate_html_report(self) -> str:
        """Generate an HTML report."""
        summary = self.generate_summary()
        discrepancies = self.reconciliation.discrepancies.select_related(
            'invoice_line_item__invoice',
            'time_entry'
        ).order_by('-severity', '-difference')

        context = {
            'reconciliation': self.reconciliation,
            'summary': summary,
            'discrepancies': discrepancies,
            'generated_at': timezone.now(),
        }

        return render_to_string('reconciliation/report.html', context)

    def generate_csv_report(self) -> str:
        """Generate a CSV report of discrepancies."""
        import csv

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'Type',
            'Severity',
            'Description',
            'Invoice #',
            'Client',
            'Expected Value',
            'Actual Value',
            'Difference',
            'Status',
            'Resolution Note'
        ])

        # Data rows
        for disc in self.reconciliation.discrepancies.select_related(
            'invoice_line_item__invoice'
        ).order_by('-severity'):
            invoice_num = ''
            client = ''
            if disc.invoice_line_item and disc.invoice_line_item.invoice:
                invoice_num = disc.invoice_line_item.invoice.invoice_number
                client = disc.invoice_line_item.invoice.client_name

            writer.writerow([
                disc.get_discrepancy_type_display(),
                disc.severity.upper(),
                disc.description,
                invoice_num,
                client,
                f"${disc.expected_value:.2f}" if disc.expected_value else '',
                f"${disc.actual_value:.2f}" if disc.actual_value else '',
                f"${disc.difference:.2f}" if disc.difference else '',
                disc.get_status_display(),
                disc.resolution_note
            ])

        return output.getvalue()
