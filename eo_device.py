'''

class for device

'''

class ElectricObject(object):
	'''the electric object class controls commands to a specific EO device'''

	def __init__(self, jsonObject, api):
		
		self.api=api
		
		self.update(jsonObject)


	def refresh(self):
		"""pull updated settings from the api"""
		
		allDevices=self.api.make_request("user_devices", method="GET", parse_json=True)
		for device in allDevices:
			if device['id']==self.id:
				jsonObject=device
				break
		
		self.update(jsonObject)

		
	def update(self, jsonObject):
		"""set variables"""
		
		self.rawJson=jsonObject
		
		self.id=jsonObject['id']
		self.name=jsonObject['name']
		self.release_name=jsonObject['release_name']
		self.backlight_state=jsonObject['backlight_state']
		
		self.deviceURL=self.api.base_url+self.api.api_version_path+self.api.endpoints['devices']+str(self.id)
		
	def turnOff(self):
		"""turn off screen - currently just turning off the backlight"""
		
		self.api.make_request(endpoint="devices", params={'backlight_state':'false'}, method="PUT_AUTH", path_append=str(self.id))
		self.refresh()
		
	def turnOn(self):
		"""turn on screen - currently just turning on the backlight"""
		
		self.api.make_request(endpoint="devices", params={'backlight_state':'true'}, method="PUT_AUTH", path_append=str(self.id))
		self.refresh()
		
	def setSleepSchedule(self, wakeTime, sleepTime):
		"""passed a 24hour string (16:04:32) for wakeTime and sleepTime, set the sleep schedule"""
		
		self.api.make_request(endpoint="devices", params={'sleep_begin':sleepTime, 'sleep_end':wakeTime}, method="PUT_AUTH", path_append=str(self.id))
		#self.refresh()
		
	def enableSleep(self):
		"""enable device sleep"""
		
		self.api.make_request(endpoint="devices", params={'sleep_enabled':'true'}, method="PUT_AUTH", path_append=str(self.id))
		#self.refresh()
		
	def disableSleep(self):
		"""disable device sleeping"""
		
		self.api.make_request(endpoint="devices", params={'sleep_enabled':'false'}, method="PUT_AUTH", path_append=str(self.id))
		#self.refresh()

	def display(self, media_id):
		"""Display media by id."""
		return self.api.make_request("displayed", method="PUT", path_append=str(media_id))
	
	
	def current_artwork_id(self):
		"""Return the id of the artwork currently displayed on the given device.

		Args:
			device_json: The JSON describing the state of a device.

		Returns:
			An artwork id or 0 if the id isn't present in the device_json.
		"""
		self.refresh()
		device_json=self.rawJson
		
		if not device_json:
			return 0
		id = 0
		try:
			id = device_json["current_display_event"]["payload"]["ref"]['id']
		except KeyError as e:
			self.logger.error("problem parsing device JSON. Missing key: {0}".format(e))
		return id

