import sqlite3
import smbus2
import bme280
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials

# configuration for BME280 sensor
port = 1
address = 0x76
bus = smbus2.SMBus(port)
calibration_params = bme280.load_calibration_params(bus, address)

# function to add datas to Google Sheets
def log_to_google_sheet(sensor_id, temperature, humidity, pressure):
    try:
        # define the scope and credentials
        print("Configuration des identifiants Google Sheets...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            '/var/www/rpi_app/rpiapp-443210-49cc01bfcf2b.json', scope
        )
        client = gspread.authorize(creds)

        # open the sheet
        print("Ouverture de la feuille Google Sheets...")
        sheet = client.open('Temperature  and Humidity - Rpi').sheet1

        # add the data as a new row
        print("Préparation de la ligne de données...")
        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sensor_id,
            round(temperature, 2),
            round(humidity, 2),
            round(pressure, 2)
        ]
        print(f"Ajout de la ligne : {row}")
        sheet.append_row(row)
        print("Données enregistrées sur Google Sheets.")
    except Exception as e:
        print(f"Erreur lors de l'enregistrement sur Google Sheets : {e}")

# insert data into the database
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
            # insert pressure data
            curs.execute("""
                INSERT INTO pressures (timestamp, sensor_id, pressure)
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, pressure))
            conn.commit()
        print("Données enregistrées dans la base de données.")

        # log datas to Google Sheets
        log_to_google_sheet(sensor_id, temperature, humidity, pressure)
    except sqlite3.Error as e:
        print(f"Erreur dans la base de données : {e}")
    except Exception as e:
        print(f"Erreur générale : {e}")

# reading datas from the sensor
try:
    data = bme280.sample(bus, address, calibration_params)
    temperature = data.temperature
    humidity = data.humidity
    pressure = data.pressure
    # insert data into the db and Google Sheets
    if humidity is not None and temperature is not None and pressure is not None:
        log_datas("1", temperature, humidity, pressure)
    else:
        log_datas("1", -999, -999, -999)
except Exception as e:
    print(f"Erreur lors de la lecture du capteur : {e}")
    log_datas("1", -999, -999, -999)

