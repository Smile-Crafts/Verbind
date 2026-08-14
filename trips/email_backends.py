"""
A Django email backend that sends through Resend's HTTPS API instead of
SMTP. Exists because Railway (and several other hosts) block outbound SMTP
entirely on free/trial/hobby plans — see Railway's own docs on outbound
networking. HTTPS traffic isn't blocked, so this sidesteps the wall
completely rather than fighting it.

No new pip package needed — this uses Python's built-in urllib, the same
approach already used for the OpenStreetMap address search, to keep the
dependency footprint small.
"""
import json
import urllib.request
import urllib.error

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        api_key = getattr(settings, 'RESEND_API_KEY', '')
        if not api_key:
            if not self.fail_silently:
                raise ValueError(
                    "RESEND_API_KEY is not set — cannot send email via Resend."
                )
            return 0

        sent_count = 0
        for message in email_messages:
            payload = {
                'from': message.from_email,
                'to': list(message.to),
                'subject': message.subject,
                'text': message.body,
            }
            if message.cc:
                payload['cc'] = list(message.cc)
            if message.bcc:
                payload['bcc'] = list(message.bcc)

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                'https://api.resend.com/emails',
                data=data,
                method='POST',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Verbind/1.0 (Django email backend)',
                },
            ) 
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    resp.read()
                sent_count += 1
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')
                if not self.fail_silently:
                    raise RuntimeError(f"Resend API error {e.code}: {body}") from e
            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count
