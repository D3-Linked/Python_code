# Imports:
import requests
import os
from picamera import PiCamera
import time
import RPi.GPIO as GPIO
import json
from datetime import datetime, timedelta

import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Raspberry Pi hardware SPI config + variable:
DC = 23
RST = 24
SPI_PORT = 0
SPI_DEVICE = 1
TRIG = 4
ECHO = 17
gevonden_levering = {}
datum_juist = 0
disp = LCD.PCD8544(DC, RST, spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE, max_speed_hz=4000000))

# Setups van de GPIO:
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(5, GPIO.OUT)
GPIO.setup(6, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(19, GPIO.OUT)
GPIO.setup(TRIG,GPIO.OUT)
GPIO.setup(ECHO,GPIO.IN)

# Definitie voor het inladen van de LCD:
def lcd():
	# Library inladen:
	disp.begin(contrast=60)

	# Clear display:
	disp.clear()
	disp.display()
		
	image = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))

	# Object aamaken om een image te plaatsen:
	draw = ImageDraw.Draw(image)
		 
	# Een wit gevuld vierkant om het scherm te clearen:
	draw.rectangle((0,0,LCD.LCDWIDTH,LCD.LCDHEIGHT), outline=255, fill=255)
	
	# Inladen van default font:
	font = ImageFont.load_default()
	
	return draw, image, font
	
# Definitie voor het aanroepen van de sensor aan de laadkade:
def isBezetCheck():
	GPIO.output(TRIG, False)
	print ('Waiting a few seconds for the sensor to settle')
	time.sleep(5)
	GPIO.output(TRIG, True)
	time.sleep(0.00001)
	GPIO.output(TRIG, False)
					
	# Aanmaken van variable wanneer de sensor het signaal verstuurd en wanneer het aankomt, de tijd tussen deze 2 wordt opgeslagen:
	while GPIO.input(ECHO)==0:
		pulse_start = time.time()
	while GPIO.input(ECHO)==1:
		pulse_end = time.time()

	# Afstand berekenen
	pulse_duration = pulse_end - pulse_start
	distance = pulse_duration * 17165
	distance = round(distance, 1)
	print ('Distance:',distance,'cm')
	
	r = requests.get("https://backendappproject4.azurewebsites.net/api/laadkades/1")
	data = r.json()
	nummer = data['nummer']
	locatie = data['locatie']
	headers = {"Content-Type": "application/json"}

	isBezet = {"nummer": nummer, "isBezet": True, "locatie": locatie}
	nietBezet = {"nummer": nummer, "isBezet": False, "locatie": locatie}
					
	# Is bezet aanpassen naar True wanneer de afstand minder is dan 11 (maw, wanneer de vrachtwagen onder de laadkade staat:
	if(distance < 11):
		response = requests.put('https://backendappproject4.azurewebsites.net/api/laadkades/1', headers=headers, json=isBezet)
		print(response.json())
	else:
		response = requests.put('https://backendappproject4.azurewebsites.net/api/laadkades/1', headers=headers, json=nietBezet)
		print(response.json())
							
	return response.json()

camera = PiCamera()

time.sleep(2)
camera.capture('/home/pi/Project4.0/nummerplaat.jpg')
camera.close()

# API voor de nummerplaatherkening:
from pprint import pprint
# Kan je aanpassen naar de landen dat je zelf wil:
regions = ['be', 'nl']
foto = open('/home/pi/Project4.0/nummerplaat.jpg', 'rb')
with foto as fp:
    response = requests.post(
        'https://api.platerecognizer.com/v1/plate-reader/',
        data=dict(regions=regions),
        files=dict(upload=fp),
        headers={'Authorization': 'Token c1848db72226e9d76e337ca0fa23d9876eaf035e'})
os.remove("/home/pi/Project4.0/nummerplaat.jpg")
pprint(response.json())

# Je mag in deze if gaan wanneer er geen results zijn van de API of wanneer er geen nummerplaat gelezen is:
if (response.json()['results'] == []):
	print("Geen nummerplaat gevonden.")
	disp
	draw = lcd()
	font = draw[2]
		
	# Schrijf tekst:		
	draw[0].text((1,8), 'Geen nummer-', font=font)	
	draw[0].text((1,16), 'plaat gevonden.', font=font)
	draw[0].text((1,24), 'Probeer', font=font)
	draw[0].text((1,32), 'opnieuw!', font=font)
		 
	# Display image:
	disp.image(draw[1])
	disp.display()
	
	time.sleep(5)
	disp.clear()
	disp.display()	
	
