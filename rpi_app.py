from flask import Flask, request, render_template
import time
import datetime
import sys
import sqlite3
import Adafruit_DHT

# create an instance of the Flask app
app = Flask(__name__)
app.debug = True  # for debugging purpose

# default route
@app.route("/")
def main_page():
    return "Bienvenue dans l'app de mesure du labo acoustique"

# route that reads temperature and humidity from DHT22
@app.route("/lab_datas")
def lab_datas():
    # read temperature and humidity from DHT22 sensor
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, 17)

    # if valid data is received from the sensor
    if humidity is not None and temperature is not None:
        return render_template("lab_datas.html", temp=temperature, hum=humidity)
    else:
        # if the sensor fails, show a page indicating no sensor data
        return render_template("sensor_error.html")

# route to get datas from the db
@app.route("/lab_datas_db", methods=['GET'])
def lab_datas_db():
    temperatures, humidities, from_date, to_date = get_datas()
    return render_template("lab_datas_db.html", temp=temperatures, hum=humidities)

def get_datas():
    from_date = request.args.get('from', time.strftime("%Y-%m-%d %H:%M:%S")) # Get the from date value from the URL
    to_date = request.args.get('to', time.strftime("%Y-%m-%d %H:%M:%S")) # Get the to date value from the URL

    if not check_date(from_date):  # Validate date before sending it to the DB
        from_date = time.strftime("%Y-%m-%d 00:00:00")
    if not check_date(to_date):
        to_date = time.strftime("%Y-%m-%d %H:%M:%S")  # Validate date before sending it to the DB

    # connect to the db
    conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
    curs = conn.cursor()
    curs.execute("SELECT * FROM temperatures WHERE timestamp BETWEEN ? AND ?", (from_date, to_date))
    temperatures = curs.fetchall()
    curs.execute("SELECT * FROM humidities WHERE timestamp BETWEEN ? AND ?", (from_date, to_date))
    humidities = curs.fetchall()
    conn.close()
    return [temperatures, humidities, from_date, to_date]

def check_date(d):
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False

# to run the app on port 8080
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
