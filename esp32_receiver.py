import serial
import sqlite3
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials
import traceback  # to display full error 

# Google Sheets configuration
def log_to_google_sheet(sensor_id, temperature, humidity, pressure):
    try:
        print("Setting up Google Sheets credentials...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            '/var/www/rpi_app/rpiapp-443210-49cc01bfcf2b.json', scope
        )
        client = gspread.authorize(creds)

        # open Google Sheet
        print("Opening Google Sheet...")
        sheet = client.open('Temperature  and Humidity - Rpi').sheet1  # Assurez-vous que le nom est correct

        # add the new row
        print("Preparing data row...")
        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sensor_id,
            round(temperature, 2),
            round(humidity, 2),
            # round(pressure, 2) # to check for the new column !!
        ]
        print(f"Appending row to Google Sheets: {row}")
        sheet.append_row(row)
        print("Data logged to Google Sheets.")
    except Exception as e:
        print(f"Error logging to Google Sheets: {e}")
        traceback.print_exc()

# db configuration
def log_datas(sensor_id, temperature, humidity, pressure):
    try:
        print("Connecting to the db...")
        with sqlite3.connect('/var/www/rpi_app/rpi_app.db') as conn:
            curs = conn.cursor()
            # insert temperature data
            print("Inserting temperature data into the db...")
            curs.execute("""
                INSERT INTO temperatures (timestamp, sensor_id, temperature)
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, temperature))
            # insert humidity data
            print("Inserting humidity data into the db...")
            curs.execute("""
                INSERT INTO humidities (timestamp, sensor_id, humidities)
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, humidity))
            conn.commit()
        print("Data logged to db.")

        # log data to Google Sheets
        log_to_google_sheet(sensor_id, temperature, humidity, pressure)
    except sqlite3.Error as e:
        print(f"db error: {e}")
    except Exception as e:
        print(f"General error in log_datas: {e}")
        traceback.print_exc()

# HC12 Configuration
ser = serial.Serial(
    port='/dev/serial0',  
    baudrate=9600,
    timeout=None  # wait indefinitely for a line
)

print("Waiting for data...")

while True:
    try:
        # read data from HC12
        line = ser.readline()
        if line:
            print(f"Received raw data: {line}")
            try:
                # decode the message
                decoded_line = line.decode('utf-8', 'ignore').strip()
                print(f"Decoded data: {decoded_line}")

                # split message into parts
                message_parts = decoded_line.split(",")
                print(f"Message parts ({len(message_parts)}): {message_parts}")

                if len(message_parts) == 6:  # ensure the message has all parts
                    timestamp = message_parts[0]
                    temperature = float(message_parts[1])
                    humidity = float(message_parts[2])
                    pressure = float(message_parts[3])
                    sensor_id = message_parts[4]
                    end_marker = message_parts[5]

                    print(f"Parsed Data -> Sensor ID: {sensor_id}, Temp: {temperature}, Hum: {humidity}, Pres: {pressure}")

                    # log the values
                    log_datas(sensor_id, temperature, humidity, pressure)
                else:
                    print(f"Invalid message format: {decoded_line}")
            except ValueError as e:
                print(f"Error parsing data: {e}")
        else:
            print("No data received.")
    except Exception as e:
        print(f"Error reading from HC12: {e}")
        traceback.print_exc()
