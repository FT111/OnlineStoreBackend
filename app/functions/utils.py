"""
This file contains utility functions that are used in the application.
"""
import base64
import datetime
import time
import uuid

from typing_extensions import Union


def quickSort(listObj: Union[list, set, tuple], key=lambda x: x, reverse=False) -> list:
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
	Generates a range of string ISO dates between two ISO dates.
	:param startDate: The start date. YYYY-MM-DD
	:param endDate: The end date. YYYY-MM-DD
	"""

	startDate, endDate = datetime.datetime.fromisoformat(startDate), datetime.datetime.fromisoformat(endDate)
	delta = datetime.timedelta(days=1)
	while startDate <= endDate:
		yield startDate.strftime('%Y-%m-%d')
		startDate += delta


def userStatisticsGenerator(dataRepoInstance, user):
	"""
	Generates a stream of user statistics.
	:param user: The user to get statistics for, auth object
	:param dataRepoInstance: The data repository.
	"""

	previousSales = None
	while True:
		endDate = datetime.timedelta(weeks=2)
		startDate = datetime.datetime.now() - endDate
		stats: dict = dataRepoInstance.getUserStatistics(user, startDate.strftime('%Y-%m-%d'), datetime.datetime.now().strftime('%Y-%m-%d'))
		if stats.get('sale'):
			if stats['sale']['count'] != previousSales:
				if previousSales:
					yield f'event: sale\ndata: {stats['sale']['count'] - previousSales}\n\n'

				previousSales = stats['sale']['count']

		yield f'event: userStatsUpdate\ndata: {stats}\n\n'
		time.sleep(10)


def processAndStoreImagesFromBase64(images: Union[str, list], relationID, prefix: str, folder='listingImages') -> Union[str, list, None]:
	"""
	Store images from base64 strings.
	Categorises them into folders.
	:param folder: The folder to store the images in. Must be a subfolder of app/static and already exist.
	:param images: A list of image strings to store, can be base64 or existing file paths
	:param relationID: The ID of the relation to store the images for
	:param prefix: The prefix to use for the image filenames
	:return:
	"""

	useList = True
	if not isinstance(images, list):
		# If the images are not a list, convert them to a list
		images = [images]
		useList = False

	# Save new images to the filesystem
	for index, image in enumerate(images):
		# If the image is a base64 string, save it to the filesystem
		if image.startswith('data:image'):
			try:
				filetype = image.split(';')[0].split('/')[1]
				# Remove the base64 header
				image = image.split('base64,')[1]

				# Save the image to the filesystem
				filename = f"{prefix}-{relationID}-{int(uuid.uuid4())}.{filetype}"
				with open(f"app/static/{folder}/{filename}", 'wb') as file:
					file.write(base64.decodebytes(image.encode('utf-8')))
				images[index] = filename
				continue
			except Exception as e:
				del images[index]
				continue

		# If the image is an existing filepath, keep it
		if image.startswith(prefix):
			continue

		# Remove the image if it isn't a base64 string or filepath
		print(f"Invalid image: {image}")
		del images[index]

	if not images:
		# If no images were saved, return None
		return []

	if not useList:
		# If the images were not a list, return the first image
		return images[0]

	return images
