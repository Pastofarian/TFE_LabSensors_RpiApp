# Raspberry Pi Climate Monitoring System

This repository hosts a small web application that collects and displays real-time temperature, humidity, and pressure data from multiple “acoustic cells" in a specialized lab environment.

---

## 1. Overview

- **Key Features**  
  - Collects sensor data (temperature, humidity, pressure) via **433 MHz** radio modules connected to ESP32-based nodes.  
  - Stores measurements in a local SQLite database and optionally logs them to Google Sheets.  
  - Provides an internal **Flask** web interface for real-time data visualization and historical trends.  
  - Runs entirely on a **Raspberry Pi** with **Nginx + uWSGI**.  

---

## 2. Technical Details

1. **Hardware**  
   - Raspberry Pi 4B (running Raspberry Pi OS).  
   - Multiple nodes (ESP32 + BME280 + HC12 radio module).  
   - Local Wi-Fi/Ethernet is not used for the nodes because of thick acoustically insulated walls.

2. **Software Stack**  
   - **Flask** as the main Python web framework.  
   - **Nginx** as the web server, **uWSGI** as the application server.  
   - **SQLite** for local data storage.  
   - **Google Charts** and **Plotly** for data visualization.  
   - **Jinja** templating + **CSS/JS** for the front-end.  
   - **Virtual environment** (venv) to isolate Python dependencies.

3. **Data Flow**  
   1. Radio signal → Raspberry Pi → Flask routes.  
   2. Database insert (SQLite).  
   3. Automatic logging to Google Sheets (optional).  
   4. Front-end: Real-time & historical data via browser.

---

## 3. Setup & Usage

1. **Install Dependencies**
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-venv nginx
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Nginx & uWSGI**  
   - Copy the provided `.ini` and `.conf` files into appropriate locations.  
   - Adjust paths (e.g., `/var/www/rpi_app/`).  
   - Restart services:
     ```bash
     sudo systemctl restart nginx
     sudo systemctl restart uwsgi
     ```

3. **Run the Application**  
   - Development mode:
     ```bash
     python rpi_app.py
     ```
   - Production mode through **uWSGI + Nginx**:
     ```bash
     uwsgi --ini rpi_app_uwsgi.ini
     ```

4. **Access the Web Interface**  
   - Visit `http://<raspberry-pi-ip>/lab_datas_db` for historical data.  
   - Visit `http://<raspberry-pi-ip>/lab_datas` for live readings.

---

## 4. Project Structure

```
rpi_app/
├── rpi_app.py          # Flask entry point
├── lab_datas.py        # Periodic logging script
├── static/             # Static files (CSS/JS)
├── templates/          # Jinja2 templates
├── requirements.txt    # Python dependencies
├── rpi_app_nginx.conf  # Nginx config snippet
├── rpi_app_uwsgi.ini   # uWSGI config
└── ...
```
