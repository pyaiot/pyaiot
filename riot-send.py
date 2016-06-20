"""Test UDP packet sending."""

import socket

UDP_IP = "localhost"
UDP_PORT = 8888
MESSAGE = "2001:db8:abad::20".encode()

print("UDP target IP: {0}".format(UDP_IP))
print("UDP target port:{0}".format(UDP_PORT))
print("message:{0}".format(MESSAGE))

sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_DGRAM)  # UDP
sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
