"""Test UDP packet sending."""

import socket


def send(args):
    """Send an UDP message containing an IP address."""
    target_ip = args.ip
    target_port = args.port
    source_ip = args.source

    print("UDP target IP: {0}".format(target_ip))
    print("UDP target port:{0}".format(target_port))
    print("Source IP:{0}".format(source_ip))

    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.sendto(source_ip.encode(), (target_ip, target_port))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RIOT UDP paquet sender")
    parser.add_argument('--ip', type=str, default="localhost",
                        help="UDP target IP.")
    parser.add_argument('--port', type=int, default=8888,
                        help="UDP target port.")
    parser.add_argument('--source', type=str, default='2001:db8:abad::10',
                        help="Source IP.")
    send(parser.parse_args())
