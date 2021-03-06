#!/usr/bin/env python
"""
.. module:: temperature
    :platform: unix
    :synopsis: This module is for communicating with the temperature sensor.

.. codeauthor:: Michael Coughlin, Eric Coughlin

.. warning:: This module is currently inactive
"""

import serial, sys, time, glob, struct, os
import numpy as np
import optparse
import pexpect

class Temperature:
    """
    This is the class for communicating with the temperature sensor.
    """
    def __init__(self):
        self.status = None
        self.serial = self.create_serial()

    def create_serial(self):
        """
        This method returns the serial connection to the sensor

        :return: a serial connection that is ostensibly from the sensor
        """
        try:
            PORT = '/dev/ttyACM.TEMP'
            BAUD_RATE = 9600
            ser2 = serial.Serial(PORT, BAUD_RATE)
            self.status = "connected"
            return ser2
        except Exception as e:
            print(e)
            self.status = "not connected"

    def check_status(self):
        """
        This method checks the status of the sensor

        :return:
        """
        try:
            self.receiving()
        except Exception as e:
            self.status = "not connected"

    def receiving(self):
        """
        This method returns the last message received from the port.

        :return:
        """
        if self.status != "not connected":
            ser = self.serial
            buffer_string = ''
            last_received = ''
            while last_received == "":
                buffer_string = buffer_string + ser.read(ser.inWaiting())
                if '\n' in buffer_string:
                    lines = buffer_string.split('\n')  # Guaranteed to have at least 2 entries
                    last_received = lines[-2]
                    # If the Arduino sends lots of empty lines, you'll lose the
                    # last filled line, so you could make the above statement conditional
                    # like so: if lines[-2]: last_received = lines[-2]
                    buffer_string = lines[-1]

            return last_received
        else:
            pass

    def get_temperature(self):
        """
        This method returns the temperature reading from the sensor.

        :return:
        """
        if self.status != "not connected":
            ser2 = self.serial
            conversion = 1.0

            success = 0
            numlines = 5
            linenum = 0
            data_out_1 = None
            while success == 0:
                line = self.receiving()
                if linenum < numlines:
                    linenum = linenum + 1
                    continue
                line = line.replace("\n", "").replace("\r", "")
                lineSplit = line.split(" ")
                lineSplit = filter(None, lineSplit)

                if not len(lineSplit) == 1:
                    continue

                data_out_1 = float(lineSplit[0])
                data_out_1 = data_out_1 / conversion

                success = 1

            return data_out_1
        else:
            pass

    def do_compile(self):
        """
        This method compiles the arduino code for the sensor.

        :return:
        """
        if self.status != "not connected":
            steps_command = "cd /home/pi/Code/arduino/Temperature/; ./compile.sh"
            os.system(steps_command)
        else:
            pass

    def do_photodiode(self):
        """
        This method returns the temperature reading from the sensor.

        :return:
        """
        if self.status != "not connected":
            temp = self.get_temperature()
            conv = (0.5 / 10.0)  # 0.5 mv/1 bit * 1 degree C / 10 mV
            temp = temp * conv
            print "Temperature: %.2f" % temp
            return temp
        else:
            pass

def parse_commandline():
    """
    Parse the options given on the command-line.
    """
    parser = optparse.OptionParser()

    parser.add_option("-c","--compile", action="store_true",default=False)
    parser.add_option("--doTemperature", action="store_true",default=False)
    parser.add_option("--doCompile", action="store_true",default=False)

    opts, args = parser.parse_args()

    return opts

def main(runtype = "compile", val = 0):
    temperature = Temperature()

    if runtype == "compile":
        temperature.do_compile()
    elif runtype == "photodiode":
        temperature.do_photodiode()

if __name__ == "__main__":

    # Parse command line
    opts = parse_commandline()

    if opts.doCompile:
        main(runtype = "compile")
    if opts.doTemperature:
        main(runtype = "photodiode")

