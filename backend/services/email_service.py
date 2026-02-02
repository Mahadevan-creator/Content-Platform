"""
Email service - SMTP only.
Supports Microsoft 365 (@hackerrank.com), Gmail, Outlook, etc.
M365: smtp.office365.com:587. Gmail: smtp.gmail.com:587 (App Password required).
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

logger = logging.getLogger(__name__)


# HackerRank signature assets (match reference email from Siddhant)
HACKERRANK_ICON_URL = "https://lh4.googleusercontent.com/5jAVk7vZk3Xr3rori3CfbCgm8IdGVtxGjfRQg9cBfzFZMlxF7tolezNL--q1VQY79unOdKcQf-YQR3dWESz0Cus8-IrvAGDKhF_T8NkWQf5kaQ-MMO8xnfMcltDkyC9v7XDuJTxo"
HACKERRANK_GREEN = "rgb(27, 169, 76)"


def _build_html_body(
    body: str,
    interest_form_link: str = None,
    sender_name: str = "",
) -> str:
    html = body.replace("\n", "<br>")
    # Insert Google form link before "Best," (so it appears where "the link below" is referenced)
    if interest_form_link:
        link_block = f'<br><br><p><a href="{interest_form_link}" style="color:{HACKERRANK_GREEN};font-weight:600;text-decoration:underline">{interest_form_link}</a></p><br>'
        best_idx = html.rfind("Best,")
        if best_idx >= 0:
            html = html[:best_idx] + link_block + html[best_idx:]
        else:
            html += link_block
    # Replace plain signature with styled block (gray name, icon, green HackerRank)
    best_idx = html.rfind("Best,")
    if best_idx >= 0:
        sig_block = (
            f'Best,<br><br>'
            f'<p style="margin:0;font-size:9pt;line-height:1.38;font-family:Verdana">'
            f'<font color="#999999">{sender_name}</font>'
            f'<img width="7" height="11" src="{HACKERRANK_ICON_URL}" alt="" style="vertical-align:middle;margin-left:2px" />'
            f'</p>'
            f'<p style="margin:4px 0 0 0;font-size:8pt;line-height:1.2;font-family:Verdana;font-weight:700;color:{HACKERRANK_GREEN}">'
            f'HackerRank</p>'
        )
        html = html[:best_idx] + sig_block
    return html


def send_email(
    to_emails: List[str],
    subject: str,
    body: str,
    interest_form_link: str = None,
    sender_name: str = "",
) -> dict:
    """
    Send emails via SMTP.
    Env: SMTP_HOST, SMTP_USER, SMTP_PASSWORD.
    For @hackerrank.com (M365): SMTP_HOST=smtp.office365.com, SMTP_PORT=587.
    MFA: use App Password from Microsoft account security settings.
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS")
    from_email = os.getenv("SMTP_FROM_EMAIL") or user

    if not all([host, user, password]):
        raise ValueError(
            "SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD. "
            "For @hackerrank.com: SMTP_HOST=smtp.office365.com SMTP_PORT=587 SMTP_USER=you@hackerrank.com"
        )

    logger.info(
        "[Email] Sending to %d recipient(s) via %s:%s (user=%s)",
        len([e for e in to_emails if e and "@" in str(e)]),
        host,
        port,
        user,
    )

    html_body = _build_html_body(body, interest_form_link, sender_name)
    to_list = [e.strip() for e in to_emails if e and "@" in str(e)]
    if not to_list:
        logger.warning("[Email] No valid recipient emails")
        return {"success": False, "sent": 0, "sent_emails": [], "failed": ["No valid emails"]}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    sent_count = 0
    sent_emails = []
    failed = []
    try:
        with smtplib.SMTP(host, port) as server:
            logger.debug("[Email] Connected to %s:%s, starting TLS", host, port)
            server.starttls()
            try:
                server.login(user, password)
            except smtplib.SMTPAuthenticationError as auth_err:
                err_str = str(auth_err)
                logger.error(
                    "[Email] SMTP auth failed (host=%s, user=%s): %s",
                    host,
                    user,
                    err_str,
                )
                if "535" in err_str or "BadCredentials" in err_str or "Username and Password not accepted" in err_str:
                    logger.error(
                        "[Email] TIP: Gmail/M365 require an App Password, not your regular password. "
                        "Gmail: Google Account → Security → 2-Step Verification → App passwords. "
                        "M365: Microsoft account → Security → Advanced security → App passwords."
                    )
                raise
            for to_email in to_list:
                try:
                    msg["To"] = to_email
                    server.sendmail(from_email, [to_email], msg.as_string())
                    sent_count += 1
                    sent_emails.append(to_email)
                    logger.info("[Email] Sent to %s", to_email)
                except Exception as e:
                    failed.append(f"{to_email}: {str(e)}")
                    logger.warning("[Email] Failed to send to %s: %s", to_email, e)
    except smtplib.SMTPAuthenticationError:
        raise
    except Exception as e:
        logger.exception("[Email] SMTP error: %s", e)
        return {"success": False, "sent": 0, "sent_emails": [], "failed": [str(e)]}

    logger.info("[Email] Done: sent=%d, failed=%d", sent_count, len(failed))
    return {"success": sent_count > 0, "sent": sent_count, "sent_emails": sent_emails, "failed": failed}
