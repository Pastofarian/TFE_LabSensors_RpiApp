import sqlite3
import Adafruit_DHT

# Function to log temperature and humidity data into the database
def log_datas(sensor_id, temperature, humidity):
    try:
        # Use 'with' to ensure the connection is properly closed after use
        with sqlite3.connect('/var/www/rpi_app/rpi_app.db') as conn:
            curs = conn.cursor()
            # Insert temperature data
            curs.execute("""
                INSERT INTO temperatures (timestamp, sensor_id, temperature) 
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, temperature))
            # Insert humidity data
            curs.execute("""
                INSERT INTO humidities (timestamp, sensor_id, humidities) 
                VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)
            """, (sensor_id, humidity))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"General error: {e}")

# Read from the sensor
humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, 17)

# Log the data, using -999 as a placeholder for failed readings
if humidity is not None and temperature is not None:
    log_datas("1", temperature, humidity)
else:
    log_datas("1", -999, -999)
