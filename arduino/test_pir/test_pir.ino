// Quick test sketch to verify both PIR sensors (D2 and D3)
#define PIR1_PIN 2
#define PIR2_PIN 3

void setup() {
  Serial.begin(9600);
  pinMode(PIR1_PIN, INPUT);
  pinMode(PIR2_PIN, INPUT);
  Serial.println("PIR test started. (Note: PIR sensors take ~30s to warm up/settle)");
}

void loop() {
  int pir1 = digitalRead(PIR1_PIN);
  int pir2 = digitalRead(PIR2_PIN);

  Serial.print("PIR 1 (D2): ");
  Serial.print(pir1);
  Serial.print("  |  PIR 2 (D3): ");
  Serial.print(pir2);

  if (pir1 == HIGH || pir2 == HIGH) {
    Serial.println("  --> [MOTION DETECTED]");
  } else {
    Serial.println("  --> [quiet]");
  }

  delay(500);
}
