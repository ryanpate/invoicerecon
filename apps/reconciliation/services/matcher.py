"""
Invoice to time entry matching engine.
"""
import logging
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


class ReconciliationMatcher:
    """
    Matches invoice line items against time entries from integrations.
    Uses fuzzy matching for descriptions and strict matching for dates/amounts.
    """

    def __init__(self, reconciliation):
        self.reconciliation = reconciliation
        self.firm = reconciliation.firm

    def run(self) -> bool:
        """
        Run the reconciliation matching process.

        Returns:
            True if successful, False otherwise
        """
        from apps.reconciliation.models import (
            Reconciliation, ReconciliationInvoice, Discrepancy
        )
        from apps.invoices.models import Invoice, InvoiceLineItem
        from apps.integrations.models import TimeEntry

        try:
            self.reconciliation.status = 'processing'
            self.reconciliation.save(update_fields=['status'])

            # Get invoices for this reconciliation
            invoice_ids = ReconciliationInvoice.objects.filter(
                reconciliation=self.reconciliation
            ).values_list('invoice_id', flat=True)

            invoices = Invoice.objects.filter(
                id__in=invoice_ids,
                status__in=['extracted', 'confirmed']
            ).prefetch_related('line_items')

            # Get time entries for date range
            time_entries = TimeEntry.objects.filter(
                firm=self.firm,
                date__gte=self.reconciliation.start_date,
                date__lte=self.reconciliation.end_date
            ).select_related('matter')

            # Build lookup dictionaries
            entry_lookup = self._build_time_entry_lookup(time_entries)

            # Track counts
            total_line_items = 0
            matched_count = 0
            discrepancy_count = 0
            total_invoice_amount = Decimal('0')
            total_discrepancy_amount = Decimal('0')

            # Process each invoice
            for invoice in invoices:
                total_invoice_amount += invoice.total_amount

                for line_item in invoice.line_items.all():
                    total_line_items += 1

                    # Try to find matching time entry
                    match = self._find_matching_entry(line_item, entry_lookup)

                    if match:
                        line_item.matched = True
                        line_item.matched_time_entry_id = str(match.external_id)
                        line_item.save(update_fields=['matched', 'matched_time_entry_id'])
                        matched_count += 1

                        # Check for value discrepancies
                        discrepancies = self._check_value_discrepancies(line_item, match)
                        for disc in discrepancies:
                            disc.reconciliation = self.reconciliation
                            disc.save()
                            discrepancy_count += 1
                            if disc.difference:
                                total_discrepancy_amount += abs(disc.difference)
                    else:
                        # No match found - create missing time entry discrepancy
                        Discrepancy.objects.create(
                            reconciliation=self.reconciliation,
                            invoice_line_item=line_item,
                            discrepancy_type='missing_time',
                            severity='high',
                            description=f"No matching time entry found for: {line_item.description[:100]}",
                            expected_value=line_item.amount,
                            actual_value=Decimal('0'),
                            difference=line_item.amount
                        )
                        discrepancy_count += 1
                        total_discrepancy_amount += line_item.amount

            # Check for unbilled time entries
            unbilled = self._find_unbilled_entries(time_entries, invoices)
            for entry in unbilled:
                Discrepancy.objects.create(
                    reconciliation=self.reconciliation,
                    time_entry=entry,
                    discrepancy_type='extra_time',
                    severity='medium',
                    description=f"Unbilled time entry: {entry.description[:100]}",
                    expected_value=Decimal('0'),
                    actual_value=entry.total,
                    difference=-entry.total
                )
                discrepancy_count += 1

            # Update reconciliation with results
            self.reconciliation.invoices_count = invoices.count()
            self.reconciliation.line_items_count = total_line_items
            self.reconciliation.matched_count = matched_count
            self.reconciliation.discrepancy_count = discrepancy_count
            self.reconciliation.total_invoice_amount = total_invoice_amount
            self.reconciliation.total_discrepancy_amount = total_discrepancy_amount
            self.reconciliation.status = 'completed'
            self.reconciliation.completed_at = timezone.now()
            self.reconciliation.save()

            return True

        except Exception as e:
            logger.error(f"Reconciliation matching error: {e}")
            self.reconciliation.status = 'error'
            self.reconciliation.error_message = str(e)
            self.reconciliation.save()
            return False

    def _build_time_entry_lookup(self, time_entries) -> dict:
        """Build a lookup dictionary for time entries by date and timekeeper."""
        lookup = {}
        for entry in time_entries:
            key = (entry.date, entry.timekeeper_name.lower())
            if key not in lookup:
                lookup[key] = []
            lookup[key].append(entry)
        return lookup

    def _find_matching_entry(self, line_item, entry_lookup) -> Optional['TimeEntry']:
        """
        Find a matching time entry for an invoice line item.
        Uses date, timekeeper, and fuzzy description matching.
        """
        if not line_item.date or not line_item.timekeeper:
            return None

        key = (line_item.date, line_item.timekeeper.lower())
        candidates = entry_lookup.get(key, [])

        if not candidates:
            # Try fuzzy timekeeper matching
            for lookup_key, entries in entry_lookup.items():
                if lookup_key[0] == line_item.date:
                    if self._similar(line_item.timekeeper, lookup_key[1], 0.8):
                        candidates.extend(entries)

        if not candidates:
            return None

        # Find best match by description similarity
        best_match = None
        best_score = 0.0

        for entry in candidates:
            score = self._similar(line_item.description, entry.description, 0)
            # Also consider hours match
            if line_item.hours and entry.hours:
                hours_match = 1.0 if float(line_item.hours) == float(entry.hours) else 0.5
                score = (score + hours_match) / 2

            if score > best_score and score > 0.5:
                best_score = score
                best_match = entry

        return best_match

    def _similar(self, a: str, b: str, threshold: float) -> float:
        """Calculate string similarity ratio."""
        a = a.lower().strip() if a else ''
        b = b.lower().strip() if b else ''
        ratio = SequenceMatcher(None, a, b).ratio()
        return ratio if ratio >= threshold else 0.0

    def _check_value_discrepancies(self, line_item, time_entry) -> list:
        """Check for value discrepancies between matched items."""
        from apps.reconciliation.models import Discrepancy

        discrepancies = []

        # Rate mismatch
        if line_item.rate and time_entry.rate:
            if abs(float(line_item.rate) - float(time_entry.rate)) > 0.01:
                disc = Discrepancy(
                    invoice_line_item=line_item,
                    time_entry=time_entry,
                    discrepancy_type='rate_mismatch',
                    severity='medium',
                    description=f"Rate mismatch: Invoice ${line_item.rate}/hr vs System ${time_entry.rate}/hr",
                    expected_value=time_entry.rate,
                    actual_value=line_item.rate,
                    difference=line_item.rate - time_entry.rate
                )
                discrepancies.append(disc)

        # Hours mismatch
        if line_item.hours and time_entry.hours:
            if abs(float(line_item.hours) - float(time_entry.hours)) > 0.1:
                disc = Discrepancy(
                    invoice_line_item=line_item,
                    time_entry=time_entry,
                    discrepancy_type='hours_mismatch',
                    severity='medium',
                    description=f"Hours mismatch: Invoice {line_item.hours}h vs System {time_entry.hours}h",
                    expected_value=time_entry.hours,
                    actual_value=line_item.hours,
                    difference=line_item.hours - time_entry.hours
                )
                discrepancies.append(disc)

        # Amount mismatch
        if line_item.amount and time_entry.total:
            if abs(float(line_item.amount) - float(time_entry.total)) > 1.0:
                disc = Discrepancy(
                    invoice_line_item=line_item,
                    time_entry=time_entry,
                    discrepancy_type='amount_mismatch',
                    severity='high',
                    description=f"Amount mismatch: Invoice ${line_item.amount} vs System ${time_entry.total}",
                    expected_value=time_entry.total,
                    actual_value=line_item.amount,
                    difference=line_item.amount - time_entry.total
                )
                discrepancies.append(disc)

        return discrepancies

    def _find_unbilled_entries(self, time_entries, invoices) -> list:
        """Find time entries that weren't matched to any invoice."""
        from apps.invoices.models import InvoiceLineItem

        # Get all matched external IDs
        matched_ids = set()
        for invoice in invoices:
            for item in invoice.line_items.all():
                if item.matched_time_entry_id:
                    matched_ids.add(item.matched_time_entry_id)

        # Find unbilled entries
        unbilled = []
        for entry in time_entries:
            if str(entry.external_id) not in matched_ids and entry.billable:
                unbilled.append(entry)

        return unbilled
