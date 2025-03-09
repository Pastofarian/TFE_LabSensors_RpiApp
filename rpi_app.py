
from flask import Flask, request, render_template, abort, jsonify
import datetime
import sqlite3
import arrow
import smbus2
import bme280
import os
from plotly.graph_objs import Scatter, Layout
from plotly.offline import plot
import gspread
import sys
from oauth2client.service_account import ServiceAccountCredentials

# manage sensor reading from bme280
class SensorReader:
    def __init__(self):
        self.port = 1
        self.address = 0x76
        self.bus = smbus2.SMBus(self.port)
        # load calibration parameters for bme280
        self.calibration_params = bme280.load_calibration_params(self.bus, self.address)
        # read actual sensor values
    def read_sensor(self):
        data = bme280.sample(self.bus, self.address, self.calibration_params)
        return {"temperature": data.temperature, "humidity": data.humidity, "pressure": data.pressure}

# manage db connections and queries
class DatabaseManager:
    def __init__(self):
        self.db_path = '/var/www/rpi_app/rpi_app.db'
        
        # get last recorded values for a sensor
    def fetch_latest(self, sensor_id):
        conn = sqlite3.connect(self.db_path)
        curs = conn.cursor()
        curs.execute("SELECT * FROM temperatures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (sensor_id,))
        temp_data = curs.fetchone()
        curs.execute("SELECT * FROM humidities WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (sensor_id,))
        hum_data = curs.fetchone()
        curs.execute("SELECT * FROM pressures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (sensor_id,))
        pres_data = curs.fetchone()
        conn.close()
        if temp_data and hum_data and pres_data:
            return {"temperature": temp_data[2], "humidity": hum_data[2], "pressure": pres_data[2]}
        return {"temperature": None, "humidity": None, "pressure": None}
    
    # get historical data for a choosen sensor and date range
    def fetch_data(self, sensor_id, from_date, to_date):
        conn = sqlite3.connect(self.db_path)
        curs = conn.cursor()
        curs.execute("SELECT * FROM temperatures WHERE timestamp BETWEEN ? AND ? AND sensor_id = ?", (from_date, to_date, sensor_id))
        temperatures = curs.fetchall()
        curs.execute("SELECT * FROM humidities WHERE timestamp BETWEEN ? AND ? AND sensor_id = ?", (from_date, to_date, sensor_id))
        humidities = curs.fetchall()
        curs.execute("SELECT * FROM pressures WHERE timestamp BETWEEN ? AND ? AND sensor_id = ?", (from_date, to_date, sensor_id))
        pressures = curs.fetchall()
        conn.close()
        return temperatures, humidities, pressures
     # insert current sensor data into the db
    def insert_data(self, sensor_id, temperature, humidity, pressure):
        conn = sqlite3.connect(self.db_path)
        curs = conn.cursor()
        curs.execute("INSERT INTO temperatures (timestamp, sensor_id, temperature) VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)", (sensor_id, temperature))
        curs.execute("INSERT INTO humidities (timestamp, sensor_id, humidities) VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)", (sensor_id, humidity))
        curs.execute("INSERT INTO pressures (timestamp, sensor_id, pressure) VALUES (datetime(CURRENT_TIMESTAMP, 'localtime'), ?, ?)", (sensor_id, pressure))
        conn.commit()
        conn.close()

# log to google sheets
class GoogleSheetsLogger:
    def __init__(self):
        self.credentials_file = os.environ.get("GOOGLE_CREDENTIALS_PATH")
        if not self.credentials_file:
            raise ValueError(
                "La variable d'environnement GOOGLE_CREDENTIALS_PATH "
                "n'est pas définie."
            )  
    # add sensor data to google sheet
    def log(self, sensor_id, temperature, humidity, pressure):
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, scope)
            client = gspread.authorize(creds)
            sheet = client.open('Temperature  and Humidity - Rpi').sheet1
            row = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sensor_id, round(temperature, 2), round(humidity, 2), round(pressure, 2)]
            sheet.append_row(row)
        except Exception:
            pass

# read from sensor, write to db, and log to sheets
class DataLogger:
    def __init__(self, sensor_reader, db_manager, sheets_logger):
        self.sensor_reader = sensor_reader
        self.db_manager = db_manager
        self.sheets_logger = sheets_logger
    # get sensor data, manage errors, store data and log it
    def log_all(self, sensor_id):
        try:
            data = self.sensor_reader.read_sensor()
            temperature = data.get("temperature")
            humidity = data.get("humidity")
            pressure = data.get("pressure")
        except Exception:
            temperature = humidity = pressure = None
        # if sensor fails, mark values as -999
        if temperature is None or humidity is None or pressure is None:
            temperature = humidity = pressure = -999
        self.db_manager.insert_data(sensor_id, temperature, humidity, pressure)
        self.sheets_logger.log(sensor_id, temperature, humidity, pressure)

# creates plotly graph for sensor data
class PlotlyGenerator:
    def generate_plot(self, temperatures, humidities, pressures, node):
        # extract time series and values
        time_series_temp = [record[0] for record in temperatures]
        temperature_values = [round(record[2], 2) for record in temperatures]
        time_series_hum = [record[0] for record in humidities]
        humidity_values = [round(record[2], 2) for record in humidities]
        time_series_pres = [record[0] for record in pressures]
        pressure_values = [round(record[2], 2) for record in pressures]
        
        # define traces
        temp = Scatter(x=time_series_temp, y=temperature_values, name='Température')
        hum = Scatter(x=time_series_hum, y=humidity_values, name='Humidité', yaxis='y2')
        press = Scatter(x=time_series_pres, y=pressure_values, name='Pression', yaxis='y3')
        data = [temp, hum, press]
        layout = Layout(title="Température, Humidité et Pression - Cellule " + str(node), xaxis=dict(title="Date"), yaxis=dict(title="Température (°C)"), yaxis2=dict(title="Humidité (%)", overlaying="y", side="right"), yaxis3=dict(title="Pression (Pa)", overlaying="y", side="right", anchor="free", position=0.95))
        fig = dict(data=data, layout=layout)
        html_file_path = '/var/www/rpi_app/static/plotly_graph.html'
        plot(fig, filename=html_file_path, auto_open=False)
        return "/static/plotly_graph.html"

# cron job 
class CronManager:
    def __init__(self):
        # default interval
        self.selected_interval = "30min"
        self.interval_mapping = {
            "1min": "* * * * *",
            "3min": "*/3 * * * *",
            "5min": "*/5 * * * *",
            "10min": "*/10 * * * *",
            "30min": "*/30 * * * *",
            "60min": "0 * * * *"
        }
        
    # update cron interval based on user selection
    def update_interval(self, new_interval):
        if new_interval in self.interval_mapping:
            self.selected_interval = new_interval
            cron_line = self.interval_mapping[new_interval]
        else:
            cron_line = self.interval_mapping["1min"]
            self.selected_interval = "1min"
        command = "/var/www/rpi_app/bin/python /var/www/rpi_app/lab_datas.py"
        cron_content = f"{cron_line} {command}\n"
        
        # write cron config to file and load with crontab
        with open("/tmp/my_cron_file", "w") as f:
            f.write(cron_content)
        os.system("crontab /tmp/my_cron_file")
        return cron_content

# main flask app manage routes and logic
class RpiBackend:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.debug = True
        
        # instantiate required components
        self.sensor_reader = SensorReader()
        self.db_manager = DatabaseManager()
        self.sheets_logger = GoogleSheetsLogger()
        self.data_logger = DataLogger(self.sensor_reader, self.db_manager, self.sheets_logger)
        self.cron_manager = CronManager()
        self.plotly_generator = PlotlyGenerator()
        
        # set up routes and error handlers
        self.register_routes()
        self.register_error_handlers()
    def register_routes(self):
        @self.app.route("/")
        def main_page():
            return "Bienvenue dans l'app de mesure du labo acoustique"
        
        # display current sensor data or latest data from db
        @self.app.route("/lab_datas")
        def lab_datas():
            node = request.args.get('node', '7')
            if node == '7':
                try:
                    data = self.sensor_reader.read_sensor()
                    temperature = data.get("temperature")
                    humidity = data.get("humidity")
                    pressure = data.get("pressure")
                except Exception:
                    temperature = humidity = pressure = None
            else:
                result = self.db_manager.fetch_latest(node)
                temperature = result.get("temperature")
                humidity = result.get("humidity")
                pressure = result.get("pressure")
            return render_template("lab_datas.html", temp=temperature, hum=humidity, pres=pressure, node=node)
        
        # display historical data with optional time range
        @self.app.route("/lab_datas_db")
        def lab_datas_db():
            try:
                temperatures, humidities, pressures, timezone, from_date, to_date, node = self.get_datas()
            except Exception as e:
                print(f"Error in lab_datas_db: {e}")
                abort(500)
            range_time = request.args.get('range_time', '')
            # calculate from_date/to_date if not specified
            if (not from_date or not to_date) and range_time.isdigit():
                range_time_int = int(range_time)
                now = arrow.now(timezone)
                from_date = now.shift(hours=-range_time_int).format("YYYY-MM-DD HH:mm:ss")
                to_date = now.format("YYYY-MM-DD HH:mm:ss")
            elif not from_date or not to_date:
                now = arrow.now(timezone)
                from_date = now.shift(hours=-24).format("YYYY-MM-DD HH:mm:ss")
                to_date = now.format("YYYY-MM-DD HH:mm:ss")
                
            # convert timestamps to local time strings    
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
                
            # combine data for stats    
            combined_data = []
            for t_row, h_row, p_row in zip(time_adjusted_temperatures, time_adjusted_humidities, time_adjusted_pressures):
                combined_data.append({'date': t_row[0], 'temp': round(t_row[2], 1), 'humidity': round(h_row[2], 1), 'pressure': round(p_row[2], 2)})
            
            # calculate min, max, and avg if I have data    
            if len(combined_data) > 0:
                temp_values = [d['temp'] for d in combined_data]
                hum_values = [d['humidity'] for d in combined_data]
                press_values = [d['pressure'] for d in combined_data]
                min_temp = min(temp_values)
                max_temp = max(temp_values)
                avg_temp = sum(temp_values)/len(temp_values)
                min_hum = min(hum_values)
                max_hum = max(hum_values)
                avg_hum = sum(hum_values)/len(hum_values)
                min_press = min(press_values)
                max_press = max(press_values)
                avg_press = sum(press_values)/len(press_values)
            else:
                min_temp = max_temp = avg_temp = None
                min_hum = max_hum = avg_hum = None
                min_press = max_press = avg_press = None
            return render_template("lab_datas_db.html", temp=time_adjusted_temperatures, hum=time_adjusted_humidities, press=time_adjusted_pressures, combined_data=combined_data, start_date=from_date, end_date=to_date, range_time=range_time, temp_items=len(temperatures), hum_items=len(humidities), press_items=len(pressures), node=node, timezone=timezone, selected_interval=self.cron_manager.selected_interval, min_temp=min_temp, max_temp=max_temp, avg_temp=avg_temp, min_hum=min_hum, max_hum=max_hum, avg_hum=avg_hum, min_press=min_press, max_press=max_press, avg_press=avg_press)
        
        # create offline plotly graph 
        @self.app.route("/to_plotly")
        def to_plotly_offline():
            try:
                temperatures, humidities, pressures, timezone, from_date, to_date, node = self.get_datas()
            except Exception as e:
                print(f"Error generating plot: {e}")
                abort(500)
            file_path = self.plotly_generator.generate_plot(temperatures, humidities, pressures, node)
            return file_path
        
        # update cron based on user selection
        @self.app.route("/update_cron", methods=['POST'])
        def update_cron():
            new_interval = request.form.get('interval')
            if new_interval:
                self.cron_manager.selected_interval = new_interval
                cron_line = self.cron_manager.update_interval(new_interval)
                return jsonify({"status": "ok", "selected_interval": self.cron_manager.selected_interval, "applied_cron": cron_line})
            return jsonify({"status": "error", "message": "No interval provided"}), 400
        @self.app.route("/live_data")
        
        # return live sensor data for the selected node
        def live_data():
            node = request.args.get('node', '7')
            if node == '7':
                try:
                    data = self.sensor_reader.read_sensor()
                    temperature = data.get("temperature")
                    humidity = data.get("humidity")
                    pressure = data.get("pressure")
                except Exception:
                    temperature = humidity = pressure = None
            else:
                temperature = humidity = pressure = None
            return jsonify({"temp": temperature, "hum": humidity, "pres": pressure})
        
    # get data based on query parameters (date range, node, ...)    
    def get_datas(self):
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        timezone = request.args.get('timezone', 'Europe/Brussels')
        range_time_form = request.args.get('range_time', '')
        node = request.args.get('node', '7')
        if not from_date:
            from_date = arrow.now(timezone).shift(days=-1).format("DD-MM-YYYY HH:mm:ss")
        if not to_date:
            to_date = arrow.now(timezone).format("DD-MM-YYYY HH:mm:ss")
        try:
            range_time_int = int(range_time_form)
        except ValueError:
            range_time_int = None
            print("range_time_form not valid")
            
        # conversion of dates or fallback to defaults    
        if range_time_int is not None and not (from_date and to_date):
            arrow_time_to = arrow.now(timezone)
            arrow_time_from = arrow_time_to.shift(hours=-range_time_int)
            from_date_str = arrow_time_from.format("YYYY-MM-DD HH:mm:ss")
            to_date_str = arrow_time_to.format("YYYY-MM-DD HH:mm:ss")
        elif from_date and to_date:
            try:
                arrow_from = arrow.get(from_date, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
                arrow_to = arrow.get(to_date, "DD-MM-YYYY HH:mm:ss", tzinfo=timezone)
            except Exception as e:
                print(f"Error parsing dates: {e}")
                arrow_from = arrow.now(timezone).floor('day')
                arrow_to = arrow.now(timezone)
            from_date_str = arrow_from.format("YYYY-MM-DD HH:mm:ss")
            to_date_str = arrow_to.format("YYYY-MM-DD HH:mm:ss")
        else:
            arrow_time_to = arrow.now(timezone)
            arrow_time_from = arrow_time_to.shift(hours=-24)
            from_date_str = arrow_time_from.format("YYYY-MM-DD HH:mm:ss")
            to_date_str = arrow_time_to.format("YYYY-MM-DD HH:mm:ss")
        data = self.db_manager.fetch_data(node, from_date_str, to_date_str)
        return [data[0], data[1], data[2], timezone, from_date, to_date, node]
    
    # manage error responses for internal errors
    def register_error_handlers(self):
        @self.app.errorhandler(500)
        def internal_error(error):
            return "Une erreur interne est survenue", 500
        
    # start flask app    
    def run(self):
        self.app.run(host='0.0.0.0', port=8080)

# create backend instance and assign flask app for external use
backend = RpiBackend()
app = backend.app

# run in log mode or start flask 
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "log":
        backend.data_logger.log_all("7")
    else:
        backend.run()

