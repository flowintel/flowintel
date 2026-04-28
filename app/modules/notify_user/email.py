import conf.config_module as Config
import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
import datetime


module_config = {
    "case_task": "task"
}

ARCHIVE_FOLDER = "logs/email_archive.log"


def send_email_notification(recipient_email, subject, body):
    """Send notification email via SMTP"""
    message = MIMEMultipart()
    message['From'] = Config.SENDER_EMAIL
    message['To'] = recipient_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
    server.starttls()
    server.login(Config.SENDER_EMAIL, Config.SENDER_PASSOWRD)
    server.sendmail(Config.SENDER_EMAIL, recipient_email, message.as_string())
    server.quit()

    _archive_email(recipient_email, subject, body, sent=True)


def handler(task, case, current_user, user):
    """
    task: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
           completed, deadline, finish_date, tags, clusters, connectors

    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id
    """
    if not Config.SENDER_EMAIL or not Config.SENDER_PASSOWRD:
        return

    recipient_email = user.email
    subject = f"[Flowintel] Task notification - {task.get('title', '')}"
    body = (
        f"{current_user.first_name} {current_user.last_name} notifies you on task "
        f"'{task.get('title', '')}' for case '{case.get('title', '')}'\n"
        f"(http://{Config.ORIGIN_URL}/case/{task.get('case_id', '')})"
    )

    try:
        send_email_notification(recipient_email, subject, body)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Email error: {e}")
        _archive_email(recipient_email, subject, body, sent=False, error=str(e))


def _archive_email(recipient, subject, body, sent=True, error=None):
    """Archive sent/received emails to a log file"""
    try:
        with open(ARCHIVE_FOLDER, "a") as f:
            ts = datetime.datetime.now().isoformat()
            status = "SENT" if sent else f"FAILED ({error})"
            f.write(f"[{ts}] {status} | To: {recipient} | Subject: {subject}\n")
    except Exception:
        pass


def fetch_imap_archive():
    """Fetch emails from IMAP for archive viewing"""
    if not Config.IMAP_SERVER or not Config.IMAP_USER or not Config.IMAP_PASSWORD:
        return []

    messages = []
    try:
        mail = imaplib.IMAP4_SSL(Config.IMAP_SERVER, Config.IMAP_PORT)
        mail.login(Config.IMAP_USER, Config.IMAP_PASSWORD)
        mail.select("INBOX")

        status, data = mail.search(None, "FROM", Config.SENDER_EMAIL)
        if status == "OK":
            for num in data[0].split()[-20:]:  # Last 20 emails
                status, msg_data = mail.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        raw = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(raw["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")
                        messages.append({
                            "subject": subject,
                            "from": raw["From"],
                            "date": raw["Date"],
                        })
        mail.logout()
    except Exception as e:
        print(f"IMAP error: {e}")

    return messages


def test_imap():
    """Test IMAP connection"""
    if not Config.IMAP_SERVER:
        return {"status": "error", "message": "IMAP not configured"}
    try:
        mail = imaplib.IMAP4_SSL(Config.IMAP_SERVER, Config.IMAP_PORT)
        mail.login(Config.IMAP_USER, Config.IMAP_PASSWORD)
        mail.logout()
        return {"status": "ok", "message": "IMAP connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def introspection():
    return module_config