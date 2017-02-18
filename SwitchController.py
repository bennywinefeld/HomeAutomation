import string, cherrypy, HTML, os, sys, argparse


'''==============================================================
   Section 1 - classes supporting communication with edge devices
  ==============================================================='''
def enum(**enums):
    return type('Enum', (), enums)

# Enumerated types for pins of the edge devices
PinTypes = enum(momentary_switch='momentary_switch', toggle_switch='toggle_switch',digital_input='digital_input', analog_input='analog_input')

class ControlHub:
  def __init__(self,name):
    self.name = name
    self.edgeDevices=[]

  def __repr__(self):
    text = self.name
    for device in self.edgeDevices:
      text += "\n" + device.getInfo()
    return text

  def addEdgeDevice(self,device):
    self.edgeDevices.append(device)

  def getEdgeDevice(self,id):
    for device in self.edgeDevices:
      if device.id == id:
        return device

    print '''Error, can't find device %d in  %s''' % (id, self.name)

  def showAsHtml(self):
    text = "<html><h2>" + self.name + "</h2>\n<table>"
    for device in self.edgeDevices:
      text += "\n " + device.showAsHtml()
    text += "\n</table>\n</html>"
    return text

# Each instance of this class controls one edge device with few pin switches which can be set to either 0 or 1 
# pin can control optocoupler, relay or led 
# Every edge device must have unique ID 
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
    return getInfo(self)

  def getInfo(self):
    text = " device name=" + self.name + " id=" + str(self.id) 
    for pinId in sorted(self.pins.keys()):
      text += "\n  " + self.pins[pinId].getInfo()  
    return text

  def setPinState(self,pinId,pinValue):
    pin = self.pins[pinId]
    pin.setState(pinValue)

  def showAsHtml(self):
    text = '''<tr><td colspan="3" bgcolor="cyan"> device %s id=%d </td> </tr>''' % (self.name,self.id)
    for pinId in sorted(self.pins.keys()):
      pin = self.pins[pinId]
      text += pin.showAsHtml()
    return text

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

  # Return info (name, state) about this pin object in gets format
  def __repr__(self):
    return getInfo(self)

  def getInfo(self):
    return "device " + str(self.deviceId) + " pin " + str(self.id) + " type=" + self.type + " state=" + str(self.state)

  # Show table html representation for the web server
  def showAsHtml(self):
    return "\n   <tr><td> %d </td> <td> %s </td> <td> %d </td>" % (self.id, self.type, self.state)  
  
'''
================================================================
    Section 2 - web interface 
==============================================================='''
class MainServer(object):

  def __init__(self):
    print "MainServer initialized"

    # Temporarily hardcode creation of edge devices
    device3 = EdgeDevice("abc",3)
    device4 = EdgeDevice("xyz",4)


  
  # This is the entry point to the web interface
  @cherrypy.expose
  def index(self):
    text = "<html><h2> Switch controller</h2>"
    #t = HTML.Table(header_row=["Edge device name","ID","State"])
    text += '''
<table>
  <tr>
    <td colspan="3" bgcolor="cyan"> Device </td> 
  </tr>
  <tr>
    <td >Pin id</td>
    <td>type</td>
    <td>Toggle</td>
  </tr>
  <tr>
    <td colspan="2">This</td>
    <td>Little</td>
    <td>Piggy</td>
    <td>Went</td>
    <td>To</td>
  </tr>
    <tr>
    <td colspan="4">This</td>
    <td rowspan="3">Little</td>
    <td>Piggy</td>
  </tr>
  <tr>
    <td rowspan="2">This</td>
    <td>Little</td>
    <td>Piggy</td>
    <td>Went</td>
    <td>To</td>
  </tr>
  <tr>
    <td>Little</td>
    <td>Piggy</td>
    <td>Went</td>
    <td>To</td>
  </tr>
</table>
'''

    return text

'''
=================================================================
    Section 3 - testing and main proc
================================================================='''
def testMode():
  myHub = ControlHub("Switch controller hub")
  myHub.addEdgeDevice(EdgeDevice("abc",3))
  myHub.addEdgeDevice(EdgeDevice("xyz",4))
  print myHub
  
 

  print "\nTesting momentary switch pin 2 of device 3"
  device3 = myHub.getEdgeDevice(3)
  device3.setPinState(2,1)
  device3.setPinState(2,1)
  device3.setPinState(2,0)
  device3.setPinState(2,1)

  print "\nTesting toggle switch pin 3 of device 4 "
  device4 = myHub.getEdgeDevice(4)
  device4.setPinState(3,1)
  device4.setPinState(3,1)
  device4.setPinState(3,0)
  
  print myHub.showAsHtml()

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-w', '--web', help='Run under web server',action="store_true")
  args = parser.parse_args()
  
  if args.web:
    print "Starting web server"
    cherrypy.config.update({'server.socket_host': '0.0.0.0','server.socket_port': 8090})
    cherrypy.tree.mount(MainServer(),"/","main.cfg") 
    #cherrypy.quickstart(MainServer())
    cherrypy.engine.start()
    cherrypy.engine.block()

  else:
    print "Running testing in a terminal mode"
    testMode()
