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
def log_to_google_sheet(sensor_id, temperature, humidity):
    try:
        # define the scope and credentials
        print("Setting up Google Sheets credentials...")
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            '/var/www/rpi_app/rpiapp-443210-49cc01bfcf2b.json', scope
        )
        client = gspread.authorize(creds)

        # open the sheet
        print("Opening Google Sheet...")
        sheet = client.open('Temperature  and Humidity - Rpi').sheet1

        # add the data as a new row
        print("Preparing data row...")
        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            sensor_id,
            round(temperature, 2),
            round(humidity, 2),
        ]
        print(f"Appending row: {row}")
        sheet.append_row(row)
        print("Data logged to Google Sheets.")
    except Exception as e:
        print(f"Error logging to Google Sheets: {e}")


# insert data into the database
def log_datas(sensor_id, temperature, humidity):
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
        print("Data logged to database.")

        # log datas to Google Sheets
        log_to_google_sheet(sensor_id, temperature, humidity)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"General error: {e}")

# reading datas from the sensor
try:
    data = bme280.sample(bus, address, calibration_params)
    temperature = data.temperature
    humidity = data.humidity
    # insert data into the db and Google Sheets
    if humidity is not None and temperature is not None:
        log_datas("1", temperature, humidity)
    else:
        log_datas("1", -999, -999)
except Exception as e:
    print(f"Error reading from sensor: {e}")
    log_datas("1", -999, -999)

