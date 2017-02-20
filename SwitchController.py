import string, cherrypy, os, sys, argparse, time, sys
try:
  from radioComm import *
except:
  print "Can't load radio module, will run in emulation mode"
  def sendMessage(*args):
    print "sendMessage is invoked, but not executed"


def dbgPrint(msg):
    currTime = time.strftime("%d %b %Y %H:%M:%S", time.localtime())
    print "[" + currTime + "] " + msg

def enum(**enums):
    return type('Enum', (), enums)


'''==============================================================
   Section 1 - classes defining behavior of the structure 
    ControlHub -> EdgeDevice/s -> Pin/s
  ==============================================================='''


# Enumerated types for pins of the edge devices
PinTypes = enum(momentary_switch='momentary_switch', toggle_switch='toggle_switch',digital_input='digital_input', analog_input='analog_input')

# This is an ID of the control hub, this numbe will be sent as a first byt in all communication packets to edge devices
CONTROL_HUB_ID = 1

# Instance of ControlHub contains a list of edge device objects
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

  # Return edge device object  by its id
  def getEdgeDevice(self,id):
    for device in self.edgeDevices:
      if device.id == id:
        return device

    dbgPrint('''Error, can't find device %d in  %s''' % (id, self.name))

  # This function starts forming the main web page (table with device and pin status)
  # refresh meta tag insures periodic refresh of the web page, which means that showAsHtml function 
  # gets periodically executed 
  def showAsHtml(self):
    tm = time.localtime()
    timeStamp = time.strftime("%d %b %Y %H:%M:%S", tm)
    text = '''
    <html> <meta http-equiv="refresh" content="5" />
      <h2> %s </h2>
      <table border=1>''' % self.name

    for device in self.edgeDevices:
      # For all pins of all edge devices compare current with startTime and
      # endTime and set status to 1 or 0 correspondingly
      device.refreshPinState()
      text += "\n " + device.showAsHtml()
    text += '''
      </table>
      <div><br> %s </div>
    </html> ''' % timeStamp
    
    return text

# Each instance of this class controls one edge device with few pin switches which can be set to either 0 or 1 
# pin can control optocoupler, relay or led. Every edge device must have unique ID 
class EdgeDevice:
  def __init__(self,deviceId,deviceName,pins):
    self.name = deviceName
    self.id = deviceId
    self.pins = {}
    
    # Initialize pin objects belonging to this edge device
    # passed var pins is a list of tuples, each consists of 4 parms:
    for pin in pins:
      (pinId, pinType, startTime, endTime) = pin

      # class var 'pins' is a dictionary whose keys are pinId's and values are Pin objects
      self.pins[pinId] = Pin(deviceId, pinId, pinType, startTime, endTime)

  # Get a hash of name-value parameters from configureEdgeDevice web form 
  # and store this parms as appropriate member vars of the edge device
  # object and its pin objects
  def configure(self,parmHash):
    for key, value in parmHash.iteritems():
      if (key=="deviceId"):
        continue
      (pinId, parmName) = key.split(":")
      pinId = int(pinId)
      pin = self.pins[pinId]
      if (parmName == "startTime"):
        pin.startTime = value
      elif (parmName=="endTime"):
        pin.endTime = value
      elif (parmName=="state"):
        pin.setState(int(value))

  # Update pin state depending on current time
  def refreshPinState(self):
    for pinId in sorted(self.pins.keys()):
      pin = self.pins[pinId]
      pin.refreshPinState()

  def __repr__(self):
    return getInfo(self)

  # Print textual information about this edge device
  def getInfo(self):
    text = " device name=" + self.name + " id=" + str(self.id) 
    for pinId in sorted(self.pins.keys()):
      text += "\n  " + self.pins[pinId].getInfo()  
    return text

  # This prints a portion of main HTML table describing the info of this edge device and status of all its pins
  def showAsHtml(self):
    configure_btn = '''
    <form method="get" action="configureEdgeDevice">
      <button  name="device_id" value ="%d" type="submit"/>Configure
    </form>''' % self.id

    text = '''
      <tr>
        <td colspan="5" bgcolor="cyan"> %s (id=%d) %s</td> 
      </tr>''' % (self.name,self.id,configure_btn)
    text += "<tr><td>pin id</td> <td>pin type</td> <td>pin state</td> <td>Turn on at</td> <td>Turn off at</td></tr>"
    for pinId in sorted(self.pins.keys()):
      pin = self.pins[pinId]
      text += pin.showAsHtml()
    return text

  # Display HTML form containing all the fields necessary for configuration of this edge device 
  def showConfigDialog(self):
    text = '''
    <html>
      <b>Configuring edge device: %s (id=%d)</b>
      <form method="get" action="submitEdgeDeviceConfig">''' % (self.name, self.id)

    # Print configuration web form sections for each pin
    for pinId in sorted(self.pins.keys()):
      pin = self.pins[pinId]
      text += pin.showConfigDialog()

    # Finish web form configuring edge device with Submit button
    text += '''
      <div>
          <br>
          <button  name="deviceId" value ="%d" type="submit">Submit</button>
          <button  name="deviceId" value = -1 type="submit">Cancel</button>
      </div>
      </form>
    </html>''' % self.id
    return text



