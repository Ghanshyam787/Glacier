"""
Glacier Tools: Communication
WhatsApp (desktop app), email (Gmail/IMAP/SMTP), Telegram (phone ko message/file).
Koi bhi message BHEJNE wala tool confirmation maangta hai - Glacier tumhari taraf se kabhi chupke se message nahi bhejta.
"""

import email
import imaplib
import os
import re
import smtplib
import ssl
import time
import webbrowser
from email.header import decode_header, make_header
from email.message import EmailMessage
from urllib.parse import quote

import config
import netsafe
import safety
from registry import tool
from tools.productivity import lookup_contact

DEFAULT_COUNTRY_CODE = os.environ.get("DEFAULT_COUNTRY_CODE", "91")


# ============================================================ WhatsApp
def _resolve_phone(who: str):
    """(digits, display_name) ya (None, error)."""
    w = (who or "").strip()
    digits = re.sub(r"[^\d+]", "", w)
    if re.fullmatch(r"\+?\d{8,15}", digits):
        d = digits.lstrip("+")
        if len(d) == 10:
            d = DEFAULT_COUNTRY_CODE + d
        return d, w
    c = lookup_contact(w)
    if c and c["phone"]:
        d = re.sub(r"[^\d]", "", c["phone"])
        if len(d) == 10:
            d = DEFAULT_COUNTRY_CODE + d
        return d, c["name"]
    return None, f"'{who}' ka phone number nahi mila. Number batao ya add_contact se save karo."


@tool(category="comms", dangerous=True, label="WhatsApp message")
def send_whatsapp(to: str, message: str, confirmed: bool = False) -> str:
    """
    Send a WhatsApp message through the WhatsApp desktop app. 'to' = phone number (10-digit Indian numbers get +91)
    or a saved contact name. Needs confirmation: confirmed=False first, then confirmed=True (same arguments) after
    the user says yes.
    """
    phone, name = _resolve_phone(to)
    if not phone:
        return name
    if not message.strip():
        return "Message khaali hai."
    gate = safety.confirm_gate("send_whatsapp", {"phone": phone, "message": message}, confirmed,
                               f"WhatsApp par {name} (+{phone}) ko ye bhejun?\n\"{message[:300]}\"")
    if gate:
        return gate
    uri = f"whatsapp://send?phone={phone}&text={quote(message)}"
    try:
        os.startfile(uri)  # type: ignore[attr-defined]
    except Exception:
        webbrowser.open(f"https://wa.me/{phone}?text={quote(message)}")
        return (f"WhatsApp desktop app nahi mila, browser mein chat khol di ({name}). Message likha hua hai - "
                "bas Send dabana baaki hai (WhatsApp Web login chahiye).")
    time.sleep(4.5)  # app / chat load hone do
    try:
        import pyautogui
        pyautogui.press("enter")
        return (f"{name} ke liye message bhej diya (Enter daba diya). Pakka karna ho to bolo, "
                "main screen dekh ke confirm kar dunga.")
    except Exception:
        return f"WhatsApp mein {name} ki chat message ke saath khul gayi hai, par Enter nahi daba paya - Send tum dabao."


# ============================================================ Email
def _imap():
    if not (config.EMAIL_ADDRESS and config.EMAIL_APP_PASSWORD):
        raise RuntimeError("Email set nahi hai. .env mein EMAIL_ADDRESS aur EMAIL_APP_PASSWORD daalo "
                           "(Gmail: Google Account > Security > 2-Step > App passwords).")
    m = imaplib.IMAP4_SSL(config.IMAP_HOST, timeout=20)
    m.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
    return m


def _hdr(msg, name: str) -> str:
    try:
        return str(make_header(decode_header(msg.get(name, ""))))
    except Exception:
        return msg.get(name, "") or ""


def _body(msg) -> str:
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if part.get_content_disposition() == "attachment":
                continue
            if ctype == "text/plain":
                text = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                break
            if ctype == "text/html" and not text:
                html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                text = netsafe.html_to_text(html, 8000)
    else:
        payload = msg.get_payload(decode=True) or b""
        text = payload.decode(msg.get_content_charset() or "utf-8", "replace")
        if msg.get_content_type() == "text/html":
            text = netsafe.html_to_text(text, 8000)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _list(m, criteria: str, count: int) -> str:
    m.select("INBOX", readonly=True)
    typ, data = m.search(None, criteria)
    ids = (data[0].split() if typ == "OK" and data and data[0] else [])[-count:][::-1]
    if not ids:
        return "Koi email nahi mila."
    lines = []
    for i in ids:
        typ, d = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        msg = email.message_from_bytes(d[0][1])
        lines.append(f"#{i.decode()} | {_hdr(msg, 'From')[:50]} | {_hdr(msg, 'Subject')[:80]} | {_hdr(msg, 'Date')[:22]}")
    return "\n".join(lines)


