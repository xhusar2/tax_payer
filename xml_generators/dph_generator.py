from __future__ import annotations

import os
from datetime import date
from typing import Iterable

from lxml import etree

from parsers.invoice_parser import ParsedInvoice


class DPHGenerator:
    """
    DPH XML generator.

    This is intentionally simple and *not* strictly schema‑accurate yet.
    Once you download the official XSD from Finanční správa, we can tune
    element/attribute names accordingly.
    """

    def __init__(self, taxpayer_ico: str, taxpayer_dic: str, taxpayer_name: str) -> None:
        self.taxpayer_ico = taxpayer_ico
        self.taxpayer_dic = taxpayer_dic
        self.taxpayer_name = taxpayer_name

    def build_tree(
        self,
        invoices: Iterable[ParsedInvoice],
        period_from: date,
        period_to: date,
    ) -> etree._ElementTree:
        root = etree.Element("DPHPriznani")

        header = etree.SubElement(root, "Hlavicka")
        etree.SubElement(header, "ICO").text = self.taxpayer_ico
        etree.SubElement(header, "DIC").text = self.taxpayer_dic
        etree.SubElement(header, "Nazev").text = self.taxpayer_name
        etree.SubElement(header, "ObdobiOd").text = period_from.isoformat()
        etree.SubElement(header, "ObdobiDo").text = period_to.isoformat()

        data = etree.SubElement(root, "Data")

        for inv in invoices:
            f_el = etree.SubElement(data, "Faktura")
            etree.SubElement(f_el, "Cislo").text = inv.invoice_number
            etree.SubElement(f_el, "DatumVystaveni").text = inv.issue_date.date().isoformat()
            if inv.taxable_supply_date:
                etree.SubElement(f_el, "DatumPlneni").text = inv.taxable_supply_date.date().isoformat()

            etree.SubElement(f_el, "ZakladDane").text = f"{inv.vat_base:.2f}"
            etree.SubElement(f_el, "Dan").text = f"{inv.vat_amount:.2f}"
            etree.SubElement(f_el, "Sazba").text = f"{inv.vat_rate:.0f}"

            if inv.customer_dic:
                etree.SubElement(f_el, "OdberatelskeDIC").text = inv.customer_dic

        return etree.ElementTree(root)

    @staticmethod
    def save(tree: etree._ElementTree, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tree.write(path, encoding="utf-8", xml_declaration=True, pretty_print=True)





