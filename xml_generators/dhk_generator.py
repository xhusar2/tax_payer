from __future__ import annotations

import hashlib
import logging
import os
from datetime import date, datetime
from typing import Iterable, List, Optional

from lxml import etree

from parsers.expense_parser import ParsedExpense
from parsers.invoice_parser import ParsedInvoice
from xml_generators.czk import czk_ceil_tax, czk_round

logger = logging.getLogger(__name__)


class DHKGenerator:
    """
    Kontrolní hlášení (KH / DHK) XML generator.
    
    Generates DPHKH1 format matching the official Finanční správa schema.
    """

    def __init__(
        self,
        taxpayer_ico: str,
        taxpayer_dic: str,
        taxpayer_name: str,
        taxpayer_title: str = "",
        taxpayer_first_name: str = "",
        taxpayer_last_name: str = "",
        taxpayer_street: str = "",
        taxpayer_house_number: str = "",
        taxpayer_house_number_pop: str = "",
        taxpayer_city: str = "",
        taxpayer_zip: str = "",
        taxpayer_country: str = "ČESKÁ REPUBLIKA",
        taxpayer_email: str = "",
        taxpayer_phone: str = "",
        taxpayer_ufo: str = "451",
        taxpayer_pracufo: str = "2002",
    ) -> None:
        self.taxpayer_ico = taxpayer_ico
        # Strip CZ prefix if present
        self.taxpayer_dic = taxpayer_dic.replace("CZ", "").replace("cz", "")
        self.taxpayer_name = taxpayer_name
        self.taxpayer_title = taxpayer_title
        self.taxpayer_first_name = taxpayer_first_name
        self.taxpayer_last_name = taxpayer_last_name
        self.taxpayer_street = taxpayer_street
        self.taxpayer_house_number = taxpayer_house_number
        self.taxpayer_house_number_pop = taxpayer_house_number_pop
        self.taxpayer_city = taxpayer_city
        self.taxpayer_zip = taxpayer_zip
        self.taxpayer_country = taxpayer_country
        self.taxpayer_email = taxpayer_email
        self.taxpayer_phone = taxpayer_phone
        self.taxpayer_ufo = taxpayer_ufo
        self.taxpayer_pracufo = taxpayer_pracufo

    @staticmethod
    def _parse_evid_date_from_invoice_number(invoice_number: str) -> Optional[str]:
        """Try to parse date from invoice number like '2025-10-01'."""
        try:
            # Try to parse as date YYYY-MM-DD
            date_obj = datetime.strptime(invoice_number, "%Y-%m-%d")
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _format_dan(vat: float) -> str:
        return f"{czk_ceil_tax(vat)}"

    def build_tree(
        self,
        invoices: Iterable[ParsedInvoice],
        period_from: date,
        period_to: date,
        expenses: Optional[Iterable[ParsedExpense]] = None,
    ) -> etree._ElementTree:
        # Get taxpayer_dic from first invoice if available
        taxpayer_dic_from_invoice = None
        invoice_list = list(invoices)
        if invoice_list:
            first_inv = invoice_list[0]
            if first_inv.taxpayer_dic:
                taxpayer_dic_from_invoice = first_inv.taxpayer_dic.replace("CZ", "").replace("cz", "")
        
        # Use taxpayer_dic from invoice if available, otherwise fall back to config
        final_taxpayer_dic = taxpayer_dic_from_invoice or self.taxpayer_dic
        
        # Root: Pisemnost
        root = etree.Element("Pisemnost", nazevSW="EPO MF ČR", verzeSW="46.2.1")
        
        # DPHKH1 document
        dhkh1 = etree.SubElement(root, "DPHKH1", verzePis="03.01")
        
        # VetaD - Document header
        month = period_from.month
        year = period_from.year
        submission_date = datetime.now().strftime("%d.%m.%Y")
        veta_d = etree.SubElement(
            dhkh1,
            "VetaD",
            dokument="KH1",
            k_uladis="DPH",
            mesic=str(month),
            rok=str(year),
            d_poddp=submission_date,
            khdph_forma="B",
        )
        
        # VetaP - Taxpayer info
        # Parse name if not provided separately
        first_name = self.taxpayer_first_name
        last_name = self.taxpayer_last_name
        title = self.taxpayer_title
        
        if not first_name and not last_name:
            # Try to parse title and name from taxpayer_name
            name_parts = self.taxpayer_name.split()
            common_titles = ["Ing.", "Mgr.", "Bc.", "MUDr.", "JUDr.", "Dr.", "PhDr.", "RNDr."]
            
            if len(name_parts) >= 3 and name_parts[0] in common_titles:
                # Title + first + last
                if not title:
                    title = name_parts[0]
                first_name = name_parts[1]
                last_name = " ".join(name_parts[2:])
            elif len(name_parts) == 2:
                first_name = name_parts[0]
                last_name = name_parts[1]
            else:
                first_name = self.taxpayer_name
                last_name = ""
        
        veta_p = etree.SubElement(
            dhkh1,
            "VetaP",
            c_ufo=self.taxpayer_ufo,
            c_pracufo=self.taxpayer_pracufo,
            dic=final_taxpayer_dic,
            typ_ds="F",
            titul=title or "",
            jmeno=first_name,
            prijmeni=last_name,
            ulice=self.taxpayer_street or "",
            c_orient=self.taxpayer_house_number or "",
            c_pop=self.taxpayer_house_number_pop or "",
            naz_obce=self.taxpayer_city or "",
            psc=self.taxpayer_zip or "",
            stat=self.taxpayer_country,
            email=self.taxpayer_email or "",
            c_telef=self.taxpayer_phone or "",
        )
        
        # VetaA4 - Invoice data (one per invoice)
        total_base = 0.0
        row_num = 1
        
        for inv in invoice_list:
            # Calculate totals for 21% VAT rate
            base = inv.vat_base
            vat = inv.vat_amount
            
            total_base += base
            
            # Format taxable supply date as DD.MM.YYYY for dppd
            supply_date_str = (
                inv.taxable_supply_date.strftime("%d.%m.%Y")
                if inv.taxable_supply_date
                else inv.issue_date.strftime("%d.%m.%Y")
            )
            
            # Parse evidence date from invoice number (if it's in YYYY-MM-DD format)
            evid_date = self._parse_evid_date_from_invoice_number(inv.invoice_number)
            if not evid_date:
                # Fallback to issue_date if invoice number doesn't contain date
                evid_date = inv.issue_date.strftime("%Y-%m-%d")
            
            # Format amounts: zakl_dane1 as integer (no decimal), dan1 as integer if whole, otherwise 2 decimals
            # Both are in CZK, stored as strings
            zakl_dane1 = f"{czk_round(base)}"
            dan1 = self._format_dan(vat)
            
            veta_a4 = etree.SubElement(
                dhkh1,
                "VetaA4",
                c_radku=str(row_num),
                dic_odb=inv.customer_dic or "",
                c_evid_dd=evid_date,
                dppd=supply_date_str,
                zakl_dane1=zakl_dane1,
                dan1=dan1,
                kod_rezim_pl="0",
                zdph_44="N",
            )
            row_num += 1

        expense_list: List[ParsedExpense] = list(expenses or [])
        pln23_kh = 0.0
        pln5_kh = 0.0

        for exp in expense_list:
            if exp.total_with_vat > 10000 and not exp.supplier_dic:
                logger.warning(
                    "Expense %s over 10k CZK incl. VAT has no supplier DIČ — "
                    "omitted from KH B2/B3 (fix in Fakturoid); DPH still includes it if parsed.",
                    exp.number or exp.evidence_number,
                )
                continue
            if exp.total_with_vat > 10000 and exp.supplier_dic:
                dppd = exp.dppd_for_kh().strftime("%d.%m.%Y")
                evid = exp.evidence_number or exp.number or str(row_num)
                sd = exp.supplier_dic
                if len(sd) > 10:
                    sd = sd[-10:]
                dic_dod = sd.zfill(10)
                b1, v1 = exp.base_21, exp.vat_21
                b2, v2 = exp.base_12, exp.vat_12
                if not (b1 or v1 or b2 or v2):
                    logger.warning(
                        "Expense %s has no VAT bases in summary — skipping B2",
                        exp.number or exp.evidence_number,
                    )
                    continue
                pln23_kh += b1
                pln5_kh += b2
                attrs = dict(
                    c_radku=str(row_num),
                    dic_dod=dic_dod,
                    c_evid_dd=evid[:60],
                    dppd=dppd,
                    pomer="N",
                    zdph_44="N",
                )
                if b1 or v1:
                    attrs["zakl_dane1"] = f"{czk_round(b1)}"
                    attrs["dan1"] = self._format_dan(v1)
                if b2 or v2:
                    attrs["zakl_dane2"] = f"{czk_round(b2)}"
                    attrs["dan2"] = self._format_dan(v2)
                etree.SubElement(dhkh1, "VetaB2", **attrs)
                row_num += 1

        small = [e for e in expense_list if e.total_with_vat <= 10000]
        if small:
            sb1 = sum(e.base_21 for e in small)
            sv1 = sum(e.vat_21 for e in small)
            sb2 = sum(e.base_12 for e in small)
            sv2 = sum(e.vat_12 for e in small)
            pln23_kh += sb1
            pln5_kh += sb2
            b3attrs = {}
            if sb1 or sv1:
                b3attrs["zakl_dane1"] = f"{czk_round(sb1)}"
                b3attrs["dan1"] = self._format_dan(sv1)
            if sb2 or sv2:
                b3attrs["zakl_dane2"] = f"{czk_round(sb2)}"
                b3attrs["dan2"] = self._format_dan(sv2)
            if b3attrs:
                etree.SubElement(dhkh1, "VetaB3", **b3attrs)

        # VetaC - Summary totals
        obrat23 = f"{czk_round(total_base)}"
        veta_c_attrs = {"obrat23": obrat23}
        if pln23_kh:
            veta_c_attrs["pln23"] = f"{czk_round(pln23_kh)}"
        if pln5_kh:
            veta_c_attrs["pln5"] = f"{czk_round(pln5_kh)}"
        veta_c = etree.SubElement(dhkh1, "VetaC", **veta_c_attrs)
        
        # Kontrola - File control/checksum
        # Generate filename: DPHKH1-{DIC with leading zero}-{YYYYMMDD}-{HHMMSS}
        # DIC should be 10 digits with leading zero if needed
        dic_formatted = final_taxpayer_dic.zfill(10)
        file_date = datetime.now().strftime("%Y%m%d")
        file_time = datetime.now().strftime("%H%M%S")
        filename = f"DPHKH1-{dic_formatted}-{file_date}-{file_time}"
        
        # Calculate checksum - need to serialize DPHKH1 element only
        xml_str = etree.tostring(dhkh1, encoding="utf-8", xml_declaration=False)
        file_length = len(xml_str)
        checksum = hashlib.md5(xml_str).hexdigest()
        
        kontrola = etree.SubElement(root, "Kontrola")
        soubor = etree.SubElement(
            kontrola,
            "Soubor",
            Delka=str(file_length),
            KC=checksum,
            Nazev=filename,
            c_ufo=self.taxpayer_ufo,
        )
        
        return etree.ElementTree(root)

    @staticmethod
    def save(tree: etree._ElementTree, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # Write XML to string first
        xml_bytes = etree.tostring(
            tree.getroot(),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=False,
            method="xml",
        )
        xml_str = xml_bytes.decode("utf-8")
        # Ensure XML declaration uses double quotes and uppercase UTF-8
        if xml_str.startswith("<?xml version='"):
            xml_str = xml_str.replace("<?xml version='", '<?xml version="', 1).replace("' encoding='", '" encoding="', 1).replace("'?>", '"?>', 1)
        elif 'encoding="utf-8"' in xml_str:
            xml_str = xml_str.replace('encoding="utf-8"', 'encoding="UTF-8"', 1)
        
        # Write to file
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml_str)
