// Use Serial2 to communicate with HC12
HardwareSerial HC12(2);  // UART2 on ESP32

void setup() {
  Serial.begin(9600);                         // Debugging via Serial Monitor
  HC12.begin(9600, SERIAL_8N1, 16, 17);       // RX=16, TX=17
  Serial.println("ESP32 ready to send data via HC12.");
}

void loop() {
  unsigned long millis_to_tx = millis();      // Get current time in ms
  char buf[20];
  utoa(millis_to_tx, buf, 10);                // Convert unsigned long to string

  // Send data via HC12
  HC12.print(buf);                            // Send the string
  HC12.print('\n');                           // Send newline

  // Debug: Show sent data on Serial Monitor
  Serial.print("Sent: ");
  Serial.println(buf);

  delay(1000);                                // Wait 1 second before sending again
}

