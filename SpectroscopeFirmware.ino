const int clockPin = 3;
const int readPin0 = 2;
const int ICG = 4;
const int SH = 5;
const int CS = 9;
const int SCLK = 8;
const int DIN = 10;

int shState = LOW;

const int MaxCC = 6184;

int clockState = LOW;

int cc = 0;

#define BUFFER_SIZE 1500

uint8_t buffer_0[BUFFER_SIZE];
uint16_t buffer_0_count = 0x0000;
uint8_t reading = 0;
uint32_t delta_time_0 = 0;

bool enabled = true;

bool shutter = false;

bool ADCreading = false;

void captureFrame(){

  while(cc < 6128){
    if(cc % 2 == 0){
      digitalWrite(clockPin,HIGH);

      if(cc > 128 && cc <= 6128) {
        if(ADCreading){
          digitalWrite(CS, HIGH);
          ADCreading = false;
        }else{
          digitalWrite(CS, LOW);
          ADCreading = true;
          reading = 0;
          for(int i = 0; i < 16; i++){

            digitalWrite(SCLK, LOW);
            delayMicroseconds(2);
            digitalWrite(SCLK, HIGH);
            if(i < 12){
              reading = reading << 1;
              reading = reading + digitalRead(DIN);
            }
            delayMicroseconds(2);
          }
          buffer_0[(cc - 128) / 4] = reading;
        }
      }
    }else{
      digitalWrite(clockPin, LOW);
      
      if((cc + 1) % 8 == 0 && cc > 30 && cc < 6108){
        shutter = !shutter;
        digitalWrite(SH, shutter);
      }
    }

    if(cc == 4){
      digitalWrite(ICG,LOW);
    }

    if(cc == 6){
      digitalWrite(SH,HIGH);
      shState = HIGH;
    }

    if(cc == 14){
      digitalWrite(SH,LOW);
      shState = LOW;
    }

    if(cc == 30){
      digitalWrite(ICG,HIGH);
    }
    cc++;
   //Serial.println("read started");
  }
}


void setup()
{
  pinMode(ICG,OUTPUT);
  pinMode(SH,OUTPUT);

  digitalWrite(ICG,HIGH);
  digitalWrite(SH,LOW);

  pinMode(clockPin, OUTPUT);

  pinMode(CS, OUTPUT);
  pinMode(SCLK, OUTPUT);
  pinMode(DIN, INPUT);

  digitalWrite(CS, HIGH);
  digitalWrite(SCLK, HIGH);

	Serial.begin(115200);

  delay(500);

	Serial.flush();
}

void loop()
{
    Serial.println("Start Frame");
    captureFrame();
    for(int i = 0; i < BUFFER_SIZE; i+=1){
      Serial.print(buffer_0[i]);
      Serial.print(", ");
    }
    Serial.println();
    Serial.println("End Frame");
    cc = 0;
}
