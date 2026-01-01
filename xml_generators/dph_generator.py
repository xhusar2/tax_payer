from __future__ import annotations

import hashlib
import os
from datetime import date, datetime
from typing import Iterable, Optional

from lxml import etree

from parsers.invoice_parser import ParsedInvoice


class DPHGenerator:
    """
    DPH XML generator.
    
    Generates DPHDP3 format matching the official Finanční správa schema.
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
        taxpayer_okec: str = "631000",
    ) -> None:
        self.taxpayer_ico = taxpayer_ico
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
        self.taxpayer_okec = taxpayer_okec

    def build_tree(
        self,
        invoices: Iterable[ParsedInvoice],
        period_from: date,
        period_to: date,
    ) -> etree._ElementTree:
        # Get taxpayer_dic from first invoice if available
        invoice_list = list(invoices)
        taxpayer_dic_from_invoice = None
        if invoice_list:
            first_inv = invoice_list[0]
            if first_inv.taxpayer_dic:
                taxpayer_dic_from_invoice = first_inv.taxpayer_dic.replace("CZ", "").replace("cz", "")
        
        # Use taxpayer_dic from invoice if available, otherwise fall back to config
        final_taxpayer_dic = taxpayer_dic_from_invoice or self.taxpayer_dic
        
        # Root: Pisemnost
        root = etree.Element("Pisemnost", nazevSW="EPO MF ČR", verzeSW="47.3.1")
        
        # DPHDP3 document
        dphdp3 = etree.SubElement(root, "DPHDP3", verzePis="03.01")
        
        # VetaD - Document header
        month = period_from.month
        year = period_from.year
        submission_date = datetime.now().strftime("%d.%m.%Y")
        veta_d = etree.SubElement(
            dphdp3,
            "VetaD",
            c_okec=self.taxpayer_okec,
            d_poddp=submission_date,
            dapdph_forma="B",
            dokument="DP3",
            k_uladis="DPH",
            mesic=str(month),
            rok=str(year),
            trans="A",
            typ_platce="P",
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
        
        # Format title (remove period if present for VetaP)
        title_formatted = title.rstrip(".") if title else ""
        
        veta_p = etree.SubElement(
            dphdp3,
            "VetaP",
            c_orient=self.taxpayer_house_number_pop or "",
            c_pop=self.taxpayer_house_number or "",
            c_telef=self.taxpayer_phone or "",
            c_ufo=self.taxpayer_ufo,
            c_pracufo=self.taxpayer_pracufo,
            dic=final_taxpayer_dic,
            email=self.taxpayer_email or "",
            jmeno=first_name,
            naz_obce=self.taxpayer_city or "",
            prijmeni=last_name,
            psc=self.taxpayer_zip or "",
            stat=self.taxpayer_country,
            titul=title_formatted,
            typ_ds="F",
            ulice=self.taxpayer_street or "",
        )
        
        # Calculate totals from all invoices
        total_base = 0.0
        total_vat = 0.0
        
        for inv in invoice_list:
            total_base += inv.vat_base
            total_vat += inv.vat_amount
        
        # Veta1 - Totals (rounded, no decimals)
        obrat23 = f"{int(round(total_base))}"
        dan23 = f"{int(round(total_vat))}"
        veta1 = etree.SubElement(
            dphdp3,
            "Veta1",
            dan23=dan23,
            obrat23=obrat23,
        )
        
        # Veta6 - Additional totals
        dan_zocelk = f"{int(round(total_vat))}"
        dano = "0"
        dano_da = f"{int(round(total_vat))}"
        dano_no = "0"
        odp_zocelk = "0"
        veta6 = etree.SubElement(
            dphdp3,
            "Veta6",
            dan_zocelk=dan_zocelk,
            dano=dano,
            dano_da=dano_da,
            dano_no=dano_no,
            odp_zocelk=odp_zocelk,
        )
        
        # Kontrola - File control/checksum
        dic_formatted = final_taxpayer_dic.zfill(10)
        file_date = datetime.now().strftime("%Y%m%d")
        file_time = datetime.now().strftime("%H%M%S")
        filename = f"DPHDP3-{dic_formatted}-{file_date}-{file_time}"
        
        # Calculate checksum - serialize DPHDP3 element only
        xml_str = etree.tostring(dphdp3, encoding="utf-8", xml_declaration=False)
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
