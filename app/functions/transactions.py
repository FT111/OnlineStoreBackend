from abc import ABC, abstractmethod
from enum import Enum

from fastapi import HTTPException
from typing_extensions import Union

from app.models.transactions import CardPaymentDetails


class PaymentMethods:
	# Possible payment string representations, used to determine the payment method from the user
	class Types(str, Enum):
		CARD = "card"

	class PaymentStrategy(ABC):
		@abstractmethod
		def __init__(self):
			pass

		@abstractmethod
		def pay(self, value: int, recipient: Union[str, int]) -> Union[bool, HTTPException]:
			pass

	class CardPayment(PaymentStrategy):
		def __init__(self, details: CardPaymentDetails):
			self.details = details

		def pay(self, value: int, recipient):
			# Do card payment
			return True

	# Dictionary of payment methods and their implementations
	paymentStrategies = {
		Types.CARD: CardPayment
	}


class PaymentHandler:
	"""
	Unified interface for payment methods

	Set a payment method strategy to use
	"""
	def __init__(self, paymentMethod: PaymentMethods.PaymentStrategy):
		self.paymentMethod = paymentMethod

	def makePayment(self, value: int, recipientIdentifier: Union[str, int]) -> Union[bool, HTTPException]:
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

	# Determine the payment method form the details given.
	# Selects the method's strategy from the paymentStrategies dictionary
	# The __repr__ gets the type of the given payment details as a string
	paymentMethod = PaymentMethods.paymentStrategies[paymentDetails.__repr__()](
		paymentDetails
	)

	if not paymentMethod:
		raise HTTPException(status_code=400, detail="Invalid payment method")

	# Return a new PaymentHandler instance with the determined payment method
	return PaymentHandler(paymentMethod)
