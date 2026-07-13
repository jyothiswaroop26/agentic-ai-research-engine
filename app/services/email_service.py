from __future__ import annotations


class EmailService:
	"""Simple email sender abstraction used by the workflow email node."""

	def send_report(self, recipient: str, subject: str, body: str) -> None:
		if not recipient or "@" not in recipient:
			raise ValueError("A valid recipient email address is required.")
		if not subject.strip():
			raise ValueError("Email subject must not be empty.")
		if not body.strip():
			raise ValueError("Email body must not be empty.")

		# This project currently exposes an interface-only sender. Integrate a concrete
		# provider (SMTP, SendGrid, SES, etc.) here when needed.
		return None