# Als er een nummerplaat gelezen is wordt er in deze else gegaan:
else:
	nummerplaat = response.json()['results'][0]['plate']
	# api-endpoint 
	URL = "https://backendappproject4.azurewebsites.net/api/leveringen/nummerplaat/" + nummerplaat

	# Verstuur een get request en slaag de reactie op in een reactie object:
	r = requests.get(url = URL) 

	# Pak de data uit in json formaat:
	data = r.json()
	
	# Check elke levering in data:
	for levering in data:
		levering_datum = datetime.strptime(levering['schedule']['datum'], "%Y-%m-%dT%H:%M:%S")
		ts = datetime.now()
		
		tijd_ts = ts.replace(microsecond = 0).time()
		tijd_ts_min = (levering_datum -timedelta(hours = 1)).time()
		tijd_ts_plus = (levering_datum +timedelta(hours = 1)).time()
		
		datum_now = ts.date()
		datum_databse = datetime.strptime(levering['schedule']['datum'], "%Y-%m-%dT%H:%M:%S").date()
		
		# Wanneer de huidige datum gelijk is aan de datum van de datum dat in de levering is ingegeven:
		if (datum_now == datum_databse):
			# Als de datum gelijk is checken we de tijd:
			# We checken hier of de huidige tijd groter is dan huidige tijd -1 en de huidige tijd +1:
			# M.a.w. zit de huidige tijd tussen een uur ervoor en erna, buffer voor vrachtwagen:
			datum_juist = 1
			if (tijd_ts >= tijd_ts_min and tijd_ts <= tijd_ts_plus):
				gevonden_levering = levering
	
	if(gevonden_levering == {} and datum_juist == 1): 
		datum_juist = 0
		disp
		draw = lcd()
		font = draw[2]
		
		# Schrijf tekst:	
		draw[0].text((0,8), 'U bent niet op', font=font)	
		draw[0].text((0,16), 'het gewenste', font=font)
		draw[0].text((0,24), 'tijdstip', font=font)
		draw[0].text((0,32), 'gearriveerd.', font=font)
		 
		# Display image:
		disp.image(draw[1])
		disp.display()
		
		time.sleep(5)
		disp.clear()
		disp.display()	
		
	# Als de data leeg is of de gevonden_levering is leeg of als isCompleet op True is gezet:
	elif (data == [] or gevonden_levering == {} or gevonden_levering['isCompleet'] == True):	
		datum_juist = 0
		print("Geen levering met deze nummerplaat gevonden.")
		disp
		draw = lcd()
		font = draw[2]
		
		# Schrijf tekst:		
		draw[0].text((1,8), 'Geen levering', font=font)	
		draw[0].text((1,16), 'gevonden met', font=font)
		draw[0].text((1,24), 'deze nummer-', font=font)
		draw[0].text((1,32), 'plaat.', font=font)
		 
		# Display image:
		disp.image(draw[1])
		disp.display()
		
		time.sleep(5)
		disp.clear()
		disp.display()
	
	# Waneeer de gevonden_levering niet leeg is:
	elif (gevonden_levering != {}):
		
		nummer = gevonden_levering['laadkade']['nummer']
		locatie = gevonden_levering['laadkade']['locatie']
			
		disp
		draw = lcd()
			
		# Laad default font:
		font = ImageFont.load_default()
			
		# Schrijf tekst:		
		draw[0].text((1,6), 'Uw nummer-', font=font)
		draw[0].text((1,14), 'plaat is:', font=font)
		draw[0].text((1,22), nummerplaat, font=font)		
		draw[0].text((1,30), locatie, font=font)
		draw[0].text((1,38), 'Laadkade ' + str(nummer), font=font)		
			 
		# Display image:
		disp.image(draw[1])
		disp.display()
					 
		# Open de slagboom:
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
			
		# Sluit de slagboom:
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

		disp.clear()
		disp.display()
		time.sleep(5)
		
		# Hier beginnen we te checken of er een vrachtwagen onder de laadkade staat, dit gebeurd alleen als er en levering gevonden is:
		while 1:
			check = isBezetCheck()
			
			# Als is bezet of True komt en daarna op False wordt er opnieuw gekeken naar de nummerplaat en kan de vrachtwagen terug naar buiten:
			if(check['isBezet'] == True):
				while 1:
					check = isBezetCheck()
					if(check['isBezet'] == False):
					
						# Spring naar andere een code:
						os.system("python3 test_buitenrijden.py")
						while 1:
						
							# Spring naar andere een code:
							os.system("python3 opnieuw_scannen.py")