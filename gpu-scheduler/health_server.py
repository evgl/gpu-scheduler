#!/usr/bin/env python3
"""
Health check server for GPU scheduler
"""

import logging
import threading
from flask import Flask, jsonify


class HealthServer:
    """Simple health check server"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = Flask(__name__)
        self.setup_routes()
        self.logger = logging.getLogger(__name__)
        
    def setup_routes(self):
        """Setup health check routes"""
        
        @self.app.route('/health')
        def health():
            return jsonify({"status": "healthy", "service": "gpu-scheduler"})
            
        @self.app.route('/ready')
        def ready():
            return jsonify({"status": "ready", "service": "gpu-scheduler"})
            
    def run(self):
        """Run the health server"""
        self.logger.info(f"Starting health server on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False)
        
    def start_background(self):
        """Start health server in background thread"""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        self.logger.info("Health server started in background")