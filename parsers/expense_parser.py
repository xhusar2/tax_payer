from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class ParsedExpense:
    """Fakturoid expense (náklad) normalized for DPH / KH."""

    number: str
    evidence_number: str
    supplier_dic: Optional[str]
    total_with_vat: float
    taxable_supply_date: Optional[datetime]
    received_on: Optional[datetime]
    issued_on: Optional[datetime]
    base_21: float
    vat_21: float
    base_12: float
    vat_12: float
    tax_deductible: bool
    proportional_vat_deduction: int
    transferred_tax_liability: bool
    status: str

    def dppd_for_kh(self) -> datetime:
        return (
            self.taxable_supply_date
            or self.issued_on
            or self.received_on
            or datetime.min
        )


class ExpenseParser:
    """Map Fakturoid expense JSON to VAT buckets (21% / 12% CZ rates)."""

    @staticmethod
    def parse(expense: Dict[str, Any]) -> ParsedExpense:
        issued = ExpenseParser._parse_date(expense.get("issued_on"))
        tfd = ExpenseParser._parse_date(expense.get("taxable_fulfillment_due"))
        received = ExpenseParser._parse_date(expense.get("received_on"))

        raw_dic = expense.get("supplier_vat_no") or ""
        supplier_dic = ExpenseParser._normalize_dic(str(raw_dic) if raw_dic else "")

        ev = expense.get("original_number") or expense.get("number") or expense.get("id")
        evidence_number = str(ev).strip()[:60] if ev is not None else ""

        total = float(expense.get("native_total") or expense.get("total") or 0)

        base_21 = base_12 = 0.0
        vat_21 = vat_12 = 0.0

        summary = expense.get("vat_rates_summary")
        if isinstance(summary, list):
            for entry in summary:
                if not isinstance(entry, dict):
                    continue
                rate = float(entry.get("vat_rate") or 0)
                b = float(entry.get("native_base") or entry.get("base") or 0)
                v = float(entry.get("native_vat") or entry.get("vat") or 0)
                if rate >= 20:
                    base_21 += b
                    vat_21 += v
                elif rate >= 10:
                    base_12 += b
                    vat_12 += v
        else:
            sub = float(expense.get("native_subtotal") or expense.get("subtotal") or 0)
            tvat = float(
                expense.get("native_total_vat")
                or expense.get("total_vat")
                or 0
            )
            lines = expense.get("lines") or []
            rates = [
                float((ln or {}).get("vat_rate") or 0)
                for ln in lines
                if isinstance(ln, dict)
            ]
            dominant = max(set(rates), key=rates.count) if rates else 21.0
            if dominant >= 20:
                base_21, vat_21 = sub, tvat
            elif dominant >= 10:
                base_12, vat_12 = sub, tvat

        return ParsedExpense(
            number=str(expense.get("number") or expense.get("id") or ""),
            evidence_number=evidence_number,
            supplier_dic=supplier_dic or None,
            total_with_vat=total,
            taxable_supply_date=tfd,
            received_on=received,
            issued_on=issued,
            base_21=base_21,
            vat_21=vat_21,
            base_12=base_12,
            vat_12=vat_12,
            tax_deductible=bool(expense.get("tax_deductible", True)),
            proportional_vat_deduction=int(expense.get("proportional_vat_deduction") or 100),
            transferred_tax_liability=bool(expense.get("transferred_tax_liability", False)),
            status=str(expense.get("status") or ""),
        )

    @staticmethod
    def _normalize_dic(dic: str) -> str:
        s = dic.replace("CZ", "").replace("cz", "").replace(" ", "").strip()
        return "".join(c for c in s if c.isdigit())

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.fromisoformat(value.split("T")[0])

    @staticmethod
    def is_eligible_for_odpocet(exp: ParsedExpense) -> bool:
        if exp.status and exp.status != "paid":
            return False
        if not exp.tax_deductible:
            return False
        if exp.transferred_tax_liability:
            return False
        if exp.proportional_vat_deduction != 100:
            return False
        return True

    @staticmethod
    def canonical_tax_period_date(exp: ParsedExpense) -> Optional[date]:
        """
        One date per expense for month assignment (avoids counting twice when
        issue date is April but Fakturoid přijetí/DUZP is filled in May).
        Priority: issued_on → taxable_fulfillment_due → received_on.
        """
        for dt in (exp.issued_on, exp.taxable_supply_date, exp.received_on):
            if dt:
                return dt.date()
        return None

    @staticmethod
    def in_tax_period(exp: ParsedExpense, period_from: date, period_to: date) -> bool:
        d = ExpenseParser.canonical_tax_period_date(exp)
        if not d:
            return False
        return period_from <= d < period_to

    @staticmethod
    def exclusion_reason(
        exp: ParsedExpense, period_from: date, period_to: date
    ) -> Optional[str]:
        """Human-readable reason when an expense is not included; None if it would be included."""
        if not ExpenseParser.in_tax_period(exp, period_from, period_to):
            d = ExpenseParser.canonical_tax_period_date(exp)
            if d is None:
                return "missing issued_on, taxable_fulfillment_due, and received_on"
            return (
                f"assigned to {d.isoformat()} (issue → DUZP → received), "
                f"outside {period_from.isoformat()}..{period_to.isoformat()}"
            )
        if not ExpenseParser.is_eligible_for_odpocet(exp):
            parts: List[str] = []
            if exp.status and exp.status != "paid":
                parts.append(f"status={exp.status!r} (need paid)")
            if not exp.tax_deductible:
                parts.append("tax_deductible=false")
            if exp.transferred_tax_liability:
                parts.append("reverse charge")
            if exp.proportional_vat_deduction != 100:
                parts.append(f"proportional_vat_deduction={exp.proportional_vat_deduction}%")
            return "; ".join(parts) or "not eligible for odpočet"
        return None
