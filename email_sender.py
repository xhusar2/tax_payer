from __future__ import annotations

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def send_xml_files(
    files: List[Path],
    recipient: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    smtp_use_tls: bool = True,
    subject: Optional[str] = None,
    body: Optional[str] = None,
) -> bool:
    """
    Send XML files as email attachments.
    
    Args:
        files: List of file paths to attach
        recipient: Email address to send to
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        smtp_user: SMTP username (if authentication required)
        smtp_password: SMTP password (if authentication required)
        smtp_use_tls: Use TLS encryption
        subject: Email subject (default: auto-generated)
        body: Email body (default: auto-generated)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not files:
        logger.warning("No files to send")
        return False
    
    # Create message
    msg = MIMEMultipart()
    msg["From"] = smtp_user or recipient
    msg["To"] = recipient
    
    if subject:
        msg["Subject"] = subject
    else:
        period = files[0].stem.split("_")[-1] if files else "unknown"
        msg["Subject"] = f"Tax XML files - {period}"
    
    if body:
        msg.attach(MIMEText(body, "plain"))
    else:
        file_list = "\n".join(f"- {f.name}" for f in files)
        msg.attach(MIMEText(f"Tax XML files generated:\n\n{file_list}", "plain"))
    
    # Attach files
    for file_path in files:
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        with open(file_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=file_path.name)
            part["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
            msg.attach(part)
    
    # Send email
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_use_tls:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {recipient}")
            return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

