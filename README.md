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

# Required taxpayer info
TAXPAYER_ICO=12345678
TAXPAYER_DIC=CZ12345678
TAXPAYER_NAME=Your s.r.o.

# Optional taxpayer details (for DHK and DPH XML - if not provided, name will be parsed from TAXPAYER_NAME)
TAXPAYER_TITLE=Ing.
TAXPAYER_FIRST_NAME=John
TAXPAYER_LAST_NAME=Doe
TAXPAYER_STREET=Main Street
TAXPAYER_HOUSE_NUMBER=123
TAXPAYER_HOUSE_NUMBER_POP=1
TAXPAYER_CITY=PRAHA 2
TAXPAYER_ZIP=12000
TAXPAYER_EMAIL=you@example.com
TAXPAYER_PHONE=123456789
TAXPAYER_UFO=451
TAXPAYER_PRACUFO=2002
TAXPAYER_OKEC=631000

TAX_PORTAL_USERNAME=optional
TAX_PORTAL_PASSWORD=optional

BANK_API_URL=optional
BANK_ACCOUNT_NUMBER=optional
BANK_API_KEY=optional

OUTPUT_DIR=./output

# Email settings (for automated monthly reports)
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password
EMAIL_SMTP_USE_TLS=true
EMAIL_RECIPIENT=your-email@gmail.com
```

Run:

```bash
python main.py
```

Or specify a specific month/year:

```bash
python main.py --month 10 --year 2024
```

To send generated XML files via email:

```bash
python main.py --send-email
```

By default it:
- takes last calendar month as the period,
- fetches paid invoices from Fakturoid for that period,
- writes `dph_YYYYMM.xml` and `dhk_YYYYMM.xml` into `OUTPUT_DIR`.

## Automated Monthly Reports (Cron)

To automatically generate and email XML files on the 1st of every month:

1. Edit your crontab:
```bash
crontab -e
```

2. Add this line (runs on 1st of every month at 2 AM):
```bash
0 2 1 * * cd /path/to/project/tax_payer && /path/to/venv/bin/python main.py --send-email >> /var/log/tax_payer.log 2>&1
```

Replace `/path/to/venv/bin/python` with your actual Python path (find it with `which python` from your venv).

**For Gmail:**
- Use an App Password 
- Go to: Google Account → Security → 2-Step Verification → App passwords
- Generate an app password and use it for `EMAIL_SMTP_PASSWORD`

