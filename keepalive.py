import threading
import time
from flask import Flask
from werkzeug.serving import make_server

class KeepAliveServer:
    def __init__(self, host='0.0.0.0', port=10000):
        """
        Initialize a Flask-based keepalive server.
        
        Args:
            host (str): Host to bind the server to. Defaults to '0.0.0.0'.
            port (int): Port to run the server on. Defaults to 8080.
        """
        self.flask_app = Flask(__name__)
        self.flask_app.route('/')(self.keep_alive)
        
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.is_running = False

    def keep_alive(self):
        """
        Simple route to respond to health checks.
        
        Returns:
            tuple: A response indicating the bot is alive.
        """
        return "Bot is alive!", 200

    def start(self):
        """
        Start the Flask server in a separate thread.
        Ensures the server runs without blocking the main thread.
        """
        if not self.is_running:
            try:
                self.server = make_server(self.host, self.port, self.flask_app)
                self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.thread.start()
                self.is_running = True
                print(f"Keepalive server started on {self.host}:{self.port}")
            except Exception as e:
                print(f"Failed to start keepalive server: {e}")

    def stop(self):
        """
        Stop the Flask server and clean up resources.
        """
        if self.is_running and self.server:
            try:
                self.server.shutdown()
                self.thread.join()
                self.is_running = False
                print("Keepalive server stopped")
            except Exception as e:
                print(f"Error stopping keepalive server: {e}")