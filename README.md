# tax_payer

Tooling for:
- pulling invoices from Fakturoid,
- parsing them into a VAT‑centric model,
- generating XML for DPH and kontrolní hlášení (DHK).

This is deliberately minimal and focused; you can wire it into cron, CI,
or run manually once a month.

## Setup

Create and activate a venv however you like, then:

```bash
pip install -r requirements.txt
```

Create a `.env` in the project root (or export env vars some other way):

```env
FAKTUROID_SLUG=your-fakturoid-subdomain
FAKTUROID_CLIENT_ID=your-client-id
FAKTUROID_CLIENT_SECRET=your-client-secret
FAKTUROID_USER_AGENT=tax-payer-tool (you@example.com)

TAXPAYER_ICO=12345678
TAXPAYER_DIC=CZ12345678
TAXPAYER_NAME=Your s.r.o.

TAX_PORTAL_USERNAME=optional
TAX_PORTAL_PASSWORD=optional

BANK_API_URL=optional
BANK_ACCOUNT_NUMBER=optional
BANK_API_KEY=optional

OUTPUT_DIR=./output
```

Run:

```bash
python main.py
```

By default it:
- takes last calendar month as the period,
- fetches paid invoices from Fakturoid for that period,
- writes `dph_YYYYMM.xml` and `dhk_YYYYMM.xml` into `OUTPUT_DIR`.

The XML shapes are intentionally simple and not 1:1 with FS schemas yet.
Once you download the official XSDs for DPH and DPHK1 we can tighten
element names and add validation using `xmlschema`.


