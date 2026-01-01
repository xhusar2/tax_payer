import os

from dotenv import load_dotenv

load_dotenv()

# Fakturoid API (OAuth2 client credentials)
FAKTUROID_SLUG = os.getenv("FAKTUROID_SLUG", "")
FAKTUROID_CLIENT_ID = os.getenv("FAKTUROID_CLIENT_ID", "")
FAKTUROID_CLIENT_SECRET = os.getenv("FAKTUROID_CLIENT_SECRET", "")
FAKTUROID_USER_AGENT = os.getenv(
    "FAKTUROID_USER_AGENT",
    "tax-payer-tool (change-me@example.com)",
)

# Tax portal
TAX_PORTAL_USERNAME = os.getenv("TAX_PORTAL_USERNAME", "")
TAX_PORTAL_PASSWORD = os.getenv("TAX_PORTAL_PASSWORD", "")

# Bank (optional)
BANK_API_URL = os.getenv("BANK_API_URL", "")
BANK_ACCOUNT_NUMBER = os.getenv("BANK_ACCOUNT_NUMBER", "")
BANK_API_KEY = os.getenv("BANK_API_KEY", "")

# Output
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

# Email settings
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USER = os.getenv("EMAIL_SMTP_USER", "")
EMAIL_SMTP_PASSWORD = os.getenv("EMAIL_SMTP_PASSWORD", "")
EMAIL_SMTP_USE_TLS = os.getenv("EMAIL_SMTP_USE_TLS", "true").lower() == "true"
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")


