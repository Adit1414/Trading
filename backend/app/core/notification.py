import smtplib
from email.message import EmailMessage
import logging
from app.core.config import settings # <-- Injecting the softcoded environment variables

logger = logging.getLogger(__name__)

def send_trade_email(user_email: str, subject: str, body: str):
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = settings.SENDER_EMAIL
        msg['To'] = user_email

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {e}")