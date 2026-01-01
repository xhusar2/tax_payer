from __future__ import annotations

import os
from datetime import date
from typing import Iterable

from lxml import etree

from parsers.invoice_parser import ParsedInvoice, ParsedLine


class DHKGenerator:
    """
    Kontrolní hlášení (KH / DHK) XML generator.

    Same story as with DPH – this is a sane, testable structure you can already
    validate visually, later we align it with the official DPHK1 XSD.
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
        root = etree.Element("KontrolniHlaseni")

        header = etree.SubElement(root, "Hlavicka")
        etree.SubElement(header, "ICO").text = self.taxpayer_ico
        etree.SubElement(header, "DIC").text = self.taxpayer_dic
        etree.SubElement(header, "Nazev").text = self.taxpayer_name
        etree.SubElement(header, "ObdobiOd").text = period_from.isoformat()
        etree.SubElement(header, "ObdobiDo").text = period_to.isoformat()

        data = etree.SubElement(root, "Data")

        for inv in invoices:
            inv_el = etree.SubElement(data, "Faktura")
            etree.SubElement(inv_el, "Cislo").text = inv.invoice_number
            etree.SubElement(inv_el, "DatumVystaveni").text = inv.issue_date.date().isoformat()
            if inv.taxable_supply_date:
                etree.SubElement(inv_el, "DatumPlneni").text = inv.taxable_supply_date.date().isoformat()

            if inv.customer_dic:
                etree.SubElement(inv_el, "OdberatelskeDIC").text = inv.customer_dic
            if inv.customer_ico:
                etree.SubElement(inv_el, "OdberatelskeICO").text = inv.customer_ico
            if inv.customer_name:
                etree.SubElement(inv_el, "OdberatelJmeno").text = inv.customer_name

            lines_el = etree.SubElement(inv_el, "Polozky")
            for line in inv.lines:
                self._append_line(lines_el, line)

        return etree.ElementTree(root)

    @staticmethod
    def _append_line(parent: etree._Element, line: ParsedLine) -> None:
        l_el = etree.SubElement(parent, "Polozka")
        etree.SubElement(l_el, "Nazev").text = line.name
        etree.SubElement(l_el, "Mnozstvi").text = f"{line.quantity:.2f}"
        etree.SubElement(l_el, "JednotkovaCena").text = f"{line.unit_price:.2f}"
        etree.SubElement(l_el, "Sazba").text = f"{line.vat_rate:.0f}"
        etree.SubElement(l_el, "Dan").text = f"{line.vat_amount:.2f}"
        etree.SubElement(l_el, "CelkovaCena").text = f"{line.total:.2f}"

    @staticmethod
    def save(tree: etree._ElementTree, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tree.write(path, encoding="utf-8", xml_declaration=True, pretty_print=True)





