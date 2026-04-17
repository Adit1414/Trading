import smtplib
from email.message import EmailMessage
import logging

logger = logging.getLogger(__name__)

# Configure these with an App Password from Gmail or an SMTP provider like SendGrid
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-email@gmail.com"
SENDER_PASSWORD = "your-app-password"
FRONTEND_URL = "http://localhost:5173"

def send_trade_email(user_email: str, subject: str, body: str):
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = user_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {user_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {e}")