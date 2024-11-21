import board  # Pin definitions
import busio  # I2C support
import adafruit_ssd1306  # SSD1306 display driver
from PIL import Image, ImageDraw, ImageFont  # For drawing on the display
import time

# Initialize I2C and OLED
i2c = busio.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3c)

try:
    # Clear the screen
    oled.fill(0)
    oled.show()
    
    # Prepare text
    text = "Test écran OLED"
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Default font
    font = ImageFont.truetype(font_path, size=14)
    image = Image.new("1", (oled.width, oled.height))  # 1-bit image
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), text, font=font, fill=255)  # Draw text at (0,0)
    
    # Display the text
    oled.image(image)
    oled.show()
    
    # Keep the text displayed until Ctrl+C is pressed
    print("CTRL + C pour exit")
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    # Clear the display when the script is interrupted
    oled.fill(0)
    oled.show()
    print("A+ dans l'bus")

