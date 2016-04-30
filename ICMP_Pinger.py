from socket import *
import os
import sys
import struct
import time
import select
import binascii
import socket

ICMP_ECHO_REQUEST = 8
rtt = [] # to calculate avg RTT / min, max
pkgRecv = 0 # calculate loss rate
pkgSent = 0


def checksum(str):
    csum = 0
    countTo = (len(str) / 2) * 2
    count = 0
    while count < countTo:
        thisVal = ord(str[count+1]) * 256 + ord(str[count])
        csum = csum + thisVal
        csum = csum & 0xffffffffL
        count = count + 2
    if countTo < len(str):
        csum = csum + ord(str[len(str) - 1])
        csum = csum & 0xffffffffL
    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
    global rtt, pkgRecv
    timeLeft = timeout
    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []: # Timeout
            return "Request timed out. 1"
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)
        #Fill in start
        #Fetch the ICMP header from the IP packet
        icmphead = recPacket[20:28]
        reqtype, reqcode, checksum, packetid, sequence = struct.unpack('bbHHh',icmphead)
        if ID == packetid:
            bytes = struct.calcsize('d')
            timeSent = struct.unpack('d',recPacket[28:28 + bytes])[0]
            rtt.append(timeReceived - timeSent)
            pkgRecv = pkgRecv + 1
            return timeReceived - timeSent
        else:
            return "ID does not match"
        #Fill in end

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out. 2"

def sendOnePing(mySocket, destAddr, ID):
    global pkgSent
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    myChecksum = 0
    # Make a dummy header with a 0 checksum.
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)
    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        myChecksum = socket.htons(myChecksum) & 0xffff
        #Convert 16-bit integers from host to network byte order.
    else:
        myChecksum = socket.htons(myChecksum)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
    pkgSent = pkgSent + 1
    #Both LISTS and TUPLES consist of a number of objects
    #which can be referenced by their position number within the object

def doOnePing(destAddr, timeout):
    icmp = socket.getprotobyname("icmp")
    #SOCK_RAW is a powerful socket type. For more details see:http://sock-raw.org/papers/sock_raw

    #Fill in start
    #Create Socket here
    try:
        mySocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    #Fill in end

        myID = os.getpid() & 0xFFFF  #Return the current process id
        sendOnePing(mySocket, destAddr, myID)
        delay = receiveOnePing(mySocket, myID, timeout, destAddr)
        mySocket.close()
        return delay
    except socket.error, (errno, msg):
        if errno == 1:
            raise socket.error(msg)

def ping(host, timeout=1):
    #timeout=1 means: If one second goes by without a reply from the server,
    dest = socket.gethostbyname(host)
    print "Pinging " + dest + " using Python:"
    print ""
    #Send ping requests to a server separated by approximately one second
    counter = 0
    while (counter < 5) :
        delay = doOnePing(dest, timeout)
        print delay
        counter = counter + 1
        time.sleep(1)# one second
    return delay

def calcRTT():
    global rtt, pkgSent, pkgRecv
    try:
        print "Round Trip Times"
        print "---------------"
        print "Loss rate: ", float(pkgSent-pkgRecv)/pkgSent*100, "%"
        print "min: ", min(rtt)
        print "max: ", max(rtt)
        print "average: ", sum(rtt)/len(rtt)
    except ValueError:
        print "ValueError: no numbers"


if __name__ == '__main__':
    ping("www.utm.utoronto.ca")
    calcRTT()
