# Imports
import requests
import os
from pprint import pprint
from picamera import PiCamera
import json
import time 
import RPi.GPIO as GPIO
from datetime import datetime, timedelta

# GPIO setups + variable:
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(5, GPIO.OUT)
GPIO.setup(6, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(19, GPIO.OUT)
gevonden_levering = {}

camera = PiCamera()

time.sleep(2)
camera.capture('/home/pi/Project4.0/nummerplaat.jpg')
camera.close()

# API voor de nummerplaatherkening:
from pprint import pprint
# Kan je aanpassen naar de landen dat je zelf wil:
regions = ['be', 'nl'] 
with open('/home/pi/Project4.0/nummerplaat.jpg', 'rb') as fp:
    response = requests.post(
        'https://api.platerecognizer.com/v1/plate-reader/',
        data=dict(regions=regions),  # Optional
        files=dict(upload=fp),
        headers={'Authorization': 'Token c1848db72226e9d76e337ca0fa23d9876eaf035e'})
os.remove("/home/pi/Project4.0/nummerplaat.jpg")
pprint(response.json())	

# Gaat in de if als er geen nummerplaat gevonden is:
if (response.json()['results'] == []):
	print("Geen nummerplaat gevonden.")

# Ga binnen als er een nummerplaat gevonden is:
else:
	nummerplaat = response.json()['results'][0]['plate']
	# api-endpoint 
	URL = "https://backendappproject4.azurewebsites.net/api/leveringen/nummerplaat/" + nummerplaat

	r = requests.get(url = URL) 

	# Data uitpakken in json formaat:
	data = r.json()
	
	headers = {"Content-Type": "application/json"}
	
	for levering in data:
		levering_datum = datetime.strptime(levering['schedule']['datum'], "%Y-%m-%dT%H:%M:%S")
		ts = datetime.now()
		
		tijd_ts = ts.replace(microsecond = 0).time()
		tijd_ts_min = (levering_datum -timedelta(hours = 1)).time()
		tijd_ts_plus = (levering_datum +timedelta(hours = 1)).time()
		
		datum_now = ts.date()
		datum_databse = datetime.strptime(levering['schedule']['datum'], "%Y-%m-%dT%H:%M:%S").date()
		
		# Opnieuw checken op datum en tijd (zie finale code):
		if (datum_now == datum_databse):
			if (tijd_ts >= tijd_ts_min and tijd_ts <= tijd_ts_plus):
				gevonden_levering = levering

	# Ga binnen als er data gevonden is en als de lervering niet compleet is:
	if(data != [] and gevonden_levering['isCompleet'] == False):  
		id = gevonden_levering['leveringID']	
		gevonden_levering['isCompleet'] = True
		response = requests.put('https://backendappproject4.azurewebsites.net/api/leveringen/' + str(id), headers=headers, json=gevonden_levering)
		print(response.json())
		print(gevonden_levering)
		
		# Open slagboom:
		for i in range(130):
			GPIO.output(5, 1)
			time.sleep(0.005)
			GPIO.output(5, 0)
				
			GPIO.output(6, 1)
			time.sleep(0.005)
			GPIO.output(6, 0)
				
			GPIO.output(13, 1)
			time.sleep(0.005)
			GPIO.output(13, 0)
				
			GPIO.output(19, 1)
			time.sleep(0.005)
			GPIO.output(19, 0)

		time.sleep(5)
				
		# Sluit slagboom:
		for i in range(130):
			GPIO.output(19, 1)
			time.sleep(0.005)
			GPIO.output(19, 0)

			GPIO.output(13, 1)
			time.sleep(0.005)
			GPIO.output(13, 0)

			GPIO.output(6, 1)
			time.sleep(0.005)
			GPIO.output(6, 0)

			GPIO.output(5, 1)
			time.sleep(0.005)
			GPIO.output(5, 0)