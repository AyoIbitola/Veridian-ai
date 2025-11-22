import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.db.models import Incident, Tenant
from app.db.events import get_db
from sqlalchemy.future import select

logger = logging.getLogger("Notifications")

class NotificationService:
    def __init__(self):
        # System-wide defaults (optional fallback)
        self.default_email_enabled = bool(settings.SMTP_SERVER and settings.SMTP_USER)
        self.default_slack_enabled = bool(settings.SLACK_WEBHOOK_URL)

    async def send_email(self, to: str, subject: str, body: str):
        if not self.default_email_enabled:
            logger.warning("Email notification skipped: System SMTP settings not configured.")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_USER
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            # Connect to SMTP Server
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent to {to}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    async def send_slack(self, message: str, webhook_url: str = None):
        url = webhook_url or settings.SLACK_WEBHOOK_URL
        if not url:
            logger.warning("Slack notification skipped: No Webhook URL configured.")
            return

        try:
            payload = {"text": message}
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code != 200:
                logger.error(f"Slack API returned {response.status_code}")
            else:
                logger.info("Slack notification sent")
        except Exception as e:
            logger.error(f"Failed to send slack notification: {e}")

    async def alert_incident(self, incident: Incident):
        """
        Send alerts based on incident severity and tenant configuration.
        """
        if incident.severity not in ["critical", "high"]:
            return

        # Fetch Tenant Configuration
        # Note: This requires an async session. In a real service, we might inject the session 
        # or use a scoped session. For now, we'll use a context manager if possible or pass DB.
        # Since this is called from an async endpoint where DB is available, we should pass DB.
        # Refactoring to accept DB session or fetch it.
        # For simplicity in this architecture, we'll assume the caller passes the config or we fetch it here.
        # Fetching here creates a new session which is safer.
        
        async for session in get_db():
            result = await session.execute(select(Tenant).filter(Tenant.id == incident.tenant_id))
            tenant = result.scalars().first()
            break # Only need one session
            
        if not tenant:
            logger.warning(f"Tenant {incident.tenant_id} not found for alert.")
            return

        config = tenant.notification_config or {}
        slack_webhook = config.get("slack_webhook")
        email_recipients = config.get("email_recipients", [])

        subject = f"[{incident.severity.upper()}] Veridian Incident Alert: {incident.classification}"
        body = f"""
        🚨 Veridian Security Alert 🚨
        
        Incident ID: {incident.id}
        Severity: {incident.severity}
        Classification: {incident.classification}
        Agent ID: {incident.agent_id}
        
        --- Transcript / Details ---
        {incident.transcript_ref}
        
        Please investigate immediately.
        """
        
        # Send to configured emails
        for email in email_recipients:
            await self.send_email(email, subject, body)
        
        # Send to configured Slack
        if slack_webhook:
            slack_msg = f"🚨 *{subject}*\n> {incident.transcript_ref}"
            await self.send_slack(slack_msg, webhook_url=slack_webhook)

notification_service = NotificationService()
