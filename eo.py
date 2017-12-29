#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Here is a wrapper for the *unreleased* electric objects API.
    Built by
    • Harper Reed (harper@nata2.org) - @harper
    • Gary Boone (gary.boone@gmail.com) - github.com/GaryBoone

    The Electric Objects API is not yet supported by Electric Objects. It may change or
    stop working at any time.

    See the __main__ below for example API calls.

    As configured, this module will display a random image from the favorites you marked on
    electricobjects.com.

    To use as is, you need to set your electricobjects.com login credentials. See the
    get_credentials() function for how to do so.

    Randomized images are picked among the first 200 images shown on your favorites page on
    electricobjects.com. Change MAX_FAVORITES_FOR_DISPLAY below to adjust this limit.

    Usage: $ python eo.py

    Written for Python 2.7.x.
"""


import logging
import logging.handlers
import os
import random
import requests
import sys
import json

import eo_api
from eo_device import ElectricObject
from scheduler import Scheduler

CREDENTIALS_FILE = ".credentials"
USER_ENV_VAR = "EO_USER"
PASSWORD_ENV_VAR = "EO_PASS"
LOG_FILENAME = 'eo-python.log'
LOG_SIZE = 1000000  # bytes
LOG_NUM = 5  # number of rotating logs to keep


SCHEDULE = ["7:02", "12:02", "17:02", "22:02"]  # 24-hour time format
SCHEDULE_JITTER = 10  # in minutes

# The maximum number of favorites to consider for randomly displaying one.
MAX_FAVORITES_FOR_DISPLAY = 200

# The number of favorites to pull per request.
NUM_FAVORITES_PER_REQUEST = 30


class ElectricAccount(object):
	"""The ElectricObject class provides functions for the Electric Objects EO1."""

	def __init__(self, username, password):
		self.api = eo_api.EO_API(username, password)
		self.logger = logging.getLogger(".".join(["eo", self.__class__.__name__]))

		self.userAccountJson=self.user().text
		self.userAccount=json.loads(self.userAccountJson)

		print "initializing eo Account for "+self.userAccount['username']

		print "getting all available devices on account "
		self.devices=[ElectricObject(device, self.api) for device in self.getDevices()]

		print "found "+str(len(self.devices))+" device(s)"

	def user(self):
		"""Obtain the user information."""
		return self.api.make_request("user", method="GET")

	def favorite(self, media_id):
		"""Set a media as a favorite by id."""
		return self.api.make_request("favorited", method="PUT", path_append=media_id)

	def unfavorite(self, media_id):
		"""Remove a media as a favorite by id."""
		return self.api.make_request("favorited", method="DELETE", path_append=media_id)

	def favorites(self):
		"""Return the user's list of favorites in JSON else [].

		Returns:
			An array of up to NUM_FAVORITES_PER_REQUEST favorites in JSON format
			or else an empty list.
		"""
		offset = 0
		favorites = []
		while True:
			params = {
				"limit": NUM_FAVORITES_PER_REQUEST,
				"offset": offset
			}
			result_JSON = self.api.make_request("favorited", method="GET", params=params,
                                                parse_json=True)
			if not result_JSON:
				break
			favorites.extend(result_JSON)
			if len(result_JSON) < NUM_FAVORITES_PER_REQUEST:  # last page
				break
			if len(favorites) > MAX_FAVORITES_FOR_DISPLAY:  # too many
				favorites = favorites[:MAX_FAVORITES_FOR_DISPLAY]
				break
			offset += NUM_FAVORITES_PER_REQUEST
		return favorites

	def getDevices(self):
		"""Return a list of devices in parsed JSON format, else None."""
		devicesList=self.api.make_request("user_devices", method="GET", parse_json=True)
		return devicesList

	def choose_random_item(self, items, excluded_id=None):
		"""Return a random item, avoiding the one with the excluded_id, if given.
		Args:
			items: a list of Electric Objects artwork objects.

		Returns:
			An artwork item, which could have the excluded_id if there's only one choice,
			or [] if the list is empty.
		"""
		if not items:
			return []
		if len(items) == 1:
			return items[0]
		if excluded_id:
			items = [item for item in items if item["artwork"]["id"] != excluded_id]
		return random.choice(items)

	def display_random_favorite(self):
		"""Retrieve the user's favorites and display one of them randomly on the first device
		associated with the signed-in user.

		Note that at present, only the first 20 favorites are returned by the API.

		A truely random choice could be the one already displayed. To avoid that, first
		request the displayed image and remove it from the favorites list, if present.

		Note:
			This function works on the first device if there are multiple devices associated
			with the given user.

		Returns:
			The id of the displayed favorite, else 0.
		"""
		devs = self.devices()
		if not devs:
			self.logger.error("in display_random_favorite: no devices returned.")
			return 0
		device_index = 0  # First device of user.
		current_image_id = self.current_artwork_id(devs[device_index])

		favs = self.favorites()
		if favs == []:
			return 0
		fav_item = self.choose_random_item(favs, current_image_id)
		if not fav_item:
			return 0
		fav_id = fav_item["artwork"]["id"]
		res = self.display(str(fav_id))
		return fav_id if res else 0

	def set_url(self, url):
		"""Display the given URL on the first device associated with the signed-in user.
		Return True on success.
		"""
		devs = self.devices()
		if not devs:
			self.logger.error("in set_url: no devices returned.")
			return 0
		device_index = 0  # First device of user.
		device_id = devs[device_index]["id"]

		request_url = self.api.base_url + "set_url"
		params = {
			"device_id": device_id,
			"custom_url": url
		}
		response = self.api.net.post_with_authenticity(request_url, params)
		return response.status_code == requests.codes.ok


def get_credentials():
	"""Returns the electricobjects.com username and password. They can be set here in the code,
    in environment variables, or in a file named by CREDENTIALS_FILE.

    A simple way to set them in the environment variables is prefix your command with them.
    For example:
        $ EO_USER=you@example.com EO_PASS=pword python eo.py

    Don't forget to clear your command history if you don't want the credentials stored.

    This function allows us to avoid uploading credentials to GitHub. In addition to not
    writing them here, the credentials filename is included in the .gitignore file.

    The sources are read in the order of: default, then environment variables, then file.
    Each source overwrites the username and password separately, if set in that source.

    Returns:
        A dictionary with key/values for the username and password.
    """
	username = ""  # You can set them here if you don"t plan on uploading this code to GitHub.
	password = ""

	username = os.environ[USER_ENV_VAR] if USER_ENV_VAR in os.environ else username
	password = os.environ[PASSWORD_ENV_VAR] if PASSWORD_ENV_VAR in os.environ else password

	try:
		with open(CREDENTIALS_FILE, "r") as f:
			username = next(f).strip()
			password = next(f).strip()
	except:
		pass  # Fail silently if no file, missing lines, or other problem.

	return {"username": username, "password": password}


def setup_logging():
	"""Set up logging to log to rotating files and also console output."""
	formatter = logging.Formatter('%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s')
	logger = logging.getLogger("eo")
	logger.setLevel(logging.INFO)

	# rotating file handler
	fh = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_SIZE, backupCount=LOG_NUM)
	fh.setFormatter(formatter)
	logger.addHandler(fh)

	# console handler
	ch = logging.StreamHandler()
	ch.setFormatter(formatter)
	logger.addHandler(ch)

	return logger


def show_a_new_favorite(eo):
	"""Update the EO1 with a new, randomly selected favorite."""
	logger = logging.getLogger("eo")
	logger.info('Updating favorite')
	displayed = eo.display_random_favorite()
	if displayed:
		logger.info("Displayed artwork id " + str(displayed))


def demo(eo):
	"""An example that displays a random favorite."""
	logger = logging.getLogger("eo")

	displayed = eo.display_random_favorite()
	if displayed:
		logger.info("Displayed artwork id " + str(displayed))

"""
def main():
    setup_logging()

    credentials = get_credentials()
    if credentials["username"] == "" or credentials["password"] == "":
        logger = logging.getLogger("eo")
        logger.error("The username or password are blank. See code for how to set them. Exiting.")
        exit()

    eo = ElectricObject(username=credentials["username"], password=credentials["password"])

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        show_a_new_favorite(eo)
        exit()
    '''
    scheduler = Scheduler(SCHEDULE, lambda: show_a_new_favorite(eo), schedule_jitter=SCHEDULE_JITTER)
    scheduler.run()
    '''

if __name__ == "__main__":
    main()
"""
setup_logging()

#testing only
credentials=get_credentials()
eoAccount=ElectricAccount(credentials['username'], credentials['password'])

for device in eoAccount.devices:
	print "device "+device.name+" is currently displaying "+str(device.current_artwork_id())
