#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT11

#define PIR1_PIN 2     // Primary PIR motion sensor
#define PIR2_PIN 3     // Secondary PIR motion sensor
#define LDR_PIN A0
#define BUTTON_PIN 13  // D13 connected to tactile button, other leg to GND

DHT dht(DHTPIN, DHTTYPE);

unsigned long lastRead = 0;
const unsigned long interval = 2000; // ms (DHT11 safe rate)

bool buttonTriggered = false;
int lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;

void setup() {
  Serial.begin(9600);

  pinMode(PIR1_PIN, INPUT);
  pinMode(PIR2_PIN, INPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  dht.begin();
}

void loop() {
  // Check button continuously so quick taps aren't missed
  int reading = digitalRead(BUTTON_PIN);
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }
  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading == LOW) { // Active LOW when pressed to GND
      buttonTriggered = true;
    }
  }
  lastButtonState = reading;

  // Periodic sensor read and transmission
  if (millis() - lastRead < interval) {
    return;
  }
  lastRead = millis();

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature(); // Celsius
  // Discard first analog read to let ADC multiplexer/capacitor settle
  analogRead(LDR_PIN);
  int light = analogRead(LDR_PIN);
  int light_level = 1023 - light;
  
  // Motion is 1 if either or both PIR sensors detect presence
  int motion1 = digitalRead(PIR1_PIN);
  int motion2 = digitalRead(PIR2_PIN);
  int motion = (motion1 == HIGH || motion2 == HIGH) ? 1 : 0;

  // DHT11 can fail; skip bad reads
  if (isnan(humidity) || isnan(temperature)) {
    return;
  }

  int btn = buttonTriggered ? 1 : 0;
  buttonTriggered = false; // Reset trigger

  Serial.print("{\"temp\":");
  Serial.print(temperature);
  Serial.print(",\"humidity\":");
  Serial.print(humidity);
  Serial.print(",\"light\":");
  Serial.print(light_level);
  Serial.print(",\"motion\":");
  Serial.print(motion);
  Serial.print(",\"button\":");
  Serial.print(btn);
  Serial.println("}");
}
