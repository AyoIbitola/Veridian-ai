import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.db.models import Incident

logger = logging.getLogger("Notifications")

class NotificationService:
    def __init__(self):
        self.email_enabled = bool(settings.SMTP_SERVER and settings.SMTP_USER)
        self.slack_enabled = bool(settings.SLACK_WEBHOOK_URL)

    async def send_email(self, to: str, subject: str, body: str):
        if not self.email_enabled:
            logger.warning("Email notification skipped: SMTP settings not configured.")
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

    async def send_slack(self, message: str):
        if not self.slack_enabled:
            logger.warning("Slack notification skipped: Webhook URL not configured.")
            return

        try:
            payload = {"text": message}
            response = requests.post(settings.SLACK_WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code != 200:
                logger.error(f"Slack API returned {response.status_code}")
            else:
                logger.info("Slack notification sent")
        except Exception as e:
            logger.error(f"Failed to send slack notification: {e}")

    async def alert_incident(self, incident: Incident):
        """
        Send alerts based on incident severity.
        """
        if incident.severity in ["critical", "high"]:
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
            
            # Send to Admin (Hardcoded for now, could be tenant owner email)
            # In real app: user = await db.get(User, incident.tenant.owner_id)
            admin_email = "admin@example.com" 
            
            await self.send_email(admin_email, subject, body)
            
            slack_msg = f"🚨 *{subject}*\n> {incident.transcript_ref}"
            await self.send_slack(slack_msg)

notification_service = NotificationService()
