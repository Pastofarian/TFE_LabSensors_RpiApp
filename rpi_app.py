from flask import Flask, request, render_template, abort, jsonify
import datetime
import sqlite3
import arrow
import smbus2
import bme280
import os
from plotly.graph_objs import *
from plotly.offline import plot

port = 1
address = 0x76
bus = smbus2.SMBus(port)
calibration_params = bme280.load_calibration_params(bus, address)

app = Flask(__name__)
app.debug = True

# default interval
selected_interval = "1min"

@app.route("/")
def main_page():
    # return a simple message for the main page
    return "Bienvenue dans l'app de mesure du labo acoustique"

@app.route("/lab_datas")
def lab_datas():
    # get node from query, default '1'
    node = request.args.get('node', '1')
    # if node=1, read sensor directly, else fetch from db
    if node == '1':
        try:
            data = bme280.sample(bus, address, calibration_params)
            temperature = data.temperature
            humidity = data.humidity
            pressure = data.pressure
        except Exception:
            # if sensor reading fails, set values to None
            temperature = None
            humidity = None
            pressure = None
    else:
        # connect to db and fetch last recorded values for this node
        conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
        curs = conn.cursor()
        # fetch most recent temperature
        curs.execute("SELECT * FROM temperatures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (node,))
        temp_data = curs.fetchone()
        # fetch most recent humidity
        curs.execute("SELECT * FROM humidities WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (node,))
        hum_data = curs.fetchone()
        # fetch most recent pressure
        curs.execute("SELECT * FROM pressures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (node,))
        pres_data = curs.fetchone()
        conn.close()

        if temp_data and hum_data and pres_data:
            # if all three values found, assign them
            temperature = temp_data[2]
            humidity = hum_data[2]
            pressure = pres_data[2]
        else:
            # no data found for this node
            temperature = None
            humidity = None
            pressure = None

    # render template with the obtained values
    return render_template("lab_datas.html", temp=temperature, hum=humidity, pres=pressure, node=node)

@app.route("/lab_datas_db", methods=['GET'])
def lab_datas_db():
    global selected_interval
    try:
        # get all data based on request parameters
        temperatures, humidities, pressures, timezone, from_date, to_date, node = get_datas()
    except Exception as e:
        print(f"Error in lab_datas_db: {e}")
        abort(500)

    # get range_time from query, default 24h if not provided
    range_time = request.args.get('range_time', '24')
    # if a valid integer, recalculate from/to dates
    if range_time.isdigit():
        range_time_int = int(range_time)
        now = arrow.now(timezone)
        from_date = now.shift(hours=-range_time_int).format("YYYY-MM-DD HH:mm:ss")
        to_date = now.format("YYYY-MM-DD HH:mm:ss")

    time_adjusted_temperatures = []
    time_adjusted_humidities = []
    time_adjusted_pressures = []

    # convert timestamps to local time and store them
    for record in temperatures:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss", tzinfo=timezone)
        time_adjusted_temperatures.append([local_timedate.format('DD-MM-YYYY HH:mm:ss'), record[1], record[2]])

    for record in humidities:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss", tzinfo=timezone)
        time_adjusted_humidities.append([local_timedate.format('DD-MM-YYYY HH:mm:ss'), record[1], record[2]])

    for record in pressures:
        local_timedate = arrow.get(record[0], "YYYY-MM-DD HH:mm:ss", tzinfo=timezone)
        time_adjusted_pressures.append([local_timedate.format('DD-MM-YYYY HH:mm:ss'), record[1], record[2]])

    # create a combined_data structure for the template
    combined_data = []
    for t_row, h_row, p_row in zip(time_adjusted_temperatures, time_adjusted_humidities, time_adjusted_pressures):
        combined_data.append({
            'date': t_row[0],
            'temp': round(t_row[2], 1),
            'humidity': round(h_row[2], 1),
            'pressure': round(p_row[2], 2)
        })

    # render template with adjusted and combined data
    return render_template(
        "lab_datas_db.html",
        temp=time_adjusted_temperatures,
        hum=time_adjusted_humidities,
        press=time_adjusted_pressures,
        combined_data=combined_data,
        start_date=from_date,
        end_date=to_date,
        range_time=range_time,
        temp_items=len(temperatures),
        hum_items=len(humidities),
        press_items=len(pressures),
        node=node,
        timezone=timezone,
        selected_interval=selected_interval
    )

def get_datas():
    # get parameters from query
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    timezone = request.args.get('timezone', 'Europe/Brussels')
    range_time_form = request.args.get('range_time', '')
    node = request.args.get('node', '1')

    # if from/to not provided, use last 24h as default
    if not from_date:
        from_date = arrow.now(timezone).shift(days=-1).format("DD-MM-YYYY HH:mm:ss")
    if not to_date:
        to_date = arrow.now(timezone).format("DD-MM-YYYY HH:mm:ss")

    # try to parse range_time_form
    try:
        range_time_int = int(range_time_form)
    except ValueError:
        range_time_int = None
        print("range_time_form not valid")

    # if a valid range_time_int, recalculate from/to based on it
    if range_time_int is not None:
        arrow_time_to = arrow.now(timezone)
        arrow_time_from = arrow_time_to.shift(hours=-range_time_int)
        from_date_str = arrow_time_from.format("YYYY-MM-DD HH:mm:ss")
        to_date_str = arrow_time_to.format("YYYY-MM-DD HH:mm:ss")
    else:
        # if not valid range_time, parse from_date/to_date directly
        try:
            arrow_from = arrow.get(from_date, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
            arrow_to = arrow.get(to_date, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
        except Exception as e:
            print(f"Error parsing dates: {e}")
            arrow_from = arrow.now(timezone).floor('day')
            arrow_to = arrow.now(timezone)

        from_date_str = arrow_from.format("YYYY-MM-DD HH:mm:ss")
        to_date_str = arrow_to.format("YYYY-MM-DD HH:mm:ss")

    # connect to db and fetch data based on node and date range
    conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
    curs = conn.cursor()

    # fetch temperatures
    curs.execute("SELECT * FROM temperatures WHERE timestamp BETWEEN ? AND ? AND sensor_id = ?", (from_date_str, to_date_str, node))
    temperatures = curs.fetchall()

    # fetch humidities
    curs.execute("SELECT * FROM humidities WHERE timestamp BETWEEN ? AND ? AND sensor_id = ?", (from_date_str, to_date_str, node))
    humidities = curs.fetchall()

    # fetch pressures
    curs.execute("SELECT * FROM pressures WHERE timestamp BETWEEN ? AND ? AND sensor_id = ?", (from_date_str, to_date_str, node))
    pressures = curs.fetchall()

    conn.close()

    # return all retrieved data and parameters
    return [temperatures, humidities, pressures, timezone, from_date, to_date, node]

@app.route("/to_plotly", methods=['GET'])
def to_plotly_offline():
    try:
        # get data needed for plotly chart
        temperatures, humidities, pressures, timezone, from_date, to_date, node = get_datas()
    except Exception as e:
        print(f"Error generating plot: {e}")
        abort(500)

    # extract time series and values
    time_series_temperature = [record[0] for record in temperatures]
    temperature_values = [round(record[2], 2) for record in temperatures]

    time_series_humidity = [record[0] for record in humidities]
    humidity_values = [round(record[2], 2) for record in humidities]

    time_series_pressure = [record[0] for record in pressures]
    pressure_values = [round(record[2], 2) for record in pressures]

    # create scatter plots for each metric
    temp = Scatter(x=time_series_temperature, y=temperature_values, name='Température')
    hum = Scatter(x=time_series_humidity, y=humidity_values, name='Humidité', yaxis='y2')
    press = Scatter(x=time_series_pressure, y=pressure_values, name='Pression', yaxis='y3')

    data = [temp, hum, press]

    # define layout with multiple y-axis
    layout = Layout(
        title=f"Température, Humidité et Pression - Cellule {node}",
        xaxis=dict(title="Date"),
        yaxis=dict(title="Température (°C)"),
        yaxis2=dict(title="Humidité (%)", overlaying="y", side="right"),
        yaxis3=dict(
            title="Pression (Pa)",
            overlaying="y",
            side="right",
            anchor="free",
            position=0.95
        )
    )

    # generate plotly html file
    fig = dict(data=data, layout=layout)
    html_file_path = '/var/www/rpi_app/static/plotly_graph.html'
    plot(fig, filename=html_file_path, auto_open=False)

    # return the path to the plotly file
    return f"/static/plotly_graph.html"

@app.route("/update_cron", methods=['POST'])
def update_cron():
    global selected_interval
    # get new interval from form
    new_interval = request.form.get('interval')
    if new_interval:
        selected_interval = new_interval
        # mapping intervals to cron syntax
        interval_mapping = {
            "1min": "* * * * *",
            "3min": "*/3 * * * *",
            "5min": "*/5 * * * *",
            "10min": "*/10 * * * *",
            "30min": "*/30 * * * *",
            "60min": "0 * * * *"
        }

        cron_line = interval_mapping.get(new_interval, "* * * * *")
        command = "/var/www/rpi_app/bin/python /var/www/rpi_app/lab_datas.py"

        # write updated cron job
        cron_content = f"{cron_line} {command}\n"
        with open("/tmp/my_cron_file", "w") as f:
            f.write(cron_content)
        os.system("crontab /tmp/my_cron_file")

        # return json response with new cron
        return jsonify({"status": "ok", "selected_interval": selected_interval, "applied_cron": cron_content})
    else:
        # if no interval provided in request
        return jsonify({"status": "error", "message": "No interval provided"}), 400

def check_date(d):
    # check if the date string is in correct format
    if not d:
        return False
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
        return True
    except (ValueError, TypeError):
        return False

if __name__ == "__main__":
    # run the flask app on specified host and port
    app.run(host='0.0.0.0', port=8080)

