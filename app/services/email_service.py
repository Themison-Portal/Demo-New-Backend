import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self._settings = None
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    @property
    def settings(self):
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    async def send_invitation_email(self, email: str, name: str, token: str, org_name: str):
        """
        Send an invitation email via SendGrid.
        Fallbacks to logging if SENDGRID_API_KEY is not set.
        """
        signup_link = f"{self.settings.frontend_url}/signup?token={token}"
        
        # Log for local development / verification
        logger.info(f"Preparing invitation for {email}: {signup_link}")

        if not self.settings.sendgrid_api_key:
            logger.warning("SENDGRID_API_KEY not set. Email will NOT be sent (logged only).")
            return True

        message = (
            f"Hello {name},\n\n"
            f"You have been invited to join {org_name} on the Themison Portal.\n"
            f"Click the link below to complete your setup and create your account:\n\n"
            f"{signup_link}\n\n"
            "If you did not expect this invitation, please ignore this email."
        )

        html_content = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee;">
            <h2 style="color: #2D3748;">You've been invited!</h2>
            <p>Hello <strong>{name}</strong>,</p>
            <p>You have been invited to join <strong>{org_name}</strong> on the Themison Portal.</p>
            <div style="margin: 30px 0;">
                <a href="{signup_link}" style="background-color: #4A90E2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Complete Signup</a>
            </div>
            <p style="color: #718096; font-size: 0.875rem;">Or copy and paste this link: <br/>{signup_link}</p>
            <hr style="margin: 30px 0; border: 0; border-top: 1px solid #eee;" />
            <p style="color: #A0AEC0; font-size: 0.75rem;">If you did not expect this invitation, please ignore this email.</p>
        </div>
        """

        payload = {
            "personalizations": [{"to": [{"email": email}]}],
            "from": {
                "email": self.settings.email_from or "noreply@themison.app",
                "name": "Themison Portal"
            },
            "subject": f"Invitation to join {org_name}",
            "content": [
                {"type": "text/plain", "value": message},
                {"type": "text/html", "value": html_content}
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.settings.sendgrid_api_key}",
            "Content-Type": "application/json"
        }

        try:
            resp = await self.client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers
            )
            
            if resp.status_code >= 400:
                logger.error(f"SendGrid Error {resp.status_code}: {resp.text}")
                return False
                
            logger.info(f"Successfully sent invitation email to {email} (Status: {resp.status_code})")
            return True
        except Exception as e:
            logger.error(f"Unexpected error sending email via SendGrid: {e}")
            return False

# Global instance
email_service = EmailService()
