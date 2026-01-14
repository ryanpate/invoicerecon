"""
Invoice parsing service using Claude API for intelligent data extraction.
"""
import base64
import json
import logging
import tempfile
import os
from decimal import Decimal
from typing import Optional
from django.conf import settings
from django.utils import timezone
import anthropic
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def get_file_path(file_field):
    """
    Get a local file path for a file field, handling both local and S3 storage.
    For S3, downloads to a temp file and returns the path.
    """
    try:
        # Try local path first
        return file_field.path
    except NotImplementedError:
        # S3 storage - download to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.write(file_field.read())
        temp_file.close()
        return temp_file.name

INVOICE_EXTRACTION_PROMPT = """
Analyze this legal invoice and extract all information into a structured JSON format.

Extract the following fields:
- client_name: Full client name
- matter_number: Matter/case number
- invoice_number: Invoice number
- invoice_date: Date in YYYY-MM-DD format
- due_date: Due date in YYYY-MM-DD format (if present)
- billing_attorney: Primary attorney name

For line_items, extract each billable entry with:
- date: Entry date in YYYY-MM-DD format
- description: Full work description
- timekeeper: Person who did the work
- hours: Hours billed (decimal)
- rate: Hourly rate (decimal)
- amount: Line total (decimal)
- type: One of "time", "expense", "flat_fee"

Also extract totals:
- subtotal: Sum before taxes
- taxes: Tax amount
- total: Grand total
- retainer_applied: Any retainer credit applied
- amount_due: Final amount due

Return ONLY valid JSON in this exact format:
{
  "client_name": "string",
  "matter_number": "string",
  "invoice_number": "string",
  "invoice_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD or null",
  "billing_attorney": "string",
  "line_items": [
    {
      "date": "YYYY-MM-DD",
      "description": "string",
      "timekeeper": "string",
      "hours": 0.0,
      "rate": 0.00,
      "amount": 0.00,
      "type": "time|expense|flat_fee"
    }
  ],
  "subtotal": 0.00,
  "taxes": 0.00,
  "total": 0.00,
  "retainer_applied": 0.00,
  "amount_due": 0.00,
  "extraction_confidence": 0.0 to 1.0,
  "extraction_notes": "Any issues or uncertainties"
}

Be precise with numbers. Use null for missing fields. Confidence should reflect how certain you are about the extraction quality.
"""


