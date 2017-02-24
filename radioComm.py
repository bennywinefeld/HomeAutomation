# This file contains low-level functions required for communication with Arduino edge 
# devices through NRF24 board plus some general purpose procs
print "sourcing radioComm.py"
import spidev,time
import RPi.GPIO as GPIO
from lib_nrf24 import NRF24

# Initialize NRF24 radio - we use global instance 'radio'
GPIO.setmode(GPIO.BCM)
radio = NRF24(GPIO,spidev.SpiDev())
GPIO.cleanup()
radio.begin(0,17)
radio.setChannel(0x78)
radio.setDataRate(NRF24.BR_250KBPS)
radio.setPALevel(NRF24.PA_MAX)
radio.setCRCLength(NRF24.CRC_8);
radio.setRetries(15,15);
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.enableAckPayload()
radio.powerUp()
radio.printDetails()

# Print packet of byte list in hex format
def dbgPrintPacket(msg,prefix="dbg"):
    currTime = time.strftime("%d %b %Y %H:%M:%S", time.localtime())
    print "[" + currTime + "] " + prefix + ":",
    print " ".join(hex(n) for n in msg)
        
# Send wireless message(4 byte packet) to one of the Arduino boards 
# By default send the same message 3 time for reliability
def sendMessage(sender_id,receiver_id, command_code, lsb_byte=0, msb_byte=0, repeat=1):
    sentMsg = [sender_id,receiver_id, command_code, lsb_byte, msb_byte]
    radio.stopListening()

    # Open reading writing pipes to a given device
    radio.openReadingPipe(receiver_id,[0xAB,0xCD,0xAB,0xCD,0x71 + receiver_id])
    radio.openWritingPipe([0xE8,0xE8,0xF0,0xF0,0xE0 + receiver_id])
    
    #dbgPrintPacket(address, " Writing to pipe: ") 
    dbgPrintPacket(sentMsg,"sending message")
    radio.write(sentMsg)
    radio.startListening()  

# Receive 4 byte wireless message
def receiveMessage(receiver_id,time_limit=0.1,time_interval=0.01):
    # Need to declare list first before filling it up
    receivedMsg = [0,0,0,0,0]
    start = time.time()
    
    # Wait until radio is available or time limit is reached
    while not radio.available(0):
        time.sleep(time_interval)
        if time.time() - start > time_limit:
            #radio.stopListening()
            dbgPrintPacket(receivedMsg,"received message timed out")
            return -1

    # OK, radio data is available within the time limit
    radio.read(receivedMsg, 5)
    dbgPrintPacket(receivedMsg,"received message")
    
    return receivedMsg

# This is a testing function which repeatedly sends 0/1 to Arduino     
def runTest(option): 
    time.sleep(0.5)
    
    # Usage sendSequence(board_id,pin_id,bitSequence,delayBtwBits=1)
    try:
        if (option == "one_pulse"):
            # Toggle pin 3 of device 4
            for signal in [0,0,1,1,0,0]:
                sendMessage(0x1,0x4,0xA4,3,signal)
                time.sleep(0.5)
                receiveMessage()
                time.sleep(0.5)
        elif(option == "long_sequence"):
            # All boards turn pins 2 and 3 off->on->off
            for i in range(300):
                sendMessage(0x1,0x4,0xA4,3,i%2)
                time.sleep(0.5)
                receiveMessage()
                time.sleep(0.5)
                print(" ")
        elif(option == "listen_only"):
            print "Starting listening"
            radio.startListening()
            while True:
                receiveMessage(1,time_interval=0.01)
        else:
            print "Incorrect option",option
            print("Cleaning up")
            radio.end()
            GPIO.cleanup()
            exit()
            
    except KeyboardInterrupt:
        print("Cleaning up")
        radio.end()
        GPIO.cleanup()
        exit()

# This test section gets executed only if this file is directly launched rather than
# imported from SwitchController.py
# Usage: homeControlHub.py  run_test one_pulse
if __name__ == '__main__':
    runTest(sys.argv[0]) 
    
    print("Cleaning up communication channel")
    radio.end()
    GPIO.cleanup()
