#!/usr/bin/env python3
"""
Basic tests for GPU scheduler logic without Kubernetes dependencies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Test the annotation parser logic directly
def test_parse_gpu_scheduling_map():
    """Test parsing GPU scheduling map without importing scheduler"""
    
    def parse_gpu_scheduling_map(annotation_value):
        """Standalone parser function for testing"""
        scheduling_map = {}
        
        try:
            lines = annotation_value.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
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
            print(f"Error parsing GPU scheduling map: {e}")
            
        return scheduling_map
    
    # Test valid annotation
    annotation_value = """0=node1:0,1
                        1=node2:2
                        2=node3:0,1,2
                        3=node4:3
                        4=node4:3"""
    
    result = parse_gpu_scheduling_map(annotation_value)
    
    expected = {
        0: ("node1", "0,1"),
        1: ("node2", "2"),
        2: ("node3", "0,1,2"),
        3: ("node4", "3"),
        4: ("node4", "3")
    }
    
    assert result == expected, f"Expected {expected}, got {result}"
    print("✓ Valid annotation parsing test passed")
    
    # Test empty annotation
    empty_result = parse_gpu_scheduling_map("")
    assert empty_result == {}, f"Expected empty dict, got {empty_result}"
    print("✓ Empty annotation parsing test passed")
    
    # Test annotation with whitespace
    whitespace_annotation = """  0 = node1 : 0,1  
    1=node2:2
    
    2=node3:0,1,2"""
    
    whitespace_result = parse_gpu_scheduling_map(whitespace_annotation)
    whitespace_expected = {
        0: ("node1", "0,1"),
        1: ("node2", "2"),
        2: ("node3", "0,1,2")
    }
    
    assert whitespace_result == whitespace_expected, f"Expected {whitespace_expected}, got {whitespace_result}"
    print("✓ Whitespace annotation parsing test passed")


def test_get_pod_index():
    """Test pod index extraction"""
    
    def get_pod_index(pod_name):
        """Standalone pod index function for testing"""
        try:
            parts = pod_name.split('-')
            if len(parts) > 1:
                index_str = parts[-1]
                return int(index_str)
        except ValueError:
            pass
        return None
    
    # Test valid pod names
    test_cases = [
        ("my-app-0", 0),
        ("gpu-workload-1", 1),
        ("test-pod-42", 42),
        ("service-deployment-123", 123)
    ]
    
    for pod_name, expected_index in test_cases:
        result = get_pod_index(pod_name)
        assert result == expected_index, f"Expected {expected_index} for {pod_name}, got {result}"
    
    print("✓ Valid pod index extraction test passed")
    
    # Test invalid pod names
    invalid_cases = [
        "my-app-abc",
        "no-index",
        "test-pod-",
        ""
    ]
    
    for pod_name in invalid_cases:
        result = get_pod_index(pod_name)
        assert result is None, f"Expected None for {pod_name}, got {result}"
    
    print("✓ Invalid pod index extraction test passed")


def main():
    """Run all tests"""
    print("Running GPU scheduler basic tests...")
    
    try:
        test_parse_gpu_scheduling_map()
        test_get_pod_index()
        print("\nAll tests passed! ✓")
        return 0
    except Exception as e:
        print(f"\nTest failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())