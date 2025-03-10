#include <Wire.h>
#include <BME280I2C.h>
#include "HardwareSerial.h"

// Initialize BME280 sensor
BME280I2C bme;

// Device ID
char this_device_id = '2';

// Use Serial2 for HC-12 (16 = RX, 17 = TX)
HardwareSerial HC12(2);

// Variables for sensor readings
float temp = NAN, hum = NAN, pres = NAN;

// Buffers for HC-12 message
char message_buffer[70];

// Timer interval for sensor readings (10 minutes)
unsigned long sensor_interval_ms = 600000;
unsigned long last_sensor_reading_ms = 0;

void setup() {
  // Initialize Serial Monitor
  Serial.begin(9600);
  Serial.println("Initializing...");

  // Initialize HC-12 on UART2
  HC12.begin(9600, SERIAL_8N1, 16, 17);
  Serial.println("HC-12 initialized on pins 16 (RX) and 17 (TX)");

  // Initialize I2C for BME280
  Wire.begin();
  while (!bme.begin()) {
    Serial.println("Could not find BME280 sensor!");
    delay(1000);
  }

  // Check sensor type
  if (bme.chipModel() == BME280::ChipModel_BME280) {
    Serial.println("Found BME280 sensor! Success.");
  } else if (bme.chipModel() == BME280::ChipModel_BMP280) {
    Serial.println("Found BMP280 sensor! No humidity available.");
  } else {
    Serial.println("Unknown sensor! Check wiring.");
  }
}

// void loop() {
//   HC12.println("Test message from ESP32");
//   Serial.println("Sent: Test message from ESP32");
//   delay(1000);
// }

void loop() {
  unsigned long currentMillis = millis();

  // Take a reading every 10 minutes
  if (currentMillis - last_sensor_reading_ms >= sensor_interval_ms) {
    last_sensor_reading_ms = currentMillis;
    take_sensor_reading_and_send();
  }
}

void take_sensor_reading_and_send() {
  // Variables locales pour les données du capteur
  BME280::TempUnit tempUnit(BME280::TempUnit_Celsius);
  BME280::PresUnit presUnit(BME280::PresUnit_hPa);

  // read datas from sensor
  bme.read(pres, temp, hum, tempUnit, presUnit);

  // prepare message
  String message = String(millis()) + "," + String(temp, 2) + "," +
                   String(hum, 2) + "," + String(pres, 2) + "," +
                   String(this_device_id) + ",999"; // '999' end marker
  message.toCharArray(message_buffer, message.length() + 1); // Convert string in char array

  // transmit message with hc12
  HC12.println(message_buffer);  

  // Display errors
  Serial.print("Sent message: ");
  Serial.println(message);
}
