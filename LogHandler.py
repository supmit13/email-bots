"""
A very basic logger: Trying to keep things simple
"""

import os, sys, re, time

class Logger(object):
    DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    def __init__(self, logfile):
        self.logfilename = os.path.basename(logfile)
        self.logpath = os.path.dirname(logfile)
        if not os.path.exists(self.logpath) or not os.path.isdir(self.logpath):
            os.makedirs(self.logpath)
        self.loghandle = open(logfile, "w")
        self._state = True
        local_t = time.localtime()
        self.datetime = self.__class__.DAYS[local_t[6]] + ", " + self.__class__.MONTHS[local_t[1]] + " " + local_t[2].__str__() + ", " + local_t[0].__str__()
        self.loghandle.write("Initializing EmailBot logger - %s\n"%(self.datetime))

    def write(self, message):
        self.loghandle.write(message.__str__() + "\n")
	self.loghandle.flush()

    def close(self):
	self.loghandle.flush()
        self.loghandle.close()

