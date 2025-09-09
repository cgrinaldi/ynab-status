import base64
import os
import smtplib
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError as GoogleRefreshError

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _get_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except GoogleRefreshError as e:
                raise RuntimeError(
                    "Gmail OAuth refresh failed (token expired or revoked). "
                    "Fix: Regenerate token.json locally by deleting it and running "
                    "`uv run -m app.main` to complete the browser consent. Then update "
                    "your CI secret GMAIL_TOKEN_JSON with the new file contents."
                ) from e
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(
    sender: str,
    to_list: list[str],
    subject: str,
    text: str,
    html: str | None = None,
    bcc: list[str] | None = None,
):
    """Send email via either Gmail API (OAuth) or SMTP with App Password.

    If the environment contains GMAIL_APP_PASSWORD, SMTP is used against
    smtp.gmail.com. Otherwise, the Gmail API OAuth flow is used.
    """
    msg = EmailMessage()
    msg["From"] = sender
    if to_list:
        msg["To"] = ", ".join(to_list)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if app_password:
        # Prefer SSL on 465. STARTTLS on 587 also works; SSL is simpler here.
        rcpts = list(to_list or []) + list(bcc or [])
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, app_password)
            smtp.sendmail(sender, rcpts or [sender], msg.as_string())
        return {"transport": "smtp", "status": "sent"}
    # Default to Gmail API OAuth
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    svc = _get_service()
    return svc.users().messages().send(userId="me", body={"raw": raw}).execute()
