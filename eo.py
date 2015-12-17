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

import datetime
from lxml import html
import os
import random
import requests
import time

CREDENTIALS_FILE = ".credentials"
USER_ENV_VAR = "EO_USER"
PASSWORD_ENV_VAR = "EO_PASS"

# The maximum number of favorites to consider for randomly displaying one.
MAX_FAVORITES_FOR_DISPLAY = 200

# The number of favorites to pull per request.
NUM_FAVORITES_PER_REQUEST = 30

# BEST PRACTICE: don't hit server at maximum rate.
# Minimum time between requests.
MIN_REQUEST_INTERVAL = 0.75  # seconds, float

# How often should we sign-in?
SIGNIN_INTERVAL_IN_HOURS = 4  # hours

# BEST PRACTICE: If you do retries, back them off exponentially. If the server is down
# or struggling to come back up, you'll avoid creating a stampede of clients retrying
# their requests.
# What's the first retry delay? If more retries are needed, double each delay.
INITIAL_RETRY_DELAY = 4.0  # seconds, float

# In this code, if there's a missed update, we can just wait until the next scheduled update
# to try again. So we don't need to retry many times.
# The number of retry attempts.
NUM_RETRIES = 4


def log(msg):
    timestamp = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d_%H:%M:%S")
    print "{0}: {1}".format(timestamp, msg)


