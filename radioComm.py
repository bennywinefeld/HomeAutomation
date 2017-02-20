# This file contains functions required for communication with Arduino edge 
# devices through NRF24 board

import RPi.GPIO as GPIO
from lib_nrf24 import NRF24
import time, sys, spidev

GPIO.setmode(GPIO.BCM)
pipes = [[0xE8,0xE8,0xF0,0xF0,0xE1],[0xAB,0xCD,0xAB,0xCD,0x71]]
radio = NRF24(GPIO,spidev.SpiDev())

# Initialize NRF24 radio
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

radio.openWritingPipe(pipes[0])
radio.openReadingPipe(1,pipes[1])
radio.powerUp()
radio.printDetails()

# Packet format: <sender_id> <receiver_id> <command_code> <LSB_byte> <MSB_byte>
# Board ids should start with 1, first byte equal 0 means - address all listening Arduino boards
# Commands:
#  0xA1 <value> - return passed lsb + msg back to check communication
#  0xA2 <digital_pin_id> <0|1>  - set digital pin mode, 0 - input, 1 - output
#  0xA3 <digital_pin_id> - digital read
#  0xA4 <digital_pin_id> <0|1> - digital write
#  0xA5 <analog_pin_id> - analog read
#  0xA6 <analog_pin_id> <0-255> - analog (pwm) write
#  0xA7  - measure and return Vcc value
#
# For every packet sent we expect packet sent back from Arduino in the following format:
#  <board_id> <command_completion_status> <LSB_byte> <MSB_byte>

def dbgPrint(prefix, msg):
    currTime = time.strftime("%d %b %Y %H:%M:%S", time.localtime())
    print "[" + currTime + "] " + prefix + ":",
    print " ".join(hex(n) for n in msg)

# Send sequence of 0,1 turn on/off signals
def sendSequence(sender_id,receiver_id,pin_id,bitSequence,delayBtwBits):
    for bit in bitSequence:
        sendMessage(sender_id,receiver_id,0xA4,pin_id,bit)
        time.sleep(0.1)
        receiveMessage()
        time.sleep(delayBtwBits)
        
# Send wireless message(4 byte packet) to one of the Arduino boards 
# By default send the same message 3 time for reliability
def sendMessage(sender_id,receiver_id, command_code, lsb_byte=0, msb_byte=0, repeat=1):
    sentMsg = [sender_id,receiver_id, command_code, lsb_byte, msb_byte]
    radio.stopListening()
    dbgPrint("sending message",sentMsg)
    radio.write(sentMsg)
    radio.startListening()  

# Receive 4 byte wireless message
def receiveMessage(time_limit=0.1,time_interval=0.01):
    # Need to declare list first before filling it up
    receivedMsg = [0,0,0,0,0]
    start = time.time()
    
    # Wait until radio is available or time limit is reached
    while not radio.available(0):
        time.sleep(time_interval)
        if time.time() - start > time_limit:
            #radio.stopListening()
            dbgPrint("received message timed out", receivedMsg)
            return -1

    # OK, radio data is available within the time limit
    radio.read(receivedMsg, 5)
    dbgPrint("received message",receivedMsg)
    
    return receivedMsg

# This is a tesign function which repeatedly sends 0/1 to Arduino     
def runTest(option): 
    myByte = 0x00
    time.sleep(0.5)
    
    # Usage sendSequence(board_id,pin_id,bitSequence,delayBtwBits=1)
    try:
        if (option == "one_pulse"):
            #sendSequence(0x0,0x2,[0,1,0],0.5)
            sendSequence(0x0,0x3,[0,0,1,1,0,0],0.5)
            #sendSequence(0x0,0x2,[0,0,1,1,0,0],0.5)
        elif(option == "long_sequence"):
            # All boards turn pins 2 and 3 off->on->off
            for i in range(300):
                #sendMessage(0x0,0xA4,0x3,i%2)
                sendMessage(0x0,0xA4,0x3,i)
                time.sleep(0.3)
                receiveMessage()
                time.sleep(1)
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

# Exec starts here
if __name__ == '__main__':
    args = sys.argv[1:]
    if (args[0] == "run_test"):
        # Usage: homeControlHub.py  run_test one_pulse
        runTest(args[1]) 
    elif (args[0] == "start_heater_control"):
        # Usage homeControlHub.py start_heater_control 18:40 18:41 
        startHeaterControl(args[1],args[2])
    else:
        print "Illegal or undefined mode"
        exit

    print("Cleaning up communication channel")
    radio.end()
    GPIO.cleanup()
