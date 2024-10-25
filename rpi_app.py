from flask import Flask, request, render_template
import sys
import Adafruit_DHT

# Create an instance of the Flask app
app = Flask(__name__)
app.debug = True  # For debugging purpose

# Default route 
@app.route("/")
def main_page():
    return "Bienvenue dans l'app de mesure du labo acoustique"

# Route that reads temperature and humidity from DHT22
@app.route("/lab_datas")
def lab_datas():
    # Read the temperature and humidity from DHT22
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, 17)
    
    # If valid data is received from the sensor
    if humidity is not None and temperature is not None:
        return render_template("lab_datas.html", temp=temperature, hum=humidity)
    else:
        # If the sensor fails, show a page indicating no sensor data
        return render_template("sensor_error.html")

# Main entry point to run the app on port 8080
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
