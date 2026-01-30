"""
Email service - supports Brevo (API key, no app password) or SMTP.
Brevo: 300 free emails/day, sign up at brevo.com - easiest option.
SMTP: Gmail, Outlook, etc. (Gmail requires App Password - not available for all accounts).
"""
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List


def _build_html_body(body: str, interest_form_link: str = None) -> str:
    html = body.replace("\n", "<br>")
    if interest_form_link:
        html += f'<br><br><p>Interest form: <a href="{interest_form_link}">{interest_form_link}</a></p>'
    return html


def send_email_brevo(
    to_emails: List[str],
    subject: str,
    body: str,
    interest_form_link: str = None,
) -> dict:
    """
    Send via Brevo (Sendinblue) - 300 free emails/day, API key only, no app password.
    Sign up at https://www.brevo.com (free), get API key from SMTP & API > API Keys.
    
    IMPORTANT: Verify your sender in Brevo dashboard: Senders & IPs > Add sender > verify with code.
    
    Env: BREVO_API_KEY, BREVO_FROM_EMAIL (your verified sender email)
    """
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("BREVO_FROM_EMAIL") or os.getenv("SMTP_USER")
    
    if not api_key:
        raise ValueError("BREVO_API_KEY not set. Sign up at brevo.com (free), get API key.")
    if not from_email:
        raise ValueError("BREVO_FROM_EMAIL or SMTP_USER required (your sender email)")
    
    html_body = _build_html_body(body, interest_form_link)
    
    to_list = [e.strip() for e in to_emails if e and "@" in str(e)]
    if not to_list:
        return {"success": False, "sent": 0, "failed": ["No valid emails"]}
    
    payload = {
        "sender": {"email": from_email, "name": os.getenv("BREVO_FROM_NAME", "Content Platform")},
        "to": [{"email": e} for e in to_list],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": body,  # Plain text fallback - improves deliverability
    }
    
    print(f"📧 Sending email via Brevo: from={from_email}, to={to_list[:3]}{'...' if len(to_list) > 3 else ''}")
    
    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    
    resp = r.json() if r.text else {}
    
    if r.status_code in (200, 201):
        msg_id = resp.get("messageId", "ok")
        print(f"✅ Brevo accepted: messageId={msg_id}")
        return {"success": True, "sent": len(to_list), "failed": [], "messageId": msg_id}
    
    msg = resp.get("message", resp.get("code", r.text or str(r.status_code)))
    print(f"❌ Brevo error {r.status_code}: {msg}")
    raise Exception(f"Brevo API error: {msg}")


def send_email_smtp(
    to_emails: List[str],
    subject: str,
    body: str,
    interest_form_link: str = None,
) -> dict:
    """
    Send via SMTP (Gmail, Outlook, etc). Gmail needs App Password (not available for all accounts).
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or user
    
    if not all([host, user, password]):
        raise ValueError(
            "SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD. "
            "Or use Brevo instead: BREVO_API_KEY + BREVO_FROM_EMAIL (no app password needed)"
        )
    
    html_body = _build_html_body(body, interest_form_link)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    
    sent_count = 0
    failed = []
    for to_email in to_emails:
        to_email = (to_email or "").strip()
        if not to_email or "@" not in to_email:
            failed.append(to_email or "(empty)")
            continue
        try:
            msg["To"] = to_email
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(from_email, [to_email], msg.as_string())
            sent_count += 1
        except Exception as e:
            failed.append(f"{to_email}: {str(e)}")
    
    return {"success": sent_count > 0, "sent": sent_count, "failed": failed}


def send_email(
    to_emails: List[str],
    subject: str,
    body: str,
    interest_form_link: str = None,
) -> dict:
    """
    Send emails. Uses Brevo if BREVO_API_KEY is set (easiest - no app password).
    Otherwise uses SMTP.
    """
    if os.getenv("BREVO_API_KEY"):
        return send_email_brevo(to_emails, subject, body, interest_form_link)
    return send_email_smtp(to_emails, subject, body, interest_form_link)
