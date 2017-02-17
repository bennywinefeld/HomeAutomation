import string, cherrypy, HTML, os, sys, argparse

def enum(**enums):
    return type('Enum', (), enums)

# Enumerated types for pins of the edge devices
PinTypes = enum(momentary_switch='momentary_switch', toggle_switch='toggle_switch',digital_input='digital_input', analog_input='analog_input')

# Each instance of this class controls one edge device with few pin switches which can eb set to either 0 or 1 
# pin can control optocoupler, relay or led 
# Every edge device must have uniwue ID 

class EdgeDevice:

  def __init__(self,deviceName,deviceId,pins=((2,PinTypes.momentary_switch),(3,PinTypes.toggle_switch))):
    self.name = deviceName
    self.id = deviceId
    self.pins = {}
    
    # Initialize pins
    for pin in pins:
      pinId = pin[0]
      pinType = pin[1]
      self.pins[pinId] = Pin(pinId,pinType,deviceId)

  def __repr__(self):
    text = "Device " + self.name + " id=" + str(self.id) 
    for pinId in sorted(self.pins.keys()):
      text += "\n " + self.pins[pinId].getInfo()  
    return text

  
  def setPinState(self,pinId,pinValue):
    pin = self.pins[pinId]
    pin.setState(pinValue)

# One pin on the edge device:
# Edge device pin can be of the following types:
#  momentary_switch, toggle_switch, digital_input, analog_input
class Pin:
  def __init__(self,pinId, pinType, deviceId):
    self.id = pinId
    self.type = pinType
    self.deviceId = deviceId    
    self.state = 0

  # This function actually sneds radio signal to edge device
  def sendSequenceToEdgeDevice(self,sequence):
    print "Sending sequence " + str(sequence) + " to pin " + str(self.id) + " of device " + str(self.deviceId)

  # For output pin - set pin state and send signal to edge device
  def setState(self, pinValue):
    # Reject attempt to set value for input pin
    if (not (self.type==PinTypes.momentary_switch or PinTypes.toggle_switch)):
      print "Can't set value to a pin " + pinId + " which is not an output switch" 
      return
    
    # If current pin state is alredy equal to speciefied pinValue - no need to do anything
    if (pinValue == self.state):
      print "Pin " + str(self.id) + " of device " + str(self.deviceId) + " is already at state " + str(self.state)
      return

    # For toggle switch, simple send signal to edge device resulting in 
    # setting its physical out pin with id identical to self.id to a specified value
    if (self.type == PinTypes.toggle_switch):
      self.sendSequenceToEdgeDevice([pinValue])
    elif (self.type == PinTypes.momentary_switch):
      self.sendSequenceToEdgeDevice([0,1,0])
    # Remember the state value
    self.state = pinValue
  
  


  def __repr__(self):
    return getInfo(self)

  def getInfo(self):
    return "device " + str(self.deviceId) + " pin " + str(self.id) + " type=" + self.type + " state=" + str(self.state)

def testMode():
  device3 = EdgeDevice("abc",3)
  device4 = EdgeDevice("xyz",4)
  print device3
  print device4

  
  print "\nTesting toggle switch pin 3 of device 4 "
  device4.setPinState(3,1)
  device4.setPinState(3,1)
  device4.setPinState(3,0)

  print "\nTesting momentary switch pin 2 of device 3"
  device3.setPinState(2,1)
  device3.setPinState(2,1)
  device3.setPinState(2,0)

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-w', '--web', help='Run under web server',action="store_true")
  args = parser.parse_args()
  
  if args.web:
    print "Starting web server"
  else:
    print "Running testing in a terminal mode"
    testMode()