# One pin on the edge device:
# Edge device pin can be of the following types:
#  momentary_switch, toggle_switch, digital_input, analog_input
class Pin:
  def __init__(self, deviceId, pinId, pinType, startTime, endTime):
    self.deviceId = deviceId
    self.id = pinId
    self.type = pinType
    self.state = 0
    # Time for automatic turn/on turn off
    self.startTime = startTime
    self.endTime = endTime

  # This function actually sneds radio signal to edge device
  def sendSequenceToEdgeDevice(self,sequence):
    dbgPrint("Sending sequence " + str(sequence) + " to pin " + str(self.id) + " of device " + str(self.deviceId))
    for bit in sequence:
      # <sender_device_id>, <receiver__device_id>, <command_code>, <pin_id>, 0/1
      sendMessage(CONTROL_HUB_ID,self.deviceId,0xA4,self.id,bit)
  
  # For output pin - set pin state and send signal to edge device
  def setState(self, pinValue):
    # Reject attempt to set value for input pin
    if (not (self.type==PinTypes.momentary_switch or PinTypes.toggle_switch)):
      dbgPrint("Can't set value to a pin " + pinId + " which is not an output switch") 
      return
    
    # If current pin state is alredy equal to speciefied pinValue - no need to do anything
    if (pinValue == self.state):
      #dbgPrint("Pin " + str(self.id) + " of device " + str(self.deviceId) + " is already at state " + str(self.state))
      return

    # For toggle switch, simple send signal to edge device resulting in 
    # setting its physical out pin with id identical to self.id to a specified value
    if (self.type == PinTypes.toggle_switch):
      self.sendSequenceToEdgeDevice([pinValue])
    elif (self.type == PinTypes.momentary_switch):
      self.sendSequenceToEdgeDevice([0,1,0])
    # Remember the state value
    self.state = pinValue
    # Let the receiving edge device time to process the packet before sending something new
    time.sleep(0.2)

  # Update pin state depending on current time
  def refreshPinState(self):
    tm = time.localtime()
    #timeStamp = time.strftime("%d %b %Y %H:%M:%S", tm)

    if ((self.startTime == '---') or (self.endTime == '---')):
      return

    (startHr, startMin) = map(int,self.startTime.split(":"))
    (endHr, endMin) = map(int,self.endTime.split(":"))
    if (tm.tm_hour==startHr and tm.tm_min == startMin and self.state == 0):
      dbgPrint("refreshing state of pin %d of device %d to 1" % (self.id, self.deviceId))
      self.setState(1)
    elif (tm.tm_hour==endHr and tm.tm_min == endMin and self.state == 1):
      self.setState(0)
      dbgPrint("refreshing state of pin %d of device %d to 0" % (self.id, self.deviceId))

  # Return info (name, state) about this pin object in gets format
  def __repr__(self):
    return getInfo(self)

  def getInfo(self):
    return "device " + str(self.deviceId) + " pin " + str(self.id) + " type=" + self.type + " state=" + str(self.state)

  # Show table html representation for the web server
  def showAsHtml(self):
    return "\n   <tr><td>%d</td> <td>%s</td> <td>%d</td> <td>%s</td> <td>%s</td>" % (self.id, self.type, self.state, self.startTime, self.endTime)  

  # Display pin configuration dialog web form
  def showConfigDialog(self): 
    if self.state:
      is_on = "checked"
      is_off = ""
    else:
      is_on = ""
      is_off = "checked"  

    text = '''
      <div>
        <br>Pin %d
          <div>
            Current state 
            <input type="radio" %s name="%d:state" value=1> ON
            <input type="radio" %s name="%d:state" value=0> OFF
          </div>
          <div>
            Start time  <input type="text" name="%d:startTime" value="%s"/>
            End time  <input type="text" name="%d:endTime" value="%s"/>
          </div>
      </div>''' % (self.id,is_on,self.id,is_off,self.id,self.id,self.startTime,self.id,self.endTime)
  
    return text

'''
================================================================
    Section 2 - web interface 
==============================================================='''
class MainServer(object):

  def __init__(self):
    print "MainServer initialized"
    self.css = '''td {
      border: solid thin;
      text-align: center;
    }'''

 
  # This is the entry point to the web interface
  # force refresh of the main page every 5 sec
  @cherrypy.expose
  def index(self):
    return '''<html> <meta http-equiv="refresh" content="5" />''' + myHub.showAsHtml() + "</html>"

  # This function calls edge device dialog web form
  # Notice that parameter name must be device_id to match showAsHtml function of EdgeDevice Class
  @cherrypy.expose
  def configureEdgeDevice(self,device_id):
    selectedEdgeDevice = myHub.getEdgeDevice(int(device_id))
    return selectedEdgeDevice.showConfigDialog()

  # This function gets executed when user clicks on Submit button on a form generated by 
  # selectedEdgeDevice.showConfigDialog()
  @cherrypy.expose
  def submitEdgeDeviceConfig(self,**kwargs):
    ''' configureEdgeDevice webform returns results in following key-value pair format
2:startTime = 21:30
2:state = 1
2:endTime = 22:21
3:startTime = ---
deviceId = 3
3:state = 0
3:endTime = ---'''

    # Extract device id, get correspondent edge device object and 
    # pass all the parameters collected from configureEdgeDevice form to edge device
    # configure function. Then simply return to the main page
    for key, value in kwargs.iteritems():
      if (key=="deviceId"):
        # deviceId value of -1 indicates that user clicked on Cancel button
        if (value != "-1"):
          myEdgeDevice = myHub.getEdgeDevice(int(value))
          myEdgeDevice.configure(kwargs)
      
    # Go back to main page
    return "<html>" + myHub.showAsHtml() + "</html>"


'''
=================================================================
    Section 3 - testing and main proc
================================================================='''
def testMode(): 
  print myHub
  print myHub.showAsHtml()

if __name__ == '__main__':
  # Create control hub no.1 with two edge devices
  myHub = ControlHub("Switch control hub")
  
  # Initializate edge devices
  myHub.addEdgeDevice(EdgeDevice(3,"Yasha's mattress heater", \
  [[2, PinTypes.momentary_switch, "21:30","22:20"], \
  [3, PinTypes.toggle_switch,"---","---"]] \
  ))
 
  myHub.addEdgeDevice(EdgeDevice(4,"Gila's mattress heater ", \
  [[2, PinTypes.momentary_switch, "22:30","23:10"], \
  [3, PinTypes.toggle_switch,"---","---"]] \
  ))  

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


'''
       

    except KeyboardInterrupt:
        print("Cleaning up...")
        radio.end()
        GPIO.cleanup()'''