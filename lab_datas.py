import sqlite3
import smbus2
import bme280

# configuration for BME280 sensor
port = 1
address = 0x76
bus = smbus2.SMBus(port)
calibration_params = bme280.load_calibration_params(bus, address)

# insert data into the database
def log_datas(sensor_id, temperature, humidity):
    try:
        with sqlite3.connect('/var/www/rpi_app/rpi_app.db') as conn:
            curs = conn.cursor()
            # insert temperature datas
            curs.execute("""
                INSERT INTO temperatures (timestamp, sensor_id, temperature)
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, temperature))
            # insert humidity datas
            curs.execute("""
                INSERT INTO humidities (timestamp, sensor_id, humidities)
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, humidity))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"General error: {e}")

# reading datas from the sensor
try:
    data = bme280.sample(bus, address, calibration_params)
    temperature = data.temperature
    humidity = data.humidity
    # insert datas into the db
    if humidity is not None and temperature is not None:
        log_datas("1", temperature, humidity)
    else:
        log_datas("1", -999, -999)
except Exception as e:
    print(f"Error reading from sensor: {e}")
    log_datas("1", -999, -999)

