from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ParsedLine:
    name: str
    quantity: float
    unit_price: float
    vat_rate: float
    vat_amount: float
    total: float


@dataclass
class ParsedInvoice:
    invoice_number: str
    issue_date: datetime
    taxable_supply_date: Optional[datetime]
    total: float
    vat_base: float
    vat_amount: float
    vat_rate: float
    customer_ico: Optional[str]
    customer_dic: Optional[str]
    customer_name: Optional[str]
    taxpayer_dic: Optional[str]
    lines: List[ParsedLine]


class InvoiceParser:
    """Translate raw Fakturoid invoice JSON to a simpler VAT-centric structure."""

    @staticmethod
    def parse(invoice: Dict[str, Any]) -> ParsedInvoice:
        issued_on = InvoiceParser._parse_date(invoice.get("issued_on"))
        taxable_supply_date = InvoiceParser._parse_date(
            invoice.get("taxable_fulfillment_due")
            or invoice.get("issued_on")
        )

        lines_raw: List[Dict[str, Any]] = invoice.get("lines", []) or []
        lines = [InvoiceParser._parse_line(l) for l in lines_raw]

        # Extract taxpayer DIC from invoice (dic field is the taxpayer's DIC)
        taxpayer_dic = invoice.get("dic")
        
        # Extract VAT amount from vat_rates_summary.vat
        vat_rates_summary = invoice.get("vat_rates_summary")
        if isinstance(vat_rates_summary, list):
            # Sum up VAT from all entries in the list
            vat_amount = sum(float(entry.get("vat", 0) or 0) for entry in vat_rates_summary if isinstance(entry, dict))
        elif isinstance(vat_rates_summary, dict):
            vat_amount = float(vat_rates_summary.get("vat", 0) or 0)
        else:
            # Fallback to total_vat if vat_rates_summary is not available
            vat_amount = float(invoice.get("total_vat", 0) or 0)

        return ParsedInvoice(
            invoice_number=str(invoice.get("number") or invoice.get("id")),
            issue_date=issued_on or datetime.min,
            taxable_supply_date=taxable_supply_date,
            total=float(invoice.get("total", 0) or 0),
            vat_base=float(invoice.get("subtotal", 0) or 0),
            vat_amount=vat_amount,
            vat_rate=InvoiceParser._extract_vat_rate(lines),
            customer_ico=(invoice.get("subject") or {}).get("ico"),
            customer_dic=invoice.get("client_registration_no"),
            customer_name=(invoice.get("subject") or {}).get("name"),

            taxpayer_dic=taxpayer_dic,
            lines=lines,
        )

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        # Fakturoid dates are ISO, usually `YYYY-MM-DD`
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            # be tolerant to timestamps etc.
            return datetime.fromisoformat(value.split("T")[0])

    @staticmethod
    def _parse_line(line: Dict[str, Any]) -> ParsedLine:
        return ParsedLine(
            name=str(line.get("name") or ""),
            quantity=float(line.get("quantity", 1) or 1),
            unit_price=float(line.get("unit_price", 0) or 0),
            vat_rate=float(line.get("vat_rate", 0) or 0),
            vat_amount=float(line.get("vat_amount", 0) or 0),
            total=float(line.get("total", 0) or 0),
        )

    @staticmethod
    def _extract_vat_rate(lines: List[ParsedLine]) -> float:
        if not lines:
            return 0.0
        rates = [l.vat_rate for l in lines if l.vat_rate]
        if not rates:
            return 0.0
        # most common rate
        return max(set(rates), key=rates.count)





