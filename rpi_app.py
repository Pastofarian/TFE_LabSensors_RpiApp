from flask import Flask, request, render_template, abort
import time
import datetime
import sys
import sqlite3
import arrow
import Adafruit_DHT
import plotly.plotly as py
from plotly.offline import plot
from plotly.graph_objs import Scatter, Data, Layout, Figure, XAxis, YAxis

# create instance of the Flask app
app = Flask(__name__)
app.debug = True  # for debugging purpose, disable this in production

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
    try:
        temperatures, humidities, timezone, from_date, to_date = get_datas()
    except Exception as e:
        print(f"Error in lab_datas_db: {e}")
        abort(500)  # return 500 error if something goes wrong
    
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
        start_date=from_date,
        end_date=to_date,
        temp_items=len(temperatures),
        hum_items=len(humidities),
    )

def get_datas():
    # fetch data range from request args
    from_date = request.args.get('from') # Get the from date value from URL
    to_date = request.args.get('to') # Get the to date value from URL
    timezone = request.args.get('timezone', 'Etc/UTC')
    range_time_form = request.args.get('range_time', '')  # optional range time param

    # check default value
    if not from_date:
        from_date = arrow.utcnow().shift(days=-1).format("DD-MM-YYYY HH:mm:ss")

    if not to_date:
        to_date = arrow.utcnow().format("DD-MM-YYYY HH:mm:ss")

    print("REQUEST:")
    print(request.args)
    print ("from: %s, to: %s, timezone: %s" % (from_date, to_date, timezone))

    # convert range_time safely
    try:
        range_time_int = int(range_time_form)
    except ValueError:
        range_time_int = None
        print("range_time_form not valid")

    if range_time_int is not None:
        # Calculate from and to date based on range_time using arrow
        arrow_time_to = arrow.utcnow()
        arrow_time_from = arrow_time_to.shift(hours=-range_time_int)
        from_date_utc = arrow_time_from.strftime("%Y-%m-%d %H:%M:%S")
        to_date_utc = arrow_time_to.strftime("%Y-%m-%d %H:%M:%S")
    else:
        try:
            # parse and adjust user-provided dates
            arrow_from = arrow.get(from_date, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
            arrow_to = arrow.get(to_date, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
        except Exception as e:
            print(f"Error parsing dates: {e}")
            arrow_from = arrow.utcnow().floor('day')  # default to start of current day
            arrow_to = arrow.utcnow()  # default to current time

        from_date_utc = arrow_from.to('Etc/UTC').format("YYYY-MM-DD HH:mm:ss")
        to_date_utc = arrow_to.to('Etc/UTC').format("YYYY-MM-DD HH:mm:ss")

    # db connection
    conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
    curs = conn.cursor()
    curs.execute("SELECT * FROM temperatures WHERE timestamp BETWEEN ? AND ?", (from_date_utc, to_date_utc))
    temperatures = curs.fetchall()
    curs.execute("SELECT * FROM humidities WHERE timestamp BETWEEN ? AND ?", (from_date_utc, to_date_utc))
    humidities = curs.fetchall()
    conn.close()

    # return all necessary data to the caller
    return [temperatures, humidities, timezone, from_date, to_date]

@app.route("/to_plotly", methods=['GET'])
def to_plotly_offline():
    try:
        # fetch data required for Plotly
        temperatures, humidities, timezone, from_date, to_date = get_datas()
    except Exception as e:
        print(f"Error generating plot: {e}")
        abort(500)  # return 500 error if data fetch fails

    # initialize lists for time series data
    time_series_adjusted_temperatures = []
    time_series_temperature_values = []
    time_series_adjusted_humidities = []
    time_series_humidity_values = []

    # process temperature records, adjust timestamps to user timezone
    for record in temperatures:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
        time_series_adjusted_temperatures.append(local_timedate.format('YYYY-MM-DD HH:mm:ss'))
        time_series_temperature_values.append(round(record[2], 2))

    # process humidity records, adjust timestamps to user timezone
    for record in humidities:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss").to(timezone)
        time_series_adjusted_humidities.append(local_timedate.format('YYYY-MM-DD HH:mm:ss'))
        time_series_humidity_values.append(round(record[2], 2))

    # create Scatter objects for temperature and humidity
    temp = Scatter(x=time_series_adjusted_temperatures, y=time_series_temperature_values, name='Température')
    hum = Scatter(x=time_series_adjusted_humidities, y=time_series_humidity_values, name='Humidité', yaxis='y2')

    data = [temp, hum]  # combine data 

    # layout for the plot
    layout = Layout(
        title="Température et Humidité",
        xaxis=dict(title='Date'),
        yaxis=dict(title='Température (°C)'),
        yaxis2=dict(title='Humidité (%)', overlaying='y', side='right')
    )

    fig = dict(data=data, layout=layout)  # prepare figure for rendering

    # save html locally for display
    html_file_path = '/var/www/rpi_app/static/plotly_graph.html'
    plot(fig, filename=html_file_path, auto_open=False)

    # return the path to the generated html file
    return f"/static/plotly_graph.html"

def check_date(d):
    if not d:
        return False
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
        return True
    except (ValueError, TypeError):
        return False

# run the app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

