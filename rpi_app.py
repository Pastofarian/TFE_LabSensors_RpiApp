from flask import Flask, request, render_template
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
@app.route("/lab_datas_db")
def lab_datas_db():
    # connect to the db
    conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
    curs = conn.cursor()
    
    # get data from 'temperatures' table
    curs.execute("SELECT * FROM temperatures")
    temperatures = curs.fetchall()
    
    # get data from 'humidities' table
    curs.execute("SELECT * FROM humidities")
    humidities = curs.fetchall()
    
    # close the db connection
    conn.close()
    
    return render_template("lab_datas_db.html", temp=temperatures, hum=humidities)

# to run the app on port 8080
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
