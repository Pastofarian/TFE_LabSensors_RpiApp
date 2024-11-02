from flask import Flask, request, render_template
import time
import datetime
import sys
import sqlite3
import arrow
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
    temperatures, humidities, from_date_str, to_date_str = get_datas()
    timezone = request.args.get('timezone', 'Etc/UTC')

    # Adjust user timezone
    time_adjusted_temperatures = []
    time_adjusted_humidities = []
    for record in temperatures:
        # record[0] is timestamp
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
        time_adjusted_temperatures.append([local_timedate.format('DD-MM-YYYY HH:mm:ss'), record[1], record[2]])

    for record in humidities:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
        time_adjusted_humidities.append([local_timedate.format('DD-MM-YYYY HH:mm:ss'), record[1], record[2]])

    return render_template(
        "lab_datas_db.html",
        temp=time_adjusted_temperatures,
        hum=time_adjusted_humidities,
        start_date=from_date_str,
        end_date=to_date_str,
        temp_items=len(temperatures),
        hum_items=len(humidities),
    )


def get_datas():
    from_date_str = request.args.get('from')  # Get the from date value from URL
    to_date_str = request.args.get('to')      # Get the to date value from URL
    timezone = request.args.get('timezone', 'Etc/UTC')
    range_time_form = request.args.get('range_time', '')  # Get 'range_time' from URL

    print("REQUEST:")
    print(request.args)

    try:
        range_time_int = int(range_time_form)
    except ValueError:
        range_time_int = None
        print("range_time_form not valid")

    if range_time_int is not None:
        # If range_time is valid, calculate from_date and to_date using arrow
        arrow_time_to = arrow.utcnow()
        arrow_time_from = arrow_time_to.shift(hours=-range_time_int)
        from_date_utc = arrow_time_from.strftime("%Y-%m-%d %H:%M:%S")
        to_date_utc = arrow_time_to.strftime("%Y-%m-%d %H:%M:%S")
        from_date_str = arrow_time_from.to(timezone).format("DD-MM-YYYY HH:mm:ss")
        to_date_str = arrow_time_to.to(timezone).format("DD-MM-YYYY HH:mm:ss")
    else:
        # If range_time is not valid, use from_date and to_date
        try:
            arrow_from = arrow.get(from_date_str, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
            arrow_to = arrow.get(to_date_str, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
        except Exception as e:
            print(f"Error parsing dates: {e}")
            # If it fails, use default values
            arrow_from = arrow.utcnow().floor('day')
            arrow_to = arrow.utcnow()
            from_date_str = arrow_from.to(timezone).format("DD-MM-YYYY HH:mm:ss")
            to_date_str = arrow_to.to(timezone).format("DD-MM-YYYY HH:mm:ss")

        # Convert in UTC for the queries to the db
        from_date_utc = arrow_from.to('Etc/UTC').format("YYYY-MM-DD HH:mm:ss")
        to_date_utc = arrow_to.to('Etc/UTC').format("YYYY-MM-DD HH:mm:ss")

    print(f"from_date_utc: {from_date_utc}, to_date_utc: {to_date_utc}")

    # DB connection
    conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
    curs = conn.cursor()
    curs.execute("SELECT * FROM temperatures WHERE timestamp BETWEEN ? AND ?", (from_date_utc, to_date_utc))
    temperatures = curs.fetchall()
    curs.execute("SELECT * FROM humidities WHERE timestamp BETWEEN ? AND ?", (from_date_utc, to_date_utc))
    humidities = curs.fetchall()
    conn.close()

    return [temperatures, humidities, from_date_str, to_date_str]

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

