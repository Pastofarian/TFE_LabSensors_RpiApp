import serial
import time

# Configure serial port
ser = serial.Serial(
    port='/dev/serial0',  # Use the appropriate port 
    baudrate=9600,
    timeout=1
)

time.sleep(2)  # Allow serial port to initialize

print("Envoi de données de HC12. Ctrl+C pour stop.")  # Notify user

try:
    counter = 0
    while True:
        message = f"Message numéro {counter}"  # Create message
        ser.write((message + '\n').encode('utf-8'))  # Send message with newline
        print(f"Envoyé : {message}")
        counter += 1
        time.sleep(1)  # Wait 1 second before sending next message

except KeyboardInterrupt:
    print("Arrêt de l'envoi.")  # Stop on user interrupt
finally:
    ser.close()  # Close the serial port

