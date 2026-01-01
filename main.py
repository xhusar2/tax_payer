from __future__ import annotations

import argparse
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import List

from config.settings import OUTPUT_DIR
from fakturoid.client import FakturoidClient
from parsers.invoice_parser import InvoiceParser, ParsedInvoice
from xml_generators.dph_generator import DPHGenerator
from xml_generators.dhk_generator import DHKGenerator

logger = logging.getLogger(__name__)


def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    # tax period is inclusive, but for filtering in Fakturoid we use < end
    return start, end


def fetch_and_parse_invoices(
    client: FakturoidClient,
    period_from: date,
    period_to: date,
) -> List[ParsedInvoice]:
    raw = client.iter_invoices(since=period_from, until=period_to, status="paid")
    parser = InvoiceParser()
    return [parser.parse(inv) for inv in raw]


def generate_xml(
    invoices: List[ParsedInvoice],
    period_from: date,
    period_to: date,
) -> tuple[Path, Path]:
    taxpayer_ico = os.getenv("TAXPAYER_ICO", "")
    taxpayer_dic = os.getenv("TAXPAYER_DIC", "")
    taxpayer_name = os.getenv("TAXPAYER_NAME", "")
    if not (taxpayer_ico and taxpayer_dic and taxpayer_name):
        raise RuntimeError("Set TAXPAYER_ICO, TAXPAYER_DIC and TAXPAYER_NAME in env/.env")

    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    period_tag = period_from.strftime("%Y%m")

    dph_gen = DPHGenerator(taxpayer_ico, taxpayer_dic, taxpayer_name)
    dph_tree = dph_gen.build_tree(invoices, period_from, period_to)
    dph_path = out_dir / f"dph_{period_tag}.xml"
    dph_gen.save(dph_tree, str(dph_path))

    dhk_gen = DHKGenerator(taxpayer_ico, taxpayer_dic, taxpayer_name)
    dhk_tree = dhk_gen.build_tree(invoices, period_from, period_to)
    dhk_path = out_dir / f"dhk_{period_tag}.xml"
    dhk_gen.save(dhk_tree, str(dhk_path))

    return dph_path, dhk_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate tax XML files")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Year (default: current year or previous if month is December)",
    )
    parser.add_argument(
        "--month",
        type=int,
        default=None,
        help="Month 1-12 (default: last calendar month)",
    )
    args = parser.parse_args()

    now = datetime.now()
    if args.month is not None:
        month = args.month
        year = args.year if args.year is not None else now.year
    else:
        # Default: last calendar month
        month = now.month - 1 or 12
        year = now.year if now.month > 1 else now.year - 1

    period_from, period_to = _month_range(year, month)
    logger.info(f"Processing tax period: {period_from} to {period_to}")

    client = FakturoidClient()
    invoices = fetch_and_parse_invoices(client, period_from, period_to)
    logger.info(f"Fetched {len(invoices)} invoices")

    dph_path, dhk_path = generate_xml(invoices, period_from, period_to)
    logger.info(f"DPH XML: {dph_path}")
    logger.info(f"DHK XML: {dhk_path}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()





