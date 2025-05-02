import datetime as dt
from abc import ABC, abstractmethod


class EmailTemplate(ABC):
	@abstractmethod
	def getSubject(self, **kwargs):
		pass

	@abstractmethod
	def getBody(self, **kwargs):
		pass

	@abstractmethod
	def getPlainText(self, **kwargs):
		pass


class Templates:
	class PasswordResetEmail(EmailTemplate):
		def getSubject(self, **kwargs):
			return f"Password Reset for {kwargs['username']}"

		def getBody(self, **kwargs):
			return f"<h1>Password Reset</h1><p>Click <a href='{kwargs['url']}'>here</a> to reset your password</p>"

		def getPlainText(self, **kwargs):
			return f"Password Reset\n\nClick here to reset your password: {kwargs['url']}"

	class WelcomeEmail(EmailTemplate):
		def getSubject(self, **kwargs):
			return f"Welcome to eBuy, {kwargs['username']}!"

		def getBody(self):
			return "<h1>Welcome to eBuy!</h1><p>Thank you for joining our platform!</p>"

		def getPlainText(self):
			return "Welcome to eBuy!\n\nThank you for joining our platform!"

	class OrderUpdateEmail(EmailTemplate):
		def getSubject(self, **kwargs):
			return f"Order Update: {kwargs['id']}"

		def getBody(self, **kwargs):
			return (f"<h1>Order Update</h1><br /><p>Your order placed on {dt.datetime.fromtimestamp(kwargs['addedAt']).strftime('%A %B %d')}, sold by "
					f"{kwargs['seller'].username}, is now <strong>{kwargs['status'].value}</strong></p><br />"
					f"Your order consists of:<br /><ul>"
					f"{', '.join([f'<li>{item.quantity}x {item.listing.title}</li>' for item in kwargs['skus']])}")

		def getPlainText(self, **kwargs):
			return f"Order Update\n\nYour order {kwargs['id']} has been updated to {kwargs['status'].lower()}"
