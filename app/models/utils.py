from functools import wraps


def allowPatches(cls, value):
	"""
	Allow patches for the field
	"""
	if cls is None:
		raise ValueError('cls cannot be None')
	if value is None:
		raise ValueError('value cannot be None')
	return value