# module for remote interfacing with BK PRECISION XLN3640

import serial

#PORT = 'COM9' # Double check the port is right

# These are the specs from the XLN manual
BAUDRATE = 57600
BYTESIZE = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_ONE
TIMEOUT = 1

# Carriage return and line feed codes from XLN Manual
CR = str(chr(0x0D)).encode()
LF = str(chr(0x0A)).encode()

# Some relevant commands from the XLN Manual
GET_ID = "*IDN?"
GET_IOUT = "IOUT?" 
ISET = "ISET " 
GET_ISET = "ISET?" 
GET_VOUT = "VOUT?"
VSET = "VSET "
GET_VSET = "VSET?"
OUTPUT = "OUT " # Pass a 1 to enable, or 0 to disable
GET_OUT = "OUT?"
GET_MODE = "OUT:STATe?" # C.V or C.C, only returns CV or CC is output is on, else it returns OFF


class XLN3640:
    """ BK Precision XLN3640 Power Supply Controller"""
    def __init__(self,PORT):
        self.ser = serial.Serial(PORT)
        self.ser.baudrate = BAUDRATE
        self.ser.parity = PARITY
        self.ser.bytesize = BYTESIZE
        self.ser.stopbits = STOPBITS
        
    def calculate_power(self):
        '''calculates power in watts'''
        voltage = self.get_voltage()
        current = self.get_current()
        power = voltage * current
        power = round(power, 3)
        return power
        
        
    def calculate_resistance(self):
        '''calculates resistance'''
        self.voltage = self.get_voltage()
        self.current = self.get_current()
        
        if self.current != 0:
            return round(self.voltage/self.current, 3)
        else:
            return 0      

    def close(self):
        """ Close the serial port """
        self.ser.close()  
        
    def get_current(self):
        """ Returns the output current as a float"""
        self._write_command(GET_IOUT)
        return(float(self._read_return()))
        
    def get_current_setpoint(self):
        """ Returns the output current as a float"""
        self._write_command(GET_ISET)
        return(float(self._read_return()))
        
    def get_mode(self):
        """ Returns the operating mode """
        self._write_command(GET_MODE)
        return(self._read_return())  
    
    def get_output(self):
        """ Returns the output state """
        self._write_command(GET_OUT)
        return(self._read_return())  
        
    def get_voltage(self):
        """ Returns the output voltage as a float"""
        self._write_command(GET_VOUT)
        return(float(self._read_return()))
    
    def get_voltage_setpoint(self):
        """ Returns the output voltage as a float"""
        self._write_command(GET_VSET)
        return(float(self._read_return()))            

    def _read_return(self):
        """ Read the return from the pyserial input buffer
        
        Read until hitting a line feed. All returns from the XLN3640 are 
        terminated with the carriage return and line feed characters. Cut off
        line feed and carriage return and returns a string
        """
        cur = b''
        ret = b''
        while cur != LF:
            cur = self.ser.read()
            ret = ret + cur
            if cur == b'':
                print('nothing to read??')
                break
        return (ret[0:len(ret)-2]).decode()
    
    def set_current(self, i):
        """ Sets the current to c"""
        self._write_command(ISET + str(i))    
        
    def set_output(self, x):
        """ Enable/Dsiable Output """
        self._write_command(OUTPUT + str(x))

    def set_voltage(self, v):
        """ Sets the voltage to v"""
        self._write_command(VSET + str(v))    

    def _write_command(self, command):
        """ Change a string into a command and send it to the XLN3640
        
        All commands sent to the XLN3640 must be terminated with a carriage
        return followed by a line feed
        """
        command = command.encode() + CR + LF
        self.ser.write(command)
   