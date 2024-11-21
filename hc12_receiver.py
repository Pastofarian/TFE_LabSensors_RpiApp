import serial
import time

# Configure serial port
ser = serial.Serial(
    port='/dev/serial0',  # Use /dev/serial0
    baudrate=9600,
    timeout=1.5
)

time.sleep(2)  # Allow serial port to initialize
ser.flushInput()  # Clear any input data

print("Ctrl-C pour stop")

while True:
    line = ser.readline()  # Read a line from serial
    if line:
        string = line.decode('utf-8', 'ignore').strip()  # Decode and clean the string
        print("Recu: " + string)
        try:
            num = int(string)  # Convert to integer if possible
            print("Nombre converti: " + str(num))
        except ValueError:
            print("Erreur en convertissant l'integer.")
    else:
        print("Pas de données recue")

