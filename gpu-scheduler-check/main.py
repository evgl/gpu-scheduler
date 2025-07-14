#!/usr/bin/env python3
"""
GPU Scheduler Check Service - Validates GPU assignments by logging node name and CUDA_VISIBLE_DEVICES
"""

import os
import sys
import time
import signal
import logging
import socket
from typing import Optional


class GPUSchedulerCheck:
    """Test service to validate GPU scheduler assignments"""
    
    def __init__(self, log_interval: int = 10):
        self.log_interval = log_interval
        self.running = True
        self.setup_logging()
        self.setup_signal_handlers()
        
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def get_node_name(self) -> str:
        """Get the Kubernetes node name"""
        # Try to get from environment variable (set by Kubernetes)
        node_name = os.environ.get('NODE_NAME')
        if node_name:
            return node_name
            
        # Fallback to hostname
        try:
            return socket.gethostname()
        except Exception as e:
            self.logger.warning(f"Could not get hostname: {e}")
            return "unknown-node"
            
    def get_cuda_visible_devices(self) -> str:
        """Get CUDA_VISIBLE_DEVICES environment variable"""
        cuda_devices = os.environ.get('CUDA_VISIBLE_DEVICES')
        if cuda_devices is None:
            return "not-set"
        elif cuda_devices == "":
            return "empty"
        else:
            return cuda_devices
            
    def validate_environment(self) -> bool:
        """Validate environment variables and log any issues"""
        issues = []
        
        # Check if NODE_NAME is set
        if not os.environ.get('NODE_NAME'):
            issues.append("NODE_NAME environment variable not set")
            
        # Check CUDA_VISIBLE_DEVICES
        cuda_devices = os.environ.get('CUDA_VISIBLE_DEVICES')
        if cuda_devices is None:
            issues.append("CUDA_VISIBLE_DEVICES not set by scheduler")
        elif cuda_devices == "":
            issues.append("CUDA_VISIBLE_DEVICES is empty")
            
        # Log issues
        if issues:
            for issue in issues:
                self.logger.warning(f"Environment issue: {issue}")
            return False
        else:
            self.logger.info("Environment validation passed")
            return True
            
    def log_gpu_assignment(self):
        """Log the current GPU assignment"""
        node_name = self.get_node_name()
        cuda_devices = self.get_cuda_visible_devices()
        
        # Main log message in the required format
        self.logger.info(f"Node: {node_name}, CUDA_VISIBLE_DEVICES: {cuda_devices}")
        
        # Additional debug information
        pod_name = os.environ.get('HOSTNAME', 'unknown-pod')
        namespace = os.environ.get('POD_NAMESPACE', 'unknown-namespace')
        
        self.logger.debug(f"Pod: {pod_name}, Namespace: {namespace}")
        
    def run(self):
        """Main service loop"""
        self.logger.info("GPU Scheduler Check service starting...")
        self.logger.info(f"Log interval: {self.log_interval} seconds")
        
        # Initial environment validation
        self.validate_environment()
        
        # Log initial assignment
        self.log_gpu_assignment()
        
        # Main loop
        while self.running:
            try:
                time.sleep(self.log_interval)
                if self.running:  # Check again after sleep
                    self.log_gpu_assignment()
                    
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, stopping...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(1)  # Brief pause before continuing
                
        self.logger.info("GPU Scheduler Check service stopped")


def main():
    """Main entry point"""
    # Get log interval from environment variable or use default
    log_interval = int(os.environ.get('LOG_INTERVAL', '10'))
    
    # Validate log interval
    if log_interval < 1:
        print("LOG_INTERVAL must be at least 1 second", file=sys.stderr)
        sys.exit(1)
        
    # Create and run the service
    service = GPUSchedulerCheck(log_interval=log_interval)
    
    try:
        service.run()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()