"""
Additional data extraction utilities.
"""
import re
from decimal import Decimal
from typing import Optional
import pdfplumber


class DataExtractor:
    """
    Fallback text-based extraction when image processing isn't suitable.
    Uses pdfplumber for text extraction.
    """

    def __init__(self):
        self.date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{4}-\d{2}-\d{2}',
            r'[A-Z][a-z]+ \d{1,2}, \d{4}',
        ]
        self.amount_pattern = r'\$[\d,]+\.?\d*'

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from a PDF file."""
        text_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        return '\n'.join(text_content)

    def find_invoice_number(self, text: str) -> Optional[str]:
        """Try to find invoice number in text."""
        patterns = [
            r'Invoice\s*#?\s*:?\s*(\w+[-\w]*)',
            r'Invoice\s+Number\s*:?\s*(\w+[-\w]*)',
            r'Inv\s*#?\s*:?\s*(\w+[-\w]*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def find_total_amount(self, text: str) -> Optional[Decimal]:
        """Try to find total amount in text."""
        patterns = [
            r'Total\s*:?\s*\$?([\d,]+\.?\d*)',
            r'Amount\s+Due\s*:?\s*\$?([\d,]+\.?\d*)',
            r'Grand\s+Total\s*:?\s*\$?([\d,]+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return Decimal(amount_str)
                except (ValueError, TypeError):
                    continue
        return None

    def extract_tables(self, pdf_path: str) -> list[list[list[str]]]:
        """Extract tables from PDF pages."""
        tables = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
        return tables
