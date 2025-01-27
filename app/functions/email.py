import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.models.emails import EmailTemplate


class EmailService:
	"""
	A class to send emails
	"""
	def __init__(self, senderAddress: str, senderPassword: str, senderHost: str, senderPort: int):
		self.senderHost = senderHost
		self.senderPort = senderPort
		self.senderAddress = senderAddress
		self.senderPassword = senderPassword

	def sendEmail(self, recipientAddress: str, subject: str, body: str, plainText: str) -> None:
		"""
		Send an email
		:param recipientAddress: The recipient's email address
		:param subject: The subject of the email
		:param body: The body of the email in HTML
		:param plainText: The plain text version of the email
		:return:
		"""
		message = MIMEMultipart("alternative")
		message["Subject"] = subject
		message["From"] = self.senderAddress
		message["To"] = recipientAddress

		part1 = MIMEText(plainText, "plain")
		message.attach(part1)
		part2 = MIMEText(body, "html")
		message.attach(part2)

		context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
		context.options = ssl.OP_NO_TLSv1_1

		with smtplib.SMTP(self.senderHost, self.senderPort) as server:
			server.starttls(context=context)
			server.ehlo()

			server.login(self.senderAddress, self.senderPassword)
			server.sendmail(self.senderAddress, recipientAddress, message.as_string())
			server.quit()

	def sendEmailTemplate(self, template: EmailTemplate, recipientAddress: str, **templateKwargs):
		"""
		Send an email using a template
		:param template: The template to use
		:param recipientAddress: The recipient's email address
		:param templateKwargs: The template's arguments
		:return:
		"""
		self.sendEmail(recipientAddress,
					   template.getSubject(**templateKwargs),
					   template.getBody(**templateKwargs),
					   template.getPlainText(**templateKwargs))


