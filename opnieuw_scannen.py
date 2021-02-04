from time import sleep
import RPi.GPIO as GPIO
import os

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(16, GPIO.IN)

while 1:
	knop = GPIO.input(16)

	if (knop == 1):
		os.system("python3 finale_code.py")