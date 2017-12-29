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

	def display(self, media_id):
		"""Display media by id."""
		#return self.api.make_request("displayed", method="PUT", path_append=media_id)
		
		self.api.make_request(endpoint="devices", params={'current_display_event':{ 'payload' : {'ref_type':'Artwork', 'ref':{"id":172939,"param":"2PKDG","share_path":"/objects/2PKDG","title":"Bailey","description":null,"artist_name":"Sharleen","is_original":true,"is_premium":true,"processed":true,"processing_status":null,"display_url":"http://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=webp&dpr=1&w=1080&h=1920&bg=000&fit=crop&lossless=false&s=ba93814be6c0a657ffeaabad34098069","created_at":"2017-06-26T15:40:34.489-04:00","updated_at":"2017-12-29T14:10:48.028-05:00","published_at":"2017-06-27T09:17:00.000-04:00","total_time_displayed":3316746,"users_currently_displaying_count":1,"users_displayed_count":27,"favorited_artworks_count":2,"resolution":"2700x4800","artist_id":null,"artist_slug":null,"user":null,"organization":null,"filetype":"image/jpeg","static_previews":[{"width":64,"height":113,"url":"https://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=jpg&dpr=1&w=64&h=113&bg=000&fit=crop&lossless=false&s=71b2018290b95f12b5937f549ab77fa7"},{"width":128,"height":227,"url":"https://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=jpg&dpr=1&w=128&h=227&bg=000&fit=crop&lossless=false&s=4d7a282a84cf19875f19765ed8c6b4ed"},{"width":180,"height":320,"url":"https://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=jpg&dpr=1&w=180&h=320&bg=000&fit=crop&lossless=false&s=4bbeb0d5dca0ebfab95d303d0dc28f42"},{"width":252,"height":448,"url":"https://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=jpg&dpr=1&w=252&h=448&bg=000&fit=crop&lossless=false&s=886b20c4b33d1a5825d49c662ef41abd"},{"width":360,"height":640,"url":"https://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=jpg&dpr=1&w=360&h=640&bg=000&fit=crop&lossless=false&s=255f025535fee9e6a5b02d4956886bdb"},{"width":480,"height":853,"url":"https://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=jpg&dpr=1&w=480&h=853&bg=000&fit=crop&lossless=false&s=8aaa7c9b6d502927fc67df884da9d3bf"},{"width":756,"height":1344,"url":"https://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=jpg&dpr=1&w=756&h=1344&bg=000&fit=crop&lossless=false&s=a5ede7217a6398f937a4437700ed6756"},{"width":1080,"height":1920,"url":"https://electric-objects-web-production-attachments.imgix.net/artworks/preview_images/000/172/939/original/1fb1da817322313dc48f4b3f1c37ded5/bailey.jpg?ixlib=rb-0.3.5&fm=jpg&dpr=1&w=1080&h=1920&bg=000&fit=crop&lossless=false&s=b4e2e8be2707ef2919ce6b208e7f267f"}],"animated_previews":[],"video_previews":[]}
																															}}})
	
	
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

