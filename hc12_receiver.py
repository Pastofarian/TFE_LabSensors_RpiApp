import serial
import sqlite3
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# hc12 configuration
ser = serial.Serial(
    port='/dev/serial0',
    baudrate=9600,
    timeout=None  # wait until I get datas
)

print("en attente de données...")

def log_to_google_sheet(sensor_id, temperature, humidity, pressure):
    try:
        print("configuration des identifiants Google Sheets...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            '/var/www/rpi_app/rpiapp-443210-49cc01bfcf2b.json', scope
        )
        client = gspread.authorize(creds)

        # open the Google Sheet
        print("ouverture de la feuille Google Sheets...")
        sheet = client.open('Temperature  and Humidity - Rpi').sheet1

        # add the data as a new row
        print("préparation de la ligne de données...")
        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sensor_id,
            round(temperature, 2),
            round(humidity, 2),
            round(pressure, 2)
        ]
        print(f"ajout de la ligne : {row}")
        sheet.append_row(row)
        print("données enregistrées sur Google Sheets.")
    except Exception as e:
        print(f"erreur lors de l'enregistrement sur Google Sheets : {e}")

def log_datas(sensor_id, temperature, humidity, pressure):
    try:
        with sqlite3.connect('/var/www/rpi_app/rpi_app.db') as conn:
            curs = conn.cursor()
            # insert temperature data
            curs.execute("""
                INSERT INTO temperatures (timestamp, sensor_id, temperature)
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, temperature))
            # insert humidity data
            curs.execute("""
                INSERT INTO humidities (timestamp, sensor_id, humidities)
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, humidity))
            conn.commit()
        print("données enregistrées dans la base.")

        # log data to Google Sheets
        log_to_google_sheet(sensor_id, temperature, humidity, pressure)
    except sqlite3.Error as e:
        print(f"erreur base de données : {e}")
    except Exception as e:
        print(f"erreur générale : {e}")

while True:
    try:
        # read data from HC12
        line = ser.readline()
        if line:
            print(f"données brutes reçues : {line}")
            decoded_line = line.decode('utf-8', 'ignore').strip()
            print(f"données décodées : {decoded_line}")

            # split message into parts
            message_parts = decoded_line.split(",")
            print(f"parties du message ({len(message_parts)}) : {message_parts}")

            if len(message_parts) == 6:
                timestamp = message_parts[0]
                temperature = float(message_parts[1])
                humidity = float(message_parts[2])
                pressure = float(message_parts[3])
                sensor_id = message_parts[4]
                end_marker = message_parts[5]

                print(f"données extraites -> id capteur : {sensor_id}, temp : {temperature}, hum : {humidity}, pres : {pressure}")

                # log the values
                log_datas(sensor_id, temperature, humidity, pressure)
            else:
                print(f"format de message invalide : {decoded_line}")
        else:
            print("aucune donnée reçue.")
    except Exception as e:
        print(f"erreur lors de la lecture depuis HC12 : {e}")

