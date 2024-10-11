
import Adafruit_DHT
import time
from datetime import datetime

# Here is the sensor type (DHT22)
sensor = Adafruit_DHT.DHT22

# The pin is set in the GPIO 17
pin = 17  

# Function which read and print data with timestamp
def read_dht22():
    while True:
        humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

        # If reading ok, print the results 
        if humidity is not None and temperature is not None:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Temp: {temperature:.1f}C, Humidity: {humidity:.1f}%")
        else:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Failed to get reading. Retrying...")

        # Wait for 5 seconds before next read
        time.sleep(5)

if __name__ == "__main__":
    try:
        read_dht22()
    except KeyboardInterrupt:
        print("Program terminated.")