@tool(category="comms", untrusted="email", label="Unread emails")
def email_unread(count: int = 5) -> str:
    """List the latest unread emails (sender, subject, date). Each has a #number for email_read."""
    try:
        m = _imap()
        try:
            return _list(m, "UNSEEN", max(1, min(int(count or 5), 15)))
        finally:
            m.logout()
    except Exception as e:
        return f"Email check nahi hua: {str(e)[:200]}"


@tool(category="comms", untrusted="email", label="Search emails")
def email_search(query: str, count: int = 5) -> str:
    """Search the inbox by sender/subject/text and list matches."""
    q = query.replace('"', "")
    try:
        m = _imap()
        try:
            return _list(m, f'(OR OR FROM "{q}" SUBJECT "{q}" TEXT "{q}")', max(1, min(int(count or 5), 15)))
        finally:
            m.logout()
    except Exception as e:
        return f"Email search nahi hui: {str(e)[:200]}"


@tool(category="comms", untrusted="email", label="Read email")
def email_read(number: str) -> str:
    """Read one email's text by its #number from email_unread / email_search."""
    num = str(number).strip().lstrip("#")
    if not num.isdigit():
        return "Email ka number batao."
    try:
        m = _imap()
        try:
            m.select("INBOX", readonly=True)
            typ, d = m.fetch(num.encode(), "(BODY.PEEK[])")
            if typ != "OK" or not d or not d[0]:
                return "Is number ka email nahi mila."
            msg = email.message_from_bytes(d[0][1])
            return (f"From: {_hdr(msg, 'From')}\nSubject: {_hdr(msg, 'Subject')}\nDate: {_hdr(msg, 'Date')}\n\n"
                    f"{_body(msg)[:5000]}")
        finally:
            m.logout()
    except Exception as e:
        return f"Email padh nahi paya: {str(e)[:200]}"


def _resolve_email(who: str):
    w = (who or "").strip()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", w):
        return w, w
    c = lookup_contact(w)
    if c and c["email"]:
        return c["email"], c["name"]
    return None, f"'{who}' ka email address nahi mila."


@tool(category="comms", dangerous=True, label="Send email")
def send_email(to: str, subject: str, body: str, confirmed: bool = False) -> str:
    """
    Send an email from the user's own account. 'to' = address or saved contact name. Needs confirmation:
    confirmed=False first, then confirmed=True (same arguments) after the user says yes.
    """
    addr, name = _resolve_email(to)
    if not addr:
        return name
    if not (config.EMAIL_ADDRESS and config.EMAIL_APP_PASSWORD):
        return "Email set nahi hai. .env mein EMAIL_ADDRESS aur EMAIL_APP_PASSWORD daalo."
    gate = safety.confirm_gate("send_email", {"to": addr, "subject": subject, "body": body}, confirmed,
                               f"{name} <{addr}> ko ye email bhejun?\nSubject: {subject}\n\n{body[:500]}")
    if gate:
        return gate
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.EMAIL_ADDRESS, addr, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=ssl.create_default_context(), timeout=25) as s:
            s.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            s.send_message(msg)
        return f"Email bhej diya: {addr}"
    except Exception as e:
        return f"Email nahi gaya: {str(e)[:200]}"


# ============================================================ Telegram (phone)
@tool(category="comms", label="Message my phone")
def send_telegram_message(text: str) -> str:
    """Send a text message to the user's own phone via the Glacier Telegram bot (set up with TELEGRAM_BOT_TOKEN)."""
    from channels import telegram_bot
    return telegram_bot.send_text(text)


@tool(category="comms", dangerous=True, label="Send file to phone")
def send_file_to_phone(path: str, confirmed: bool = False) -> str:
    """
    Send a file from this PC to the user's phone via the Glacier Telegram bot (max 50 MB). Needs confirmation:
    confirmed=False first, then confirmed=True (same path) after the user says yes.
    """
    p = os.path.abspath(os.path.expanduser(path.strip().strip('"')))
    if not safety.is_allowed_path(p) or not os.path.isfile(p):
        return safety.PATH_DENIED_MSG if os.path.exists(p) else f"File nahi mili: {p}"
    gate = safety.confirm_gate("send_file_to_phone", {"path": p}, confirmed, f"Ye file tumhare phone (Telegram) par bhejun?\n{p}")
    if gate:
        return gate
    from channels import telegram_bot
    return telegram_bot.send_file(p)