class ElectricObject:
    """The ElectricObject class provides the functions for the Electric Objects API calls.

    It maintains the state of credentials and the currently signed-in session.
    Usage: instantiate the object with credentials, then make one or more API calls
    with the object.
    """

    # Class variables
    base_url = "https://www.electricobjects.com/"
    api_version_path = "api/v2/"
    endpoints = {
        "user": "user/",
        "devices": "user/devices/",
        "displayed": "user/artworks/displayed/",
        "favorited": "user/artworks/favorited/"
        }

    def __init__(self, username, password):
        """Upon initialization, set the credentials. But don't attempt to sign-in until
        an API call is made.
        """
        self.username = username
        self.password = password
        self.signed_in_session = None
        self.last_request_time = 0
        self.last_signin_time = 0

    def signin(self):
        """ Sign in. If successful, set self.signed_in_session to the session for reuse in
        subsequent requests. If not, set self.signed_in_session to None.

        Note that while the session in self.signed_in_session can be reused for subsequent
        requests, the sign-in may expire after some time. So requests that fail should
        try signing in again.
        """
        self.signed_in_session = None
        try:
            session = requests.Session()
            self.check_request_rate()
            signin_response = session.get(self.base_url + "sign_in")
            if signin_response.status_code != requests.codes.ok:
                log("Error: unable to sign in. Status: {0}, response: {1}".
                    format(signin_response.status_code, signin_response.text))
                return
            tree = html.fromstring(signin_response.content)
            authenticity_token = tree.xpath("string(//input[@name='authenticity_token']/@value)")
            if authenticity_token == "":
                return
            payload = {
                "user[email]": self.username,
                "user[password]": self.password,
                "authenticity_token": authenticity_token
            }
            self.check_request_rate()
            p = session.post(self.base_url + "sign_in", data=payload)
            if p.status_code != requests.codes.ok:
                log("Error: unable to sign in. Status: {0}, response: {1}".
                    format(signin_response.status_code, signin_response.text))
                return
            self.last_signin_time = time.clock()
            self.signed_in_session = session
        except Exception as e:
            log("Exception in signin: " + str(e))

    def signed_in(self):
        """ Return true if we have a valid signed-in session. """
        return self.signed_in_session is not None

    def check_signin_status(self):
        """Check if think we're signed in or whether enough time has passed that we
        should sign in again.
        """
        time_since_signin = time.clock() - self.last_signin_time
        if not self.signed_in() or time_since_signin > SIGNIN_INTERVAL_IN_HOURS * 3600.0:
            self.signin()
            if not self.signed_in():
                return False
        return True

    def check_request_rate(self):
        """ Are we making requests too fast? If so, pause.

        Specifically, check the current time against the last request time. If
        less than MIN_REQUEST_INTERVAL, sleep the remaining time.

        TODO: This function pauses the whole program. Improvement: create a
        request queue that handles request asynchronously.
        """
        interval = time.clock() - self.last_request_time
        if interval < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - interval)

    def execute_request(self, url, params=None, method="GET"):
        """ Request the given URL with the given method and parameters.

        Args:
            url: The URL to call.
            params: The optional parameters.
            method: The HTTP request type {GET, POST, PUT, DELETE}.

        Returns:
            The request result or None.
        """
        self.check_request_rate()
        try:
            if method == "GET":
                return self.signed_in_session.get(url, params=params)
            elif method == "POST":
                return self.signed_in_session.post(url, params=params)
            elif method == "PUT":
                return self.signed_in_session.put(url)
            elif method == "DELETE":
                return self.signed_in_session.delete(url)
            else:
                log("Unknown request type: {0}".format(method))
        except Exception as e:
            log("Error in making HTTP request: {0}".format(e))
        return None

    def make_request(self, endpoint, params=None, method="GET", path_append=None):
        """Create a request of the given type and make the request to the Electric Objects API.

        Retry the request up to NUM_RETRIES times if:

        1) execute_request() returns None, which would indicate a problem caught the request
        library. These would include network connectivity issues or request timeouts.

        OR

        2) the server returns a 50X response code. Note that 30X, and 40X responses are not errors
        that could benefit from retries, so are returned immediately.

        Args:
            endpoint: The id of the request target API path in self.endpoints.
            params: The URL parameters.
            method: The HTTP request type {GET, POST, PUT, DELETE}.
            path_append: An additional string to add to the URL, such as an ID.

        Returns:
            The request result or None.
        """
        # Check sign-in
        signin_ok = self.check_signin_status()
        if not signin_ok:
            return None

        # Build URL.
        url = self.base_url + self.api_version_path + self.endpoints[endpoint]
        if path_append:
            url += path_append

        # Call API with retries and exponential backoff.
        retries = 0
        delay = INITIAL_RETRY_DELAY
        while True:
            pass
            response = self.execute_request(url, params=params, method=method)

            if response:
                if response.status_code < 500:
                    return response
                else:
                    log("Error from API server. Response: {0} {1}.".
                        format(response.status_code, response.reason))

            if retries == NUM_RETRIES:
                break

            # retries + 1: Use natural numbers for readability.
            log("Error: Failed request {0} of {1}. Retrying in {2} seconds.".
                format(retries + 1, NUM_RETRIES + 1, delay))

            # Exponential backoff: Double the delay between each retry, or equivilently,
            #     delay = INITIAL_RETRY_DELAY * 2 ** retries
            # The constant, 2 in this case, or doubling each delay, doesn't matter so long as the
            # delay increases significantly with each retry, allowing congestion at the server
            # to disperse.
            delay *= 2
            retries += 1
            time.sleep(delay)

        log("Error: Maximum HTTP request attempts ({0}) exceeded.".format(NUM_RETRIES + 1))
        return None

    def make_JSON_request(self, endpoint, params=None, method="GET", path_append=None):
        """Create and make the given request, returning the result as JSON, else []."""
        response = self.make_request(endpoint, params=params, method=method, path_append=path_append)
        if response is None:
            return []
        elif response.status_code != requests.codes.ok:
            log("Error in make_JSON_request(). Response: {0} {1}".
                format(response.status_code, response.reason))
            return []
        try:
            return response.json()
        except:
            log("Error in make_JSON_request(): unable to parse JSON")
        return []

    def user(self):
        """Obtain the user information."""
        return self.make_request("user", method="GET")

    def favorite(self, media_id):
        """Set a media as a favorite by id."""
        return self.make_request("favorited", method="PUT", path_append=media_id)

    def unfavorite(self, media_id):
        """Remove a media as a favorite by id."""
        return self.make_request("favorited", method="DELETE", path_append=media_id)

    def display(self, media_id):
        """Display media by id."""
        return self.make_request("displayed", method="PUT", path_append=media_id)

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
            result_JSON = self.make_JSON_request("favorited", method="GET", params=params)
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

    def devices(self):
        """Return a list of devices in JSON format, else []."""
        return self.make_JSON_request("devices", method="GET")

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
        """Retrieve the user's favorites and displays one of them randomly.

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
            log("Error in display_random_favorite: no devices returned.")
            return 0
        device_index = 0
        current_image_id = devs[device_index]["reproduction"]["artwork"]["id"]

        favs = self.favorites()
        if favs == []:
            return 0
        fav_item = self.choose_random_item(favs, current_image_id)
        if not fav_item:
            return 0
        fav_id = fav_item["artwork"]["id"]
        self.display(str(fav_id))
        return fav_id

    def set_url(self, url):
        """Set a URL to be on the display.
        Note: IN PROGRESS. This function does not successfully display a URL on the EO1 currently.
        """
        url = "set_url"
        with requests.Session() as s:
            eo_sign = s.get(self.base_url + "sign_in")
            tree = html.fromstring(eo_sign.content)
            authenticity_token = tree.xpath("string(//input[@name='authenticity_token']/@value)")
            payload = {
                "user[email]": self.username,
                "user[password]": self.password,
                "authenticity_token": authenticity_token
            }
            p = s.post(self.base_url + "sign_in", data=payload)
            if p.status_code == requests.codes.ok:
                eo_sign = s.get(self.base_url + "set_url")
                tree = html.fromstring(eo_sign.content)
                authenticity_token = tree.xpath("string(//input[@name='authenticity_token']/@value)")
                params = {
                  "custom_url": url,
                  "authenticity_token": authenticity_token
                }
                r = s.post(self.base_url + url, params=params)
                return r.status_code == requests.codes.ok


def get_credentials():
    """Obtains the electricobjects.com username and password. They can be set here in the code,
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


def main():
    """An example main that displays a random favorite."""

    credentials = get_credentials()
    eo = ElectricObject(username=credentials["username"], password=credentials["password"])
    displayed = eo.display_random_favorite()
    log("Displayed artwork id " + str(displayed))

    # Mark a media item as a favorite.
    # print eo.favorite("5626")
    # Now unfavorite it.
    # print eo.unfavorite("5626")

    # Display a media item by id.
    # print eo.display("1136")

    # Let's set a URL.
    # print eo.set_url("http://www.harperreed.com/")


if __name__ == "__main__":
    main()
