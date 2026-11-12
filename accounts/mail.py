import logging
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


class ReadableConsoleEmailBackend(ConsoleEmailBackend):
    """Print the message body without quoted-printable line breaks."""

    def write_message(self, message):
        self.stream.write("\n----- Email -----\n")
        self.stream.write(f"From: {message.from_email}\n")
        self.stream.write(f"To: {', '.join(message.to)}\n")
        self.stream.write(f"Subject: {message.subject}\n\n")
        self.stream.write(message.body)
        if not message.body.endswith("\n"):
            self.stream.write("\n")
        self.stream.write("----- End -----\n")
        self.stream.flush()


def send_account_email(*, subject, recipient, text, html):
    message = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html, "text/html")
    try:
        accepted = message.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Account email could not be sent to %s", recipient)
        raise EmailDeliveryError("The email service could not send this message.") from exc
    if accepted != 1:
        raise EmailDeliveryError("The email service did not accept this message.")


def verification_message(url):
    safe_url = escape(url, quote=True)
    text = (
        "Confirm this address to activate your PrepLoop account.\n\n"
        f"{url}\n\n"
        "This link expires in one hour. If you did not create an account, ignore this email.\n"
    )
    html = (
        "<p>Confirm this address to activate your PrepLoop account.</p>"
        f'<p><a href="{safe_url}">{safe_url}</a></p>'
        "<p>This link expires in one hour. If you did not create an account, ignore this email.</p>"
    )
    return text, html


def recovery_message(url):
    safe_url = escape(url, quote=True)
    text = (
        "Use this link to choose a new PrepLoop password.\n\n"
        f"{url}\n\n"
        "This link expires in one hour. If you did not ask for a reset, ignore this email.\n"
    )
    html = (
        "<p>Use this link to choose a new PrepLoop password.</p>"
        f'<p><a href="{safe_url}">{safe_url}</a></p>'
        "<p>This link expires in one hour. If you did not ask for a reset, ignore this email.</p>"
    )
    return text, html
