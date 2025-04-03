"""
This file contains utility functions that are used in the application.
"""
import datetime


def quickSort(listObj: list, key=lambda x: x, reverse=False) -> list:
	"""
	Sorts an listObject using the quicksort algorithm.
	:param listObj: A list to sort.
	:param reverse: Whether to sort in reverse.
	:param key: A function to determine the key to sort by.
	:return: A sorted list.
	"""

	if len(listObj) <= 1:
		return listObj

	pivot = listObj[len(listObj) // 2]
	left = [x for x in listObj if key(x) < key(pivot)]
	middle = [x for x in listObj if key(x) == key(pivot)]
	right = [x for x in listObj if key(x) > key(pivot)]

	if reverse:
		return quickSort(right, key, reverse) + middle + quickSort(left, key, reverse)
	else:
		return quickSort(left, key, reverse) + middle + quickSort(right, key, reverse)


def dateRangeGenerator(startDate: str, endDate: str):
	"""
	Generates a range of dates between two ISO dates.
	:param startDate: The start date.
	:param endDate: The end date.
	"""

	startDate, endDate = datetime.datetime.fromisoformat(startDate), datetime.datetime.fromisoformat(endDate)
	delta = datetime.timedelta(days=1)
	while startDate <= endDate:
		yield startDate.strftime('%Y-%m-%d')
		startDate += delta
