# This file contains low-level functions required for communication with Arduino edge 
# devices through NRF24 board plus some general purpose procs
print "sourcing radioComm.py"
import spidev,time, sys
import RPi.GPIO as GPIO
from lib_nrf24 import NRF24

def dbgPrint(msg):
    currTime = time.strftime("%d %b %Y %H:%M:%S", time.localtime())
    print "[" + currTime + "] " + msg

# Initialize NRF24 radio - we use global instance 'radio'
GPIO.setmode(GPIO.BCM)
radio = NRF24(GPIO,spidev.SpiDev())
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


def packetToString(msg):
    return(" ".join(hex(n) for n in msg))
        
# Send wireless message(4 byte packet) to one of the Arduino boards 
# By default send the same message 3 time for reliability
def sendMessage(sender_id,receiver_id, command_code, lsb_byte=0, msb_byte=0):
    sentMsg = [sender_id,receiver_id, command_code, lsb_byte, msb_byte]
    radio.stopListening()

    # Open reading writing pipes to a given device
    radio.openReadingPipe(receiver_id,[0xAB,0xCD,0xAB,0xCD,0x71 + receiver_id])
    radio.openWritingPipe([0xE8,0xE8,0xF0,0xF0,0xE0 + receiver_id])
    
    radio.write(sentMsg)
    radio.startListening()  

# Send message and check response. If response is invalid, try few more times  
# If succesful ,return how many attempts it took. If failed - return -1
def sendMessageWithConfirm(sender_id,receiver_id, command_code, lsb_byte=0, msb_byte=0, attempts=15, pauseBtwTries=0.5):
    sentMsg = [sender_id, receiver_id, command_code, lsb_byte, msb_byte]
    for attempt in range(1,attempts+1):
        currTime = time.strftime("%d %b %Y %H:%M:%S", time.localtime())
        print " sending msg  %s, attempt %d/%s" % (packetToString(sentMsg), attempt, attempts )
        sendMessage(sender_id, receiver_id, command_code, lsb_byte, msb_byte)
        response = receiveMessage()
        if (response == [receiver_id, sender_id, command_code, lsb_byte, msb_byte]):
            print " message sent successfully"
            return attempt
        
        # Wait a little, then try again
        time.sleep(pauseBtwTries)

    print " All attempts to send message failed"
    return -1

# Receive 4 byte wireless message
def receiveMessage(time_limit=0.2,time_interval=0.02):
    # Need to declare list first before filling it up
    receivedMsg = [0,0,0,0,0]
    start = time.time()
    delay = 0
    #print "Started receiveMessage at %s " % start
    # Wait until radio is available or time limit is reached
    while not radio.available(0):
        time.sleep(time_interval)
        #print " current time= %s" % time.time()
        delay = time.time() - start
        if delay > time_limit:
            #radio.stopListening()
            print(" receiveMessage timed out, delay= %.2f" % delay)         
            return -1

    # OK, radio data is available within the time limit
    radio.read(receivedMsg, 5)
    print(" got response %s in %.2f sec" % ( packetToString(receivedMsg), delay))
    
    return receivedMsg

# This is a testing function which repeatedly sends 0/1 to Arduino     
def runTest(option): 
    time.sleep(0.5)
    
    # Usage sendSequence(board_id,pin_id,bitSequence,delayBtwBits=1)
    try:
        if (option == "one_pulse"):
            # Toggle pin 3 of device 4
            for signal in [0,0,1,1,0,0]:
                sendMessage(0x1,0x4,0xA1,3,signal)
                time.sleep(0.5)
                receiveMessage()
                time.sleep(0.5)
        elif(option == "long_sequence"):
            # All boards turn pins 2 and 3 off->on->off
            totalTransmissions = 300
            goodTransmissions = 0
            badTransmissions = 0
            attemptCnt = 0
            for i in range(totalTransmissions):
                print("Transmission %d/%d" % (i, totalTransmissions))
                # <sender>,<receiver>,<command>,pin,<value>
                attempts = sendMessageWithConfirm(1,4,0xA4, 3, i % 2)
                time.sleep(1)
                print(" attempts = %d" % attempts)
                if (attempts > 0):
                    attemptCnt += attempts
                    goodTransmissions += 1;
                else:
                    badTransmissions += 1;
                
            
            print("\n\n %d/%d good transmissions, average num of attempts = %.2f" % (goodTransmissions, totalTransmissions, float(attemptCnt)/float(goodTransmissions)))
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
    runTest(sys.argv[1]) 
    
    print("Cleaning up communication channel")
    radio.end()
    GPIO.cleanup()