class InvoiceParser:
    """Parse invoice PDFs using Claude API."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def extract_from_pdf(self, pdf_path: str) -> dict:
        """
        Extract invoice data from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with extracted invoice data
        """
        # Convert PDF pages to images
        images = self._pdf_to_images(pdf_path)

        if not images:
            return {
                'error': 'Failed to convert PDF to images',
                'extraction_confidence': 0.0
            }

        # Build message content with images
        content = []
        for i, image_data in enumerate(images):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_data
                }
            })

        content.append({
            "type": "text",
            "text": INVOICE_EXTRACTION_PROMPT
        })

        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": content}
                ]
            )

            # Parse the response
            response_text = response.content[0].text

            # Extract JSON from response
            extracted_data = self._parse_json_response(response_text)

            # Add API usage info
            extracted_data['api_tokens_used'] = (
                response.usage.input_tokens + response.usage.output_tokens
            )

            return extracted_data

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return {
                'error': str(e),
                'extraction_confidence': 0.0
            }
        except Exception as e:
            logger.error(f"Invoice parsing error: {e}")
            return {
                'error': str(e),
                'extraction_confidence': 0.0
            }

    def _pdf_to_images(self, pdf_path: str, dpi: int = 150) -> list[str]:
        """
        Convert PDF pages to base64-encoded PNG images.

        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for rendering

        Returns:
            List of base64-encoded image strings
        """
        images = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Render page to image
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                # Convert to PNG bytes
                png_bytes = pix.tobytes("png")
                # Encode to base64
                b64_string = base64.standard_b64encode(png_bytes).decode('utf-8')
                images.append(b64_string)
            doc.close()
        except Exception as e:
            logger.error(f"PDF to image conversion error: {e}")

        return images

    def _parse_json_response(self, response_text: str) -> dict:
        """
        Parse JSON from Claude's response text.

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed dictionary
        """
        # Try to find JSON in the response
        try:
            # First try direct parsing
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end > start:
                try:
                    return json.loads(response_text[start:end].strip())
                except json.JSONDecodeError:
                    pass

        # Try to find JSON object in text
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response_text[start:end])
            except json.JSONDecodeError:
                pass

        # Return error if no valid JSON found
        return {
            'error': 'Failed to parse JSON from response',
            'raw_response': response_text[:500],
            'extraction_confidence': 0.0
        }


def process_invoice(invoice_id: str) -> bool:
    """
    Process an invoice asynchronously.

    Args:
        invoice_id: UUID of the invoice to process

    Returns:
        True if successful, False otherwise
    """
    from apps.invoices.models import Invoice, InvoiceLineItem, InvoiceProcessingLog

    try:
        invoice = Invoice.objects.get(id=invoice_id)
        invoice.status = 'processing'
        invoice.save(update_fields=['status'])

        parser = InvoiceParser()
        pdf_path = get_file_path(invoice.file)
        result = parser.extract_from_pdf(pdf_path)

        # Clean up temp file if created
        if pdf_path != invoice.file.name and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except Exception:
                pass

        # Log the processing attempt
        InvoiceProcessingLog.objects.create(
            invoice=invoice,
            action='extract',
            status='success' if 'error' not in result else 'error',
            details=result,
            api_tokens_used=result.get('api_tokens_used', 0)
        )

        if 'error' in result:
            invoice.status = 'error'
            invoice.processing_error = result['error']
            invoice.save()
            return False

        # Update invoice with extracted data
        invoice.client_name = result.get('client_name', '')
        invoice.matter_number = result.get('matter_number', '')
        invoice.invoice_number = result.get('invoice_number', '')
        invoice.billing_attorney = result.get('billing_attorney', '')

        # Parse dates
        if result.get('invoice_date'):
            try:
                from dateutil.parser import parse as parse_date
                invoice.invoice_date = parse_date(result['invoice_date']).date()
            except (ValueError, TypeError):
                pass

        if result.get('due_date'):
            try:
                from dateutil.parser import parse as parse_date
                invoice.due_date = parse_date(result['due_date']).date()
            except (ValueError, TypeError):
                pass

        # Update amounts
        invoice.subtotal = Decimal(str(result.get('subtotal', 0)))
        invoice.taxes = Decimal(str(result.get('taxes', 0)))
        invoice.total_amount = Decimal(str(result.get('total', 0)))
        invoice.retainer_applied = Decimal(str(result.get('retainer_applied', 0)))
        invoice.amount_due = Decimal(str(result.get('amount_due', 0)))

        # Update processing metadata
        invoice.extraction_confidence = result.get('extraction_confidence', 0.0)
        invoice.raw_extraction = result
        invoice.extraction_notes = result.get('extraction_notes', '')
        invoice.processed_at = timezone.now()

        # Set status based on confidence
        if invoice.extraction_confidence >= 0.8:
            invoice.status = 'extracted'
        else:
            invoice.status = 'review'

        invoice.save()

        # Create line items
        for i, item in enumerate(result.get('line_items', [])):
            line_item = InvoiceLineItem(
                invoice=invoice,
                description=item.get('description', ''),
                timekeeper=item.get('timekeeper', ''),
                hours=Decimal(str(item.get('hours', 0))),
                rate=Decimal(str(item.get('rate', 0))),
                amount=Decimal(str(item.get('amount', 0))),
                item_type=item.get('type', 'time'),
                line_number=i + 1
            )

            if item.get('date'):
                try:
                    from dateutil.parser import parse as parse_date
                    line_item.date = parse_date(item['date']).date()
                except (ValueError, TypeError):
                    pass

            line_item.save()

        # Update firm's invoice count
        invoice.firm.invoices_processed_this_month += 1
        invoice.firm.save(update_fields=['invoices_processed_this_month'])

        return True

    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error processing invoice {invoice_id}: {e}")
        if 'invoice' in locals():
            invoice.status = 'error'
            invoice.processing_error = str(e)
            invoice.save()
        return False
