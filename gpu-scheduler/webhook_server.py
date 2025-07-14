#!/usr/bin/env python3
"""
Mutating Admission Webhook for GPU Environment Variable Injection
"""

import base64
import json
import logging
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional, Tuple


class WebhookHandler(BaseHTTPRequestHandler):
    """Handler for admission webhook requests"""
    
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        """Handle admission review requests"""
        # Parse URL to extract path without query parameters
        from urllib.parse import urlparse
        parsed_path = urlparse(self.path).path
        
        if parsed_path != '/mutate':
            self.send_error(404)
            return
            
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            admission_review = json.loads(body)
            
            # Process the admission request
            response = self.mutate_pod(admission_review)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logging.error(f"Error processing webhook request: {e}")
            self.send_error(500, str(e))
    
    def parse_gpu_scheduling_map(self, annotation_value: str) -> Dict[int, Tuple[str, str]]:
        """Parse the gpu-scheduling-map annotation"""
        scheduling_map = {}
        
        try:
            lines = annotation_value.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Parse format: "0=node1:0,1"
                if '=' not in line:
                    continue
                    
                pod_index_str, node_gpu_str = line.split('=', 1)
                pod_index = int(pod_index_str.strip())
                
                if ':' not in node_gpu_str:
                    continue
                    
                node_name, gpu_devices = node_gpu_str.split(':', 1)
                node_name = node_name.strip()
                gpu_devices = gpu_devices.strip()
                
                scheduling_map[pod_index] = (node_name, gpu_devices)
                
        except Exception as e:
            logging.error(f"Error parsing GPU scheduling map: {e}")
            
        return scheduling_map
    
    def get_pod_index_from_generate_name(self, pod_name: str, generate_name: str) -> Optional[int]:
        """Extract pod index from pod name based on generateName pattern"""
        # For StatefulSets, the pattern is usually: <statefulset-name>-<index>
        # The generateName usually ends with a dash
        if generate_name and generate_name.endswith('-'):
            prefix = generate_name[:-1]  # Remove trailing dash
            if pod_name.startswith(prefix + '-'):
                suffix = pod_name[len(prefix) + 1:]
                try:
                    return int(suffix)
                except ValueError:
                    pass
        
        # Fallback: try to extract index from end of pod name
        try:
            parts = pod_name.split('-')
            if len(parts) > 1:
                return int(parts[-1])
        except ValueError:
            pass
            
        return None
    
    def create_patch(self, pod: dict, cuda_devices: str) -> List[dict]:
        """Create JSON patch to add CUDA_VISIBLE_DEVICES environment variable"""
        patches = []
        
        containers = pod.get('spec', {}).get('containers', [])
        for i, container in enumerate(containers):
            env = container.get('env', [])
            
            # Check if CUDA_VISIBLE_DEVICES already exists
            cuda_exists = any(e.get('name') == 'CUDA_VISIBLE_DEVICES' for e in env)
            
            if cuda_exists:
                # Update existing environment variable
                for j, env_var in enumerate(env):
                    if env_var.get('name') == 'CUDA_VISIBLE_DEVICES':
                        patches.append({
                            'op': 'replace',
                            'path': f'/spec/containers/{i}/env/{j}/value',
                            'value': cuda_devices
                        })
                        break
            else:
                # Add new environment variable
                if not env:
                    # Initialize env array if it doesn't exist
                    patches.append({
                        'op': 'add',
                        'path': f'/spec/containers/{i}/env',
                        'value': [{'name': 'CUDA_VISIBLE_DEVICES', 'value': cuda_devices}]
                    })
                else:
                    # Append to existing env array
                    patches.append({
                        'op': 'add',
                        'path': f'/spec/containers/{i}/env/-',
                        'value': {'name': 'CUDA_VISIBLE_DEVICES', 'value': cuda_devices}
                    })
        
        return patches
    
    def mutate_pod(self, admission_review: dict) -> dict:
        """Process admission review and return mutation response"""
        # Extract request
        request = admission_review.get('request', {})
        uid = request.get('uid')
        pod = request.get('object', {})
        
        # Default response (no mutation)
        response = {
            'apiVersion': 'admission.k8s.io/v1',
            'kind': 'AdmissionReview',
            'response': {
                'uid': uid,
                'allowed': True
            }
        }
        
        # Check if this pod uses our scheduler
        scheduler_name = pod.get('spec', {}).get('schedulerName')
        if scheduler_name != 'gpu-scheduler':
            logging.debug(f"Pod uses different scheduler: {scheduler_name}")
            return response
        
        # Check for GPU scheduling annotation
        annotations = pod.get('metadata', {}).get('annotations', {})
        gpu_map = annotations.get('gpu-scheduling-map')
        if not gpu_map:
            logging.debug("No gpu-scheduling-map annotation found")
            return response
        
        # Get pod name (might be generated)
        pod_name = pod.get('metadata', {}).get('name', '')
        generate_name = pod.get('metadata', {}).get('generateName', '')
        
        # If pod name is not set (common for controllers), we need to predict it
        if not pod_name and generate_name:
            # For StatefulSets, we can predict the name based on the ordinal
            # This is a limitation - we might need additional context
            logging.warning(f"Pod name not set, using generateName: {generate_name}")
            # We'll handle this in the scheduler instead
            return response
        
        # Parse scheduling map
        scheduling_map = self.parse_gpu_scheduling_map(gpu_map)
        if not scheduling_map:
            logging.warning("Failed to parse gpu-scheduling-map")
            return response
        
        # Get pod index
        pod_index = self.get_pod_index_from_generate_name(pod_name, generate_name)
        if pod_index is None:
            logging.warning(f"Could not determine pod index for {pod_name}")
            # For now, we'll try to handle this in the scheduler
            return response
        
        # Find GPU assignment
        if pod_index not in scheduling_map:
            logging.warning(f"No GPU assignment for pod index {pod_index}")
            return response
        
        _, cuda_devices = scheduling_map[pod_index]
        logging.info(f"Injecting CUDA_VISIBLE_DEVICES={cuda_devices} for pod {pod_name} (index {pod_index})")
        
        # Create patch
        patches = self.create_patch(pod, cuda_devices)
        if patches:
            # Encode patch as base64
            patch_bytes = json.dumps(patches).encode()
            patch_base64 = base64.b64encode(patch_bytes).decode()
            
            response['response']['patchType'] = 'JSONPatch'
            response['response']['patch'] = patch_base64
            logging.info(f"Created patch for pod {pod_name}: {patches}")
        
        return response


class WebhookServer:
    """HTTPS server for admission webhook"""
    
    def __init__(self, port: int = 8443, cert_file: str = '/certs/tls.crt', key_file: str = '/certs/tls.key'):
        self.port = port
        self.cert_file = cert_file
        self.key_file = key_file
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Start the webhook server"""
        self.logger.info(f"Starting webhook server on port {self.port}")
        
        # Create HTTPS server
        server = HTTPServer(('0.0.0.0', self.port), WebhookHandler)
        
        # Configure SSL
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.cert_file, self.key_file)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        
        self.logger.info("Webhook server ready")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Webhook server stopping...")
        finally:
            server.shutdown()


def main():
    """Main entry point"""
    server = WebhookServer()
    server.run()


if __name__ == "__main__":
    main() 