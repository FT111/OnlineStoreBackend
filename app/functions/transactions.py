import time
from abc import ABC, abstractmethod

from fastapi import HTTPException
from typing_extensions import Union

from app.models.transactions import CardPaymentDetails


class PaymentMethods:
	class PaymentStrategy(ABC):
		@abstractmethod
		def __init__(self):
			pass

		@abstractmethod
		def pay(self, value: int, recipient: Union[str, int]) -> Union[bool, HTTPException]:
			pass

	class MockCardPayment(PaymentStrategy):
		def __init__(self, details: CardPaymentDetails):
			self.details = details

		def pay(self, value: int, recipient):
			# Mock payment method

			# Code here would realistically interact with a payment processor

			time.sleep(1)
			return True

	# Dictionary of payment methods and their implementations
	paymentStrategies = {
		'card': MockCardPayment
	}


class PaymentHandler:
	"""
	Unified interface for payment methods

	Set a payment method strategy to use
	"""
	def __init__(self, paymentMethod: PaymentMethods.PaymentStrategy):
		self.paymentMethod = paymentMethod

	def makePayment(self, value: int, recipientIdentifier: Union[str, int, dict]) -> Union[bool, HTTPException]:
		"""
		Make a payment using the selected payment method
		:param value: Value of the payment in pence (GBP)
		:param recipientIdentifier: The recipient's identifier for the method
		:return:m True if the payment was successful, exception otherwise
		"""
		return self.paymentMethod.pay(value, recipientIdentifier)


def paymentHandlerFactory(paymentDetails: Union[
	CardPaymentDetails
]) -> PaymentHandler:
	"""
	Factory function to create a payment handler
	Used to determine the payment method from the user input
	Add new payment methods to the union
	Works as a dependency for FastAPI endpoints
	:param paymentDetails: The payment details from the user, used to determine the payment method
	:return: A payment handler instance
	"""

	# Creates an instance of the payment method from the details given
	# Selects the method's strategy from the paymentStrategies dictionary
	# The __repr__ gets the type of the given payment details as a string
	paymentMethod = PaymentMethods.paymentStrategies[paymentDetails.__repr__()](
		paymentDetails # Passes the payment details to the payment method
	)

	if not paymentMethod:
		raise HTTPException(status_code=400, detail="Invalid payment method")

	# Return a new PaymentHandler instance with the determined payment method
	return PaymentHandler(paymentMethod)
