#!/usr/bin/env python3
"""
GPU Scheduler - Custom Kubernetes scheduler for GPU device assignment
"""

import os
import sys
import time
import logging
import json
import random
from typing import Dict, List, Optional, Tuple
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from health_server import HealthServer


class GPUScheduler:
    """Custom Kubernetes scheduler for GPU device assignment"""
    
    def __init__(self, scheduler_name: str = "gpu-scheduler"):
        self.scheduler_name = scheduler_name
        self.setup_logging()
        self.setup_kubernetes_client()
        self.health_server = HealthServer()
        
    def setup_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_kubernetes_client(self):
        """Setup Kubernetes API client"""
        try:
            # Try to load in-cluster config first
            config.load_incluster_config()
            self.logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            # Fall back to kubeconfig
            try:
                config.load_kube_config()
                self.logger.info("Loaded kubeconfig")
            except config.ConfigException as e:
                self.logger.error(f"Could not load Kubernetes config: {e}")
                sys.exit(1)
                
        self.v1 = client.CoreV1Api()
        self.logger.info("Kubernetes client initialized")
        
    def parse_gpu_scheduling_map(self, annotation_value: str) -> Dict[int, Tuple[str, str]]:
        """
        Parse the gpu-scheduling-map annotation
        
        Format: "0=node1:0,1\n1=node2:2\n2=node3:0,1,2"
        Returns: {0: ("node1", "0,1"), 1: ("node2", "2"), 2: ("node3", "0,1,2")}
        """
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
            self.logger.error(f"Error parsing GPU scheduling map: {e}")
            
        return scheduling_map
        
    def get_pod_index(self, pod_name: str) -> Optional[int]:
        """
        Extract pod index from pod name
        Assumes format like: my-app-0, my-app-1, etc.
        """
        try:
            # Try to extract index from end of pod name
            parts = pod_name.split('-')
            if len(parts) > 1:
                index_str = parts[-1]
                return int(index_str)
        except ValueError:
            pass
            
        return None

    def get_actual_node_name(self, logical_node_name: str) -> Optional[str]:
        """
        Map logical node name (e.g., 'node1') to actual Kubernetes node name.
        Uses node labels to find the mapping.
        """
        try:
            self.logger.info(f"Looking up actual node name for logical node: {logical_node_name}")
            
            # Get all nodes
            nodes = self.v1.list_node()
            self.logger.info(f"Found {len(nodes.items)} nodes in cluster")
            
            # Look for node with matching gpu-node-name label
            for node in nodes.items:
                node_labels = node.metadata.labels or {}
                gpu_node_name = node_labels.get('gpu-node-name')
                self.logger.info(f"Node {node.metadata.name} has gpu-node-name label: {gpu_node_name}")
                
                if gpu_node_name == logical_node_name:
                    self.logger.info(f"Found matching node: {node.metadata.name} for logical name {logical_node_name}")
                    return node.metadata.name
                    
            self.logger.warning(f"No node found with gpu-node-name label: {logical_node_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting actual node name: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        
    def schedule_pod(self, pod_name: str, namespace: str, node_name: str, cuda_devices: str) -> bool:
        """Schedule a pod to a specific node"""
        try:
            # Create binding to bind the pod to the node
            binding = client.V1Binding(
                api_version="v1",
                kind="Binding",
                metadata=client.V1ObjectMeta(
                    name=pod_name,
                    namespace=namespace
                ),
                target=client.V1ObjectReference(
                    api_version="v1",
                    kind="Node",
                    name=node_name
                )
            )
            
            # Bind the pod to the node
            self.v1.create_namespaced_binding(
                namespace=namespace,
                body=binding
            )
            
            self.logger.info(f"Successfully scheduled pod {pod_name} to node {node_name} (GPU devices: {cuda_devices})")
            return True
            
        except ApiException as e:
            self.logger.error(f"Error scheduling pod {pod_name}: {e}")
            return False
            
    def process_pod(self, pod: client.V1Pod):
        """Process a pod for GPU scheduling"""
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace
        
        # Check if pod has GPU scheduling annotation
        if not pod.metadata.annotations:
            return
            
        gpu_map_annotation = pod.metadata.annotations.get("gpu-scheduling-map")
        if not gpu_map_annotation:
            return
            
        self.logger.info(f"Processing pod {pod_name} with GPU scheduling annotation")
        
        # Parse the scheduling map
        scheduling_map = self.parse_gpu_scheduling_map(gpu_map_annotation)
        if not scheduling_map:
            self.logger.warning(f"No valid scheduling map found for pod {pod_name}")
            return
            
        # Get pod index
        pod_index = self.get_pod_index(pod_name)
        if pod_index is None:
            self.logger.warning(f"Could not determine pod index for {pod_name}")
            return
            
        # Find scheduling assignment
        if pod_index not in scheduling_map:
            self.logger.warning(f"No scheduling assignment found for pod index {pod_index}")
            return
            
        logical_node_name, cuda_devices = scheduling_map[pod_index]
        
        # Map logical node name to actual Kubernetes node name
        actual_node_name = self.get_actual_node_name(logical_node_name)
        if not actual_node_name:
            self.logger.error(f"Could not map logical node name '{logical_node_name}' to actual node")
            return
            
        # Schedule the pod (environment variables are handled by webhook)
        self.schedule_pod(pod_name, namespace, actual_node_name, cuda_devices)
        
    def run(self):
        """Main scheduler loop"""
        self.logger.info(f"Starting GPU scheduler: {self.scheduler_name}")
        self.logger.info("Note: CUDA_VISIBLE_DEVICES environment injection is handled by the admission webhook")
        
        # Start health server in background
        self.health_server.start_background()
        
        retry_count = 0
        max_retries = 5
        base_delay = 1.0
        
        while True:
            w = watch.Watch()
            
            try:
                self.logger.info(f"Starting watch stream (attempt {retry_count + 1})")
                
                # Watch for pods that need to be scheduled
                for event in w.stream(
                    self.v1.list_pod_for_all_namespaces,
                    field_selector=f"spec.schedulerName={self.scheduler_name},spec.nodeName=",
                    timeout_seconds=3600  # Restart watch every hour as additional safety
                ):
                    event_type = event['type']
                    pod = event['object']
                    
                    if event_type == 'ADDED':
                        self.logger.info(f"New pod to schedule: {pod.metadata.name}")
                        self.process_pod(pod)
                    
                    # Reset retry count on successful event processing
                    retry_count = 0
                        
            except KeyboardInterrupt:
                self.logger.info("Scheduler stopping...")
                break
                
            except ApiException as e:
                if e.status == 410:  # Resource version expired
                    self.logger.warning(f"Watch stream expired (resource version too old): {e}")
                    self.logger.info("Restarting watch stream with fresh resource version...")
                    retry_count = 0  # Don't count 410 errors as retries
                    
                else:
                    self.logger.error(f"Kubernetes API error: {e}")
                    retry_count += 1
                    
                    if retry_count >= max_retries:
                        self.logger.error(f"Max retries ({max_retries}) reached. Scheduler stopping.")
                        raise
                        
                    # Exponential backoff with jitter
                    delay = min(base_delay * (2 ** retry_count), 60) + random.uniform(0, 1)
                    self.logger.info(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"Unexpected scheduler error: {e}")
                retry_count += 1
                
                if retry_count >= max_retries:
                    self.logger.error(f"Max retries ({max_retries}) reached. Scheduler stopping.")
                    raise
                    
                # Exponential backoff with jitter
                delay = min(base_delay * (2 ** retry_count), 60) + random.uniform(0, 1)
                self.logger.info(f"Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
                
            finally:
                w.stop()
                
            # Brief pause before restarting watch (for 410 errors)
            time.sleep(0.1)


def main():
    """Main entry point"""
    scheduler = GPUScheduler()
    scheduler.run()


if __name__ == "__main__":
    main()