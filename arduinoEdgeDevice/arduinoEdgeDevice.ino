#include <SPI.h>
#include "RF24.h"
#include "nRF24L01.h"

// This ID must be unique for each Arduino edge device
#define BOARD_ID 0x04

// Size of payload received from and send to raspberry 
#define PACKET_SIZE 5

/* Start radio on CE, CSN pins*/
RF24 radio (9,10);

// This proc is for debugging  only to indicate that operation succeeded or failed
void myBlink(int pin, int upTime, int downTime, int repetitions) { 
  for (int i=0;i<repetitions;i++) {
    // 0 means builtin pin
    // For  Arduino Pro Micro use RXLED (17) isntead 
    if (pin == 0) { 
      pin = LED_BUILTIN;
    }
    digitalWrite(pin , HIGH);   
    delay(upTime);                    
    digitalWrite(pin, LOW);    
    delay(downTime);                       
  }
}

// Print received message byte by byte
void printMsg(String prefix, byte msg[]) {
  Serial.print(prefix);
  for (int i=0; i< PACKET_SIZE; i++) {
      Serial.print(msg[i],HEX);
      Serial.print(" ");
    }
    Serial.println("");
}
  
 
void setup() {
  Serial.begin(57600);

  /* By default pins 2 and 3 are outputs, but we can redefine them through wireless link 
    pin 2 drives optocoupler and 3 is connected to green led for debugging messages
   */
 
  pinMode(2, OUTPUT);
  digitalWrite(2,0);
  pinMode(3, OUTPUT);
  digitalWrite(3,0);
  pinMode(4, OUTPUT);
  digitalWrite(4,0);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN,0);
  
  radio.begin();
  radio.setPALevel(RF24_PA_MAX);
  radio.setRetries(15,15);
  radio.setChannel(0x78);
  radio.setCRCLength(RF24_CRC_8);
  radio.setAutoAck(true);
  radio.setDataRate(RF24_250KBPS);
  radio.enableDynamicPayloads();
//#uint8_t address[] = { 0xCC,0xCE,0xCC,0xCE,0x00 + BOARD_ID };
  
  radio.openWritingPipe(0xABCDABCD71LL + BOARD_ID);
  radio.openReadingPipe(1,0xE8E8F0F0E0LL + BOARD_ID);
  radio.powerUp();
  radio.startListening();

  // Blink pin 3 BOARD_ID times to indicate success of initialization
  myBlink(3,300,500,BOARD_ID);
  //Serial.print("Listening to pipe: ",);
}

void loop() {  
  bool ok; 
  byte receivedMsg[PACKET_SIZE];
  byte sentMsg[PACKET_SIZE];
  byte gatewayID, edgeDeviceID, commandCode, MSB, LSB;
  
  byte pinId = 0;
  byte pinValue = 0;
  int i, value;
  

  // If no radio signal detected simply wait 50ms until testing again
  if (! radio.available()) {
    delay(50);
    return;
  }

  // OK radio signal available
  radio.read(receivedMsg, PACKET_SIZE);
  printMsg("Received msg: ",receivedMsg);
  radio.stopListening();

  /* Unpack received payload to 5 individual bytes
   *  First byte is a sender ID (i.e Raspberry gateway)
   *  Second is ID of intended Arduino board
   */
  gatewayID = receivedMsg[0];
  edgeDeviceID = receivedMsg[1];
  commandCode = receivedMsg[2];
  MSB = receivedMsg[3];
  LSB = receivedMsg[4];
  
  /* edgeDeviceID sent from Raspberry must be equal to either
    0 (i.e this is a command to all Arduino edge devices) 
    or BOARD_ID
   if neither is true - ignore the message, it's for another board */
  if ((edgeDeviceID != BOARD_ID) && (edgeDeviceID != 0) ) {
    Serial.println("Received message is for different board, ignore");
    delay(50);
    radio.startListening();
    return;
  }

  /* OK, message was for this Arduino. First byte of the reply is board id
   * and second byte is a gateway (i.e raspberry) ID
   * In our messaging first byte identifies source device and second - destination
   * For unicast message exchange if message received from rapsberry is say 0x00 0x03 ... ,
   * then reply will be 0x03 0x00 ...    
   * remaining 3 bytes in the reply message are copied from received message
   */
  sentMsg[0] = BOARD_ID;
  sentMsg[1] = gatewayID;
  for (i = 2; i<=4; i++) {     
      sentMsg[i] = receivedMsg[i];
   }
    
  // Process command code
  switch(commandCode) {
    case 0xA1 :
      // Command 0xA1 - retransmitting commandCode, msb and lsb back do nothing else  
      break;       
    case 0xA4 :
      // Command 0xA4 - MSB holds a number of output pin, LSB its value (0 or 1)   
      pinId = MSB;
      pinValue = LSB;
      digitalWrite(pinId,pinValue);
      break; 
    default :
      Serial.println("Invalid command"); 
      for (i = 2; i<=4; i++) {     
        sentMsg[i] = 0xFF;
      } 
  }

  /* Different delay for different Arduino boards to set their
   replies - 20ms apart */
  delay(BOARD_ID*20);
  printMsg("Sending back msg: ", sentMsg);
  ok = radio.write(&sentMsg,PACKET_SIZE);  
  if (ok)
    Serial.println("ok...");
  else
    Serial.println("failed.\n\r");
    
  radio.startListening();
}

