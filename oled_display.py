import RPi.GPIO as GPIO
import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime
import os
import sqlite3
from ischedule import schedule, run_loop  # https://pypi.org/project/ischedule/
import signal

button_press = 0  # to follow the number of button presses
                  # to scroll between pages

# the OLED can display 4 lines
line1 = ""
line2 = ""
line3 = ""
line4 = ""

led_pin = 4   # blinking led
button_pin = 22 # button (BCM 22, physic pin 15)

GPIO.setmode(GPIO.BCM) # i use BCM
GPIO.setup(led_pin, GPIO.OUT)
GPIO.output(led_pin, GPIO.LOW)

# initializing the I2C OLED display
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)
# path to a TrueType font available on the system
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font = ImageFont.truetype(font_path, 16)

def handler(signum, frame):
    res = input("Ctrl-c a été pressé. Voulez-vous vraiment quitter? y/n ")
    if res == 'y':
        GPIO.cleanup()
        exit(1)

def button_callback(channel):
    global button_press
    time.sleep(0.05) # 5 ms sleep (anti-rebond)
    if GPIO.input(channel) == 1:
        button_press += 1
        if button_press >= len(screen_pages):
            button_press = 0
        write_to_oled()

def write_to_oled():
    GPIO.output(led_pin, GPIO.HIGH)
    oled.fill(0)
    oled.show()
    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)

    # if page is numeric, treat as sensor page
    # if page is 'S', treat as disk space
    # else show N/A
    if screen_pages[button_press].isnumeric():
        display_parts = get_database_records(screen_pages[button_press])
    else:
        if screen_pages[button_press] == "S":
            display_parts = get_disk_space()
        else:
            display_parts = ["N/A", "N/A", "N/A", "N/A"]

    line1 = display_parts[0]
    line2 = display_parts[1]
    line3 = display_parts[2]
    line4 = display_parts[3]

    draw.text((5, 0), line1, font=font, fill=255)
    draw.text((5, 15), line2, font=font, fill=255)
    draw.text((5, 30), line3, font=font, fill=255)
    draw.text((5, 45), line4, font=font, fill=255)
    # displays the current page at the bottom right
    draw.text((115,45), str(screen_pages[button_press]), font=font, fill=255)

    oled.image(image)
    oled.show()
    GPIO.output(led_pin, GPIO.LOW)

def get_disk_space():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

    free_space = os.statvfs('/')
    free_space_in_Gbytes = (free_space.f_bavail * free_space.f_frsize) / (1024*1024*1024)
    total_space_in_Gbytes = (free_space.f_blocks * free_space.f_frsize) / (1024*1024*1024)
    percent_free = (free_space.f_bavail / free_space.f_blocks) * 100

    line1 = current_time
    line2 = f"{round(free_space_in_Gbytes,2)} GB libres"
    line3 = f"{round(percent_free)}% dispo"
    line4 = ""
    return [line1, line2, line3, line4]

def get_database_records(sensor_id):
    # default values ​​if no data
    temperature = "-99"
    humidity    = "-99"
    pressure    = "-99"
    date_time   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
    curs = conn.cursor()

    # get the most recent temperature for this sensor_id
    curs.execute("SELECT timestamp, sensor_id, temperature FROM temperatures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (sensor_id,))
    row = curs.fetchone()
    if row and row[2] is not None:
        temperature = str(round(row[2],2))
        date_time = row[0]

    # get the most recent humidity for this sensor_id
    curs.execute("SELECT timestamp, sensor_id, humidities FROM humidities WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (sensor_id,))
    row = curs.fetchone()
    if row and row[2] is not None:
        humidity = str(round(row[2],2))

    # get the most recent pressure for this sensor_id
    curs.execute("SELECT timestamp, sensor_id, pressure FROM pressures WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (sensor_id,))
    row = curs.fetchone()
    if row and row[2] is not None:
        pressure = str(round(row[2],2))

    conn.close()

    # format the date for display
    record_date_time = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%y %H:%M')
    line1 = record_date_time
    line2 = temperature + " °C"
    line3 = humidity + " %"
    line4 = pressure + " hpa"
    return [line1, line2, line3, line4]

def update_oled():
    write_to_oled()

GPIO.setwarnings(False)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

signal.signal(signal.SIGINT, handler)
GPIO.add_event_detect(button_pin, GPIO.RISING, callback=button_callback)

# get sensor_ids dynamically from the db
conn = sqlite3.connect('/var/www/rpi_app/rpi_app.db')
curs = conn.cursor()
curs.execute("SELECT DISTINCT sensor_id FROM temperatures ORDER BY sensor_id ASC")
rows = curs.fetchall()
conn.close()

# create pages list based on all found sensor_ids + the stock page
sensor_pages = [str(row[0]) for row in rows]
screen_pages = sensor_pages + ["S"]

# schedule the oled update every 60 seconds
schedule(update_oled, interval=60.0)

print("Prêt")

write_to_oled()

run_loop()
