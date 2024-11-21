// Use Serial2 to communicate with HC12
HardwareSerial HC12(2);  // UART2 on ESP32

void setup() {
  Serial.begin(9600);          // Debugging via Serial Monitor
  HC12.begin(9600, SERIAL_8N1, 16, 17); // RX=16, TX=17
  Serial.println("ESP32 près à recevoir depuis le HC12.");
}

void loop() {
  // Check if data is available on HC12
  while (HC12.available()) {
    String receivedData = HC12.readStringUntil('\n');  // Read until newline
    Serial.print("Recu du HC12: ");
    Serial.println(receivedData);
  }
  delay(100);  // Small delay to avoid kaboum the CPU
}

