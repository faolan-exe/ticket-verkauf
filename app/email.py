import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.strato.de"
_SMTP_PORT = 465
_FROM = "kontakt@t-auer.com"

_PASSWORD_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "email_password.txt")


def _password() -> str:
    with open(_PASSWORD_FILE) as f:
        return f.read().strip()


def send_confirmation(
    to_email: str,
    registrant_name: str,
    reg_id: int,
    total_tickets: int,
    total_price: int,
    settings: dict,
) -> None:
    reference = f"{settings.get('bank_reference', 'Abiball Ticket')} #{reg_id}"

    lines = [
        f"Hallo {registrant_name},",
        "",
        "deine Anmeldung für den Abiball 2026 wurde erfolgreich gespeichert.",
        "",
        "────────────────────────────────",
        f"Anmeldungs-Nr.: #{reg_id}",
        f"Anzahl Tickets:  {total_tickets}",
        f"Gesamtbetrag:    {total_price} €",
        "────────────────────────────────",
        "",
        "Bitte überweise den Betrag zeitnah, damit deine Anmeldung bestätigt wird.",
        "",
    ]

    if settings.get("paypal_email"):
        lines += [
            "Zahlung per PayPal (Freunde & Familie):",
        ]
        if settings.get("paypal_name"):
            lines.append(f"  Name:             {settings['paypal_name']}")
        lines += [
            f"  E-Mail:           {settings['paypal_email']}",
            f"  Verwendungszweck: {reference}",
            "",
        ]

    if settings.get("bank_iban"):
        lines += [
            "Zahlung per Banküberweisung:",
        ]
        if settings.get("bank_owner"):
            lines.append(f"  Kontoinhaber:     {settings['bank_owner']}")
        lines += [
            f"  IBAN:             {settings['bank_iban']}",
            f"  Verwendungszweck: {reference}",
            "",
        ]

    lines += [
        "Die Tischnummer ist ein Wunsch und wird nicht garantiert.",
        "Die Anmeldung gilt erst nach Zahlungseingang als bestätigt.",
        "",
        "Viele Grüße,",
        "Das Abiball-Team",
    ]

    msg = MIMEText("\n".join(lines), "plain", "utf-8")
    msg["Subject"] = f"Anmeldungsbestätigung Abiball 2026 – #{reg_id}"
    msg["From"] = _FROM
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as smtp:
            smtp.login(_FROM, _password())
            smtp.sendmail(_FROM, to_email, msg.as_string())
    except Exception:
        logger.exception("Bestätigungsmail an %s konnte nicht gesendet werden", to_email)
