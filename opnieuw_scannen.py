# Imports:
from time import sleep
import RPi.GPIO as GPIO
import os

# GPIO setups:
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.IN)

# Constant checken of knop ingedrukt is of niet, is dit het geval gaat finale_code.py gerund worden:
while 1:
	knop = GPIO.input(16)

	if (knop == 1):
		os.system("python3 finale_code.py")