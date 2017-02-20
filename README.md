# HomeAutomation
Code and sketches for hobby home automation project

First sub-project control of mattress heaters

Brief description of the communication protocol
'''
Packet format: <sender_id> <receiver_id> <command_code> <LSB_byte> <MSB_byte>
 Board ids should start with 1, first byte equal 0 means - address all listening Arduino boards
 Commands:
  0xA1 <value> - return passed lsb + msg back to check communication
  0xA2 <digital_pin_id> <0|1>  - set digital pin mode, 0 - input, 1 - output
  0xA3 <digital_pin_id> - digital read
  0xA4 <digital_pin_id> <0|1> - digital write
  0xA5 <analog_pin_id> - analog read
  0xA6 <analog_pin_id> <0-255> - analog (pwm) write
  0xA7  - measure and return Vcc value

 For every packet sent we expect packet sent back from Arduino in the following format:
  <board_id> <command_completion_status> <LSB_byte> <MSB_byte>'''