"""
Duplicate a UDP join packet to simulate multiple players connecting.

Usage:
    # Send 5 copies of a fake join packet to the game server
    python tools/sim_clients.py --count 5

    # Replay a captured packet (hex file from tcpdump/wireshark)
    python tools/sim_clients.py --packet join.bin --count 5

    # Paste a raw hex string directly
    python tools/sim_clients.py --hex 40f50197... --count 3

    # Keep connections alive with periodic heartbeats (resend full join each time)
    python tools/sim_clients.py --hex 40f50197... --count 5 --keepalive --resend

    # Listen for server responses while keeping alive
    python tools/sim_clients.py --hex 40f50197... --keepalive --listen

Capture a real join packet:
    sudo tcpdump -i any -w join.pcap udp port 7776 &
    # connect your client once
    # kill tcpdump, then extract the payload:
    tshark -r join.pcap -T fields -e data.data -Y udp > join.hex
    python -c "import sys; open('join.bin','wb').write(bytes.fromhex(open('join.hex').read().strip()))"
"""

import argparse
import socket
import threading
import time

TARGET_HOST     = '127.0.0.1'
TARGET_PORT     = 7777
BASE_LOCAL_PORT = 19000
HEARTBEAT_SECS  = 5

# Minimal UE4-style join URL — enough for the game server to see a connection attempt
DEFAULT_PACKET  = b'/Game/Maps/Lobby?Name=TestPlayer?game=solos?listen'


def listen_for_responses(sock: socket.socket, client_id: int) -> None:
    sock.settimeout(1.0)
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            print(f'  [{client_id}] recv {len(data)}b from {addr}: {data[:32].hex()}{"..." if len(data) > 32 else ""}')
        except socket.timeout:
            continue
        except OSError:
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host',      default=TARGET_HOST)
    parser.add_argument('--port',      type=int, default=TARGET_PORT)
    parser.add_argument('--count',     type=int, default=1, help='Number of simulated clients')
    parser.add_argument('--packet',    help='Raw binary file to use as the join packet')
    parser.add_argument('--hex',       help='Raw hex string to use as the join packet')
    parser.add_argument('--interval',  type=float, default=HEARTBEAT_SECS, help='Keepalive interval in seconds')
    parser.add_argument('--keepalive', action='store_true', help='Send periodic heartbeats')
    parser.add_argument('--resend',    action='store_true', help='Resend full join packet as heartbeat (default: null byte)')
    parser.add_argument('--listen',    action='store_true', help='Print server responses')
    args = parser.parse_args()

    if args.hex:
        packet = bytes.fromhex(args.hex.strip())
    elif args.packet:
        packet = open(args.packet, 'rb').read()
    else:
        packet = DEFAULT_PACKET

    target = (args.host, args.port)
    heartbeat = packet if args.resend else b'\x00'

    print(f'Sending {args.count} join packet(s) to {args.host}:{args.port}')
    print(f'Packet ({len(packet)}b): {packet[:32].hex()}{"..." if len(packet) > 32 else ""}')
    if args.keepalive:
        mode = 'full resend' if args.resend else 'null byte'
        print(f'Keepalive every {args.interval}s ({mode})')

    sockets = []
    for i in range(args.count):
        local_port = BASE_LOCAL_PORT + i
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', local_port))
        sock.sendto(packet, target)
        sockets.append(sock)
        print(f'  [{i+1}] sent from :{local_port}')
        if args.listen:
            t = threading.Thread(target=listen_for_responses, args=(sock, i + 1), daemon=True)
            t.start()

    if not args.keepalive:
        for sock in sockets:
            sock.close()
        return

    print(f'\nHolding {args.count} session(s) alive — Ctrl+C to stop...')
    try:
        while True:
            time.sleep(args.interval)
            for i, sock in enumerate(sockets):
                sock.sendto(heartbeat, target)
            if not args.listen:
                print(f'  heartbeat × {args.count}  ({time.strftime("%H:%M:%S")})')
    except KeyboardInterrupt:
        print('\nDone.')
    finally:
        for sock in sockets:
            sock.close()


if __name__ == '__main__':
    main()
