from abc import ABC, abstractmethod
from enum import Enum

from fastapi import Query, HTTPException
from typing_extensions import Union


class PaymentMethods:
	# Possible payment string representations, used to determine the payment method from the user
	class Types(str, Enum):
		CARD = "card"

	class PaymentStrategy(ABC):
		@abstractmethod
		def __init__(self):
			pass

		@abstractmethod
		def pay(self, value: int, recipient: Union[str, int]) -> bool:
			pass

	class CardPayment(PaymentStrategy):
		def __init__(self):
			self.type = PaymentMethods.Types.CARD

		def pay(self, value: int, recipient) -> bool:
			# Do card payment
			return True


class PaymentHandler:
	def __init__(self, paymentMethod: PaymentMethods.PaymentStrategy):
		self.paymentMethod = paymentMethod

	def makePayment(self, value: int, recipientIdentifier: Union[str, int]) -> bool:
		return self.paymentMethod.pay(value, recipientIdentifier)


def paymentHandlerFactory(paymentType: PaymentMethods.Types = Query(...)) -> PaymentHandler:
	"""
	Factory function to create a payment handler
	Used to determine the payment method from the user input
	Works as a dependency for FastAPI endpoints
	:param paymentType:
	:return: A payment handler instance
	"""
	if paymentType == PaymentMethods.Types.CARD:
		return PaymentHandler(PaymentMethods.CardPayment())
	else:
		raise HTTPException(status_code=400, detail="Invalid payment method")
