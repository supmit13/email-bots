# This module contains various utility functions.

import os, sys, re, time
import GeoIP
import socket
import socks
import StringIO
import mimetypes, mimetools

urlPattern = re.compile(r"^https?:\/\/([^\/]+)/?.*$", re.IGNORECASE)

def getUrlDirPathFromUrl(url):
    urlParts = url.split("/")
    urlPath = "/".join(urlParts[0:-1])
    return (urlPath)


def getCountryNameFromIP(ipaddr):
    gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
    return(gi.country_name_by_addr(ipaddr))


def getIPAddrFromUrl(urlStr):
    urlSearch = urlPattern.search(urlStr)
    if urlSearch:
	hostname = urlSearch.groups()[0]
	return(socket.gethostbyname(hostname))
    else:
	return None


# Read a configuration file with the following basic format:
# Each line contains a config parameter and its value of the form 'param=value'.
# Parameter names may not contain spaces. Values may contain spaces and should
# always be terminated by newline character or '#' character (comment character).
# Parameter names and values are separated by a '=' sign. Whitespaces around the
# '=' sign are trimmed when the line is processed by this function. Whitespace
# characters may also be present at the start and end of a line. These are also
# trimmed while processing the line. Lines may also contain comments. Comments
# always start with '#'. Everything succeeding a '#' character is ignored by 
# this function. Lines may also be empty (containing 0 or more spaces). Comments 
# lines and empty lines are ignored during processing.
def readBasicConfig(cfgfile):
    if not os.path.exists(cfgfile) or not os.path.isfile(cfgfile):
	print "Config file ('%s') does not exist. Please specify the full path to the config file as the first argument of your program if it is not in the default location.\n"
	return(None)
    fcfg = open(cfgfile)
    configContents = fcfg.read()
    fcfg.close()
    config = {}
    configLines = configContents.split("\n")
    commentPattern = re.compile(r"^#")
    for line in configLines:
	line = line.strip()
	commentSearch = commentPattern.search(line)
	if line == "" or commentSearch:
	    continue
	param, value = line.split("=")
	param = param.strip()
	value = value.strip()
	valuesparts = list(value.split("#"))
	if valuesparts.__len__() > 1:
	    value = valuesparts[0].strip()
	    config[param] = value
	else:
	    config[param] = value
    return(config)


# Clone a config dict with the passwd info blanked out.
def _cloneConfig(cfgDict):
    cloneConfig = {}
    passwdKeyPattern = re.compile(r"passwo?r?d", re.IGNORECASE)
    for cfgKey in cfgDict.keys():
	if passwdKeyPattern.search(cfgKey):
	    cloneConfig[cfgKey] = "********"
	else:
	    cloneConfig[cfgKey] = cfgDict[cfgKey]
    return(cloneConfig)


def getContextualFilename(acctId, contextString=None):
    contextualFilename = acctId
    contextualFilename = re.sub(re.compile(r"@"), "_", contextualFilename)
    contextualFilename = re.sub(re.compile(r"\."), "_", contextualFilename)
    contextString = re.sub(re.compile(r"\s+"), "_", contextString)
    contextualFilename = contextualFilename + "_" + contextString.lower()
    return(contextualFilename)


def cleanNonFilenameCharacters(s):
    s = re.sub(re.compile(r"[\-:\"\'\*&\.\]\[\}\{\)\(\/\\]+"), "", s)
    s = re.sub(re.compile(r"[\s\-]+"), "_", s)
    s = re.sub(re.compile(r"<[^>]+>", re.MULTILINE | re.DOTALL), "", s)
    return(s)


# Function to check if a file is a binary file or not (ASCII text file).
# Return true if the given filename appears to be binary.
# File is considered to be binary if it contains a NULL byte.
# TODO: This approach incorrectly reports UTF-16 as binary. Need to fix this.
def fileIsBinary(filename):
    with open(filename, 'rb') as f:
        for block in f:
            if '\0' in block:
                return True
    return False


# Function to check if a file is a binary file or not (ASCII text file).
# Return true if the given data appears to be binary.
# Data is considered to be binary if it contains a NULL byte.
# TODO: This approach incorrectly reports UTF-16 as binary. Need to fix this.
def dataIsBinary(data):
    if "\0" in data:
	return (True)
    return (False)


# Function to merge 2 dicts to form a 3rd dict. If dict1 has one or more keys
# common to dict2, then the values for those keys in dict3 will be the ones
# specified for dict2.
def mergeDicts(dict1, dict2):
    dict3 = dict(dict1.items() + dict2.items())
    return (dict3)


def dumpCsvHeader(filehndl):
    if (filehndl.mode != 'w' and filehndl.mode != 'wb') or filehndl.closed == True:
	print "_dumpCsv: filehandle is unusable.\n"
	return None
    headerline = ""
    for attrib in cls._supported_attribs:
	headerline += attrib + ","
    headerline = headerline[:-1] + "\n"
    filehndl.write(headerline)
    return(headerline)



def dumpCsvData(filehandle):
    if (filehandle.mode != 'w' and filehandle.mode != 'wb') or filehandle.closed == True:
	print "_dumpCsv: filehandle is unusable.\n"
	return None
    else:
	line = ""
	for attrib in self.__class__.supportedAttributes():
	    line += "\"" + self.__dict__[attrib.lower()] + "\","
	line = line[0:-1]
	uline = line.encode('utf-8') # handle unicode
	filehandle.write(uline + "\n")
    return (uline + "\n")

    
def dumpXmlData(self, filehandle):
    if (filehandle.mode != 'w' and filehandle.mode != 'wb') or filehandle.closed == True:
	print "_dumpXml: filehandle is unusable.\n"
	return None
    else:
	pass # Handle the data here


def decodeHtmlEntities(content):
    entitiesDict = {'&nbsp;' : ' ', '&quot;' : '"', '&lt;' : '<', '&gt;' : '>', '&amp;' : '&', '&apos;' : "'", '&#160;' : ' ', '&#60;' : '<', '&#62;' : '>', '&#38;' : '&', '&#34;' : '"', '&#39;' : "'"}
    for entity in entitiesDict.keys():
    	content = content.replace(entity, entitiesDict[entity])
    return(content)


def cleanUp(content):
    content = content.replace("\\n", " ")
    content = re.sub("\s+", " ", content) # replace multiple whitespaces with a single whitespace.
    content = content.replace('"', '') # remove double quotes from 'content'
    content = content.replace("\\t", " ")
    return(content)


# TODO: Method to sort CSV file on one or more fields.
# This method will have the following arguments: 
# i)  The name of the CSV file that is to be sorted.
# ii) The inde(x/ices) of the field(s) on which the sorting is to be done (as a list).
# iii)A list containing of the datatypes of the fields on which the records are being sorted.
# The function will return the records as a list of lists.
def sortCsv(filename, indices, datatypes):
    pass


# Implement signal handler for ctrl+c here.
def setSignal():
    pass


# Test script.
if __name__ == "__main__":
    cfg = readBasicConfig("../config/GmailBot.cfg")
    for cfgkey in cfg.keys():
	print cfgkey + " ======= " + cfg[cfgkey]
    print "Done!"
    
