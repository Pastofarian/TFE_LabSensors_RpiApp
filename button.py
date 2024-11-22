import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library

def button_callback(channel):
        print("Bouton sur on")

GPIO.setwarnings(False) # Ignore warning 
GPIO.setmode(GPIO.BOARD) # Use physical pins
GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 

GPIO.add_event_detect(15,GPIO.RISING,callback=button_callback) # Setup event 

message = input("Press enter to quit") # Run until someone presses enter

GPIO.cleanup() # Clean up
