from pythonosc import dispatcher
from pythonosc import osc_server

def print_handler(address, *args):
    print(f"Received message at {address}: {args}")

ip = "127.0.0.1"
port = 9000

dispatcher = dispatcher.Dispatcher()
dispatcher.map("/*", print_handler)

server = osc_server.ThreadingOSCUDPServer((ip, port), dispatcher)
print(f"Serving on {server.server_address}")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nServer stopped")