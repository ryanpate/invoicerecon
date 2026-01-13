"""
Celery tasks for invoice processing.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_invoice_task(self, invoice_id: str):
    """
    Process an uploaded invoice asynchronously.

    Args:
        invoice_id: UUID of the invoice to process
    """
    from .services.parser import process_invoice

    try:
        success = process_invoice(invoice_id)
        if not success:
            logger.warning(f"Invoice {invoice_id} processing returned False")
        return success
    except Exception as e:
        logger.error(f"Error in process_invoice_task: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def reset_monthly_invoice_counts():
    """
    Reset monthly invoice counts for all firms.
    Should be scheduled to run on the 1st of each month.
    """
    from apps.accounts.models import Firm

    Firm.objects.all().update(invoices_processed_this_month=0)
    logger.info("Monthly invoice counts reset for all firms")
