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

# route live temp and hum
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

# route to get data from the db
@app.route("/lab_datas_db", methods=['GET'])
def lab_datas_db():
    temperatures, humidities, from_date, to_date = get_datas()
    return render_template(
        "lab_datas_db.html",
        temp=temperatures,
        hum=humidities,
        start_date=from_date,
        end_date=to_date,
        temp_items=len(temperatures),
        hum_items=len(humidities),
    )

def get_datas():
    from_date = request.args.get('from')  # Get the from date value from URL
    to_date = request.args.get('to')      # Get the to date value from URL
    range_time_form = request.args.get('range_time', '')  # Get 'range_time' from URL

    try:
        range_time_int = int(range_time_form)
    except ValueError:
        range_time_int = None
        print("range_time_form not valid")
        
    if range_time_int is not None:
        # if range_time is valid, calculate from_date and to_date
        time_now = datetime.datetime.now()
        time_from = time_now - datetime.timedelta(hours=range_time_int)
        from_date = time_from.strftime("%Y-%m-%d %H:%M:%S")
        to_date = time_now.strftime("%Y-%m-%d %H:%M:%S")
    else:
    # If range_time is not valid, I use the default dates
        if not check_date(from_date):
            from_date = time.strftime("%Y-%m-%d 00:00:00")  # Start at the beginning of the day
        if not check_date(to_date):
            to_date = time.strftime("%Y-%m-%d %H:%M:%S")    # Until now
            
    print(f"from_date: {from_date}, to_date: {to_date}")

    # if isinstance(range_time_int, int):
    #     time_now = datetime.datetime.now()
    #     time_from = time_now - datetime.timedelta(hours=range_time_int)
    #     time_to = time_now
    #     from_date = time_from.strftime("%Y-%m-%d %H:%M:%S")
    #     to_date = time_to.strftime("%Y-%m-%d %H:%M:%S")

    # Connect to the db
    conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
    curs = conn.cursor()
    curs.execute("SELECT * FROM temperatures WHERE timestamp BETWEEN ? AND ?", (from_date, to_date))
    temperatures = curs.fetchall()
    curs.execute("SELECT * FROM humidities WHERE timestamp BETWEEN ? AND ?", (from_date, to_date))
    humidities = curs.fetchall()
    conn.close()
    return [temperatures, humidities, from_date, to_date]

def check_date(d):
    if not d:
        return False
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
        return True
    except (ValueError, TypeError):
        return False
    
# to run the app on port 8080
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

