import http.server
import socketserver
import threading
import time
from pyngrok import ngrok
from src.config import NGROK_TOKEN

def start_server_and_tunnel(directory, port=8002):
    """Starts a local HTTP server and an Ngrok tunnel to serve the theme ZIP."""
    
    # Configure Ngrok
    ngrok.set_auth_token(NGROK_TOKEN)
    
    # Define Handler to serve the specific directory
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

    # Start HTTP Server in a thread
    httpd = socketserver.TCPServer(("", port), Handler)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print(f"🚀 Local server started on port {port}")

    # Open Ngrok Tunnel
    public_url = ngrok.connect(port).public_url
    print(f"🔗 Ngrok Tunnel: {public_url}")
    
    return httpd, public_url