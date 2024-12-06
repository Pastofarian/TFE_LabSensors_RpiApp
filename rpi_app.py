from flask import Flask, request, render_template, abort
import time
import datetime
import sys
import sqlite3
import arrow
import smbus2
import bme280
from plotly.graph_objs import *
from plotly.offline import plot

port = 1
address = 0x76
bus = smbus2.SMBus(port)

calibration_params = bme280.load_calibration_params(bus, address)

# create instance of the Flask app
app = Flask(__name__)
app.debug = True  # for debugging purpose, disable this in production

# default route
@app.route("/")
def main_page():
    return "Bienvenue dans l'app de mesure du labo acoustique"

@app.route("/lab_datas")
def lab_datas():
    data = bme280.sample(bus, address, calibration_params)
    temperature = data.temperature
    humidity = data.humidity
    pressure = data.pressure  
    
    # if valid data is received from the sensor
    if humidity is not None and temperature is not None and pressure is not None:
        return render_template("lab_datas.html", temp=temperature, hum=humidity, pres=pressure)  
    else:
        # if the sensor fails, show a page indicating no sensor data
        return render_template("sensor_error.html")

@app.route("/lab_datas_db", methods=['GET'])
def lab_datas_db():
    try:
        temperatures, humidities, pressures, timezone, from_date, to_date = get_datas()
    except Exception as e:
        print(f"Error in lab_datas_db: {e}")
        abort(500)

    range_time = request.args.get('range_time', '24')  # default 24h range time

    # automatic calculation of date range if I get range_time
    if range_time.isdigit():
        range_time_int = int(range_time)
        now = arrow.now(timezone)
        from_date = now.shift(hours=-range_time_int).format("YYYY-MM-DD HH:mm:ss")
        to_date = now.format("YYYY-MM-DD HH:mm:ss")

    # time zone 
    time_adjusted_temperatures = []
    time_adjusted_humidities = []
    time_adjusted_pressures = []

    for record in temperatures:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss", tzinfo=timezone)
        time_adjusted_temperatures.append([local_timedate.format('DD-MM-YYYY HH:mm:ss'), record[1], record[2]])

    for record in humidities:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss", tzinfo=timezone)
        time_adjusted_humidities.append([local_timedate.format('DD-MM-YYYY HH:mm:ss'), record[1], record[2]])

    for record in pressures:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss", tzinfo=timezone)
        time_adjusted_pressures.append([local_timedate.format('DD-MM-YYYY HH:mm:ss'), record[1], record[2]])

    return render_template(
        "lab_datas_db.html",
        temp=time_adjusted_temperatures,
        hum=time_adjusted_humidities,
        press=time_adjusted_pressures,
        start_date=from_date,
        end_date=to_date,
        range_time=range_time,  # transmit range time
        temp_items=len(temperatures),
        hum_items=len(humidities),
        press_items=len(pressures)
    )

def get_datas():
    from_date = request.args.get('from')  # 'from' parameter from URL
    to_date = request.args.get('to')      # 'to' parameter from URL
    timezone = request.args.get('timezone', 'Europe/Brussels')
    range_time_form = request.args.get('range_time', '')  # optional range_time parameter

    if not from_date:
        from_date = arrow.now(timezone).shift(days=-1).format("DD-MM-YYYY HH:mm:ss")

    if not to_date:
        to_date = arrow.now(timezone).format("DD-MM-YYYY HH:mm:ss")

    print("REQUEST:")
    print(request.args)
    print("from: %s, to: %s, timezone: %s" % (from_date, to_date, timezone))

    try:
        range_time_int = int(range_time_form)
    except ValueError:
        range_time_int = None
        print("range_time_form not valid")

    if range_time_int is not None:
        arrow_time_to = arrow.now(timezone)
        arrow_time_from = arrow_time_to.shift(hours=-range_time_int)
        from_date_str = arrow_time_from.format("YYYY-MM-DD HH:mm:ss")
        to_date_str = arrow_time_to.format("YYYY-MM-DD HH:mm:ss")
    else:
        try:
            arrow_from = arrow.get(from_date, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
            arrow_to = arrow.get(to_date, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
        except Exception as e:
            print(f"Error parsing dates: {e}")
            arrow_from = arrow.now(timezone).floor('day')
            arrow_to = arrow.now(timezone)

        from_date_str = arrow_from.format("YYYY-MM-DD HH:mm:ss")
        to_date_str = arrow_to.format("YYYY-MM-DD HH:mm:ss")

    conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
    curs = conn.cursor()
    curs.execute("SELECT * FROM temperatures WHERE timestamp BETWEEN ? AND ?", (from_date_str, to_date_str))
    temperatures = curs.fetchall()
    curs.execute("SELECT * FROM humidities WHERE timestamp BETWEEN ? AND ?", (from_date_str, to_date_str))
    humidities = curs.fetchall()
    curs.execute("SELECT * FROM pressures WHERE timestamp BETWEEN ? AND ?", (from_date_str, to_date_str))
    pressures = curs.fetchall()

    conn.close()

    return [temperatures, humidities, pressures, timezone, from_date, to_date]

@app.route("/to_plotly", methods=['GET'])
def to_plotly_offline():
    try:
        temperatures, humidities, pressures, timezone, from_date, to_date = get_datas()
    except Exception as e:
        print(f"Error generating plot: {e}")
        abort(500)

    time_series_temperature = [arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone).format('YYYY-MM-DD HH:mm:ss') for record in temperatures]
    temperature_values = [round(record[2], 2) for record in temperatures]

    time_series_humidity = [arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone).format('YYYY-MM-DD HH:mm:ss') for record in humidities]
    humidity_values = [round(record[2], 2) for record in humidities]

    temp = Scatter(x=time_series_temperature, y=temperature_values, name='Température')
    hum = Scatter(x=time_series_humidity, y=humidity_values, name='Humidité', yaxis='y2')

    data = [temp, hum]

    layout = Layout(
        title="Température et Humidité",
        xaxis=dict(title="Date"),
        yaxis=dict(title="Température (°C)"),
        yaxis2=dict(title="Humidité (%)", overlaying="y", side="right")
    )

    fig = dict(data=data, layout=layout)
    html_file_path = '/var/www/rpi_app/static/plotly_graph.html'
    plot(fig, filename=html_file_path, auto_open=False)

    return f"/static/plotly_graph.html"

def check_date(d):
    if not d:
        return False
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
        return True
    except (ValueError, TypeError):
        return False

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

