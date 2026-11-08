# -*- coding: utf-8 -*-
"""
Created on Thu May 25 13:36:00 2017
@author: Bomoseen
"""

# Module for remote inerfacing of equipment

import serial

# Omega DP32PT Thermocouple reader
class TC:
    """ Thermoucouple controller

    """
    def __init__(self,Port):
        self.Port = Port
        self.Baud = 19200
        self.Parity = serial.PARITY_ODD
        self.Byte = serial.EIGHTBITS
        self.Stop = serial.STOPBITS_ONE
        self.TO = 0.05 # original was 1 second

        self.initialize()

    def initialize(self):
        get_current_process_value = "*G110 \r"
        self.gcpv = get_current_process_value.encode()
##        print self.gcpv
        
        self.ser = serial.serial_for_url(self.Port) # open the serial port
        self.ser.baudrate = self.Baud
        self.ser.parity = self.Parity
        self.ser.bytesize = self.Byte
        self.ser.stopbits = self.Stop
        self.ser.timeout = self.TO

    def print_info(self):
        """ print serial port info
        """
        print(self.ser)

    def _readline(self):
        """ Reads all bytes waiting in buffer
        """
        
        #self.ser.read(self.ser.in_waiting) # reads all bytes waiting in buffer

        # old code for previous version without in_waiting
        eol = b'\r'
        leneol = len(eol)
        line = bytearray()
        while True:
            c = self.ser.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    break
            else:
                break
        return bytes(line)

    def get_temp(self):
        # read the temperature
        self.ser.write(self.gcpv)
        self.temp = self.ser.readline()
        
        # decode the byte and split it by '+'
#        print('self.temp Raw Data', self.temp)
        temp_str = self.temp.decode().split('+')[1]
        # remove the carriage return at the end and convert it to a float
        self.temp = float(temp_str.strip('\r'))
        
        return round(self.temp, 1)

    def clear_buffer(self):
        print(self.ser.read_all())

    def close(self):
        self.ser.close()
