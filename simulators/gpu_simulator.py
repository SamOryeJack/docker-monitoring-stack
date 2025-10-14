#!/usr/bin/env python3
"""
GPU Infrastructure Simulator
Simulates 8 NVIDIA A100 GPUs with realistic metrics
"""

import time
import random
import os
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import threading

# Configuration
PORT = 9400
UPDATE_INTERVAL = 10  # seconds
NUM_GPUS = 8
FAILURE_RATE = float(os.getenv('GPU_FAILURE_RATE', '0.001'))

# Metrics definitions
gpu_utilization = Gauge('gpu_utilization_percent', 'GPU utilization percentage', ['gpu_id', 'gpu_model'])
gpu_memory_used = Gauge('gpu_memory_used_bytes', 'GPU memory used in bytes', ['gpu_id', 'gpu_model'])
gpu_memory_total = Gauge('gpu_memory_total_bytes', 'GPU memory total in bytes', ['gpu_id', 'gpu_model'])
gpu_temperature = Gauge('gpu_temperature_celsius', 'GPU temperature in Celsius', ['gpu_id', 'gpu_model'])
gpu_power_draw = Gauge('gpu_power_draw_watts', 'GPU power draw in watts', ['gpu_id', 'gpu_model'])
gpu_sm_clock = Gauge('gpu_sm_clock_mhz', 'GPU SM clock speed in MHz', ['gpu_id', 'gpu_model'])
gpu_pcie_throughput_rx = Gauge('gpu_pcie_throughput_rx_bytes', 'PCIe RX throughput', ['gpu_id', 'gpu_model'])
gpu_pcie_throughput_tx = Gauge('gpu_pcie_throughput_tx_bytes', 'PCIe TX throughput', ['gpu_id', 'gpu_model'])
gpu_ecc_errors = Counter('gpu_ecc_errors_total', 'Total ECC errors', ['gpu_id', 'gpu_model', 'error_type'])

# GPU state tracking
class GPU:
    def __init__(self, gpu_id):
        self.gpu_id = f"gpu{gpu_id}"
        self.model = "NVIDIA-A100-40GB"
        self.utilization = random.randint(30, 70)
        self.base_temp = random.randint(35, 45)
        self.failed = False
        self.memory_total = 42949672960  # 40GB in bytes
        
    def update_metrics(self):
        # Simulate failure
        if random.random() < FAILURE_RATE:
            self.failed = True
        
        if self.failed and random.random() < 0.1:  # 10% chance to recover
            self.failed = False
            
        if self.failed:
            # Failed GPU metrics
            gpu_utilization.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(0)
            gpu_memory_used.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(0)
            gpu_temperature.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(0)
            gpu_power_draw.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(0)
            gpu_sm_clock.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(0)
        else:
            # Normal operation with realistic variations
            self.utilization = max(0, min(100, self.utilization + random.randint(-10, 10)))
            
            # Correlated metrics
            memory_used = self.memory_total * (self.utilization / 100) * random.uniform(0.8, 1.2)
            temperature = self.base_temp + (self.utilization * 0.5) + random.randint(-3, 3)
            power = 100 + (self.utilization * 3) + random.randint(-20, 20)
            sm_clock = 1410 - (temperature - 70) * 10 if temperature > 70 else 1410  # Thermal throttling
            
            # Set metrics
            gpu_utilization.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(self.utilization)
            gpu_memory_used.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(memory_used)
            gpu_memory_total.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(self.memory_total)
            gpu_temperature.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(temperature)
            gpu_power_draw.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(power)
            gpu_sm_clock.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(sm_clock)
            
            # PCIe throughput based on utilization
            gpu_pcie_throughput_rx.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(
                self.utilization * 1000000 * random.uniform(0.5, 1.5)
            )
            gpu_pcie_throughput_tx.labels(gpu_id=self.gpu_id, gpu_model=self.model).set(
                self.utilization * 800000 * random.uniform(0.5, 1.5)
            )
            
            # Occasional ECC errors
            if random.random() < 0.01:
                gpu_ecc_errors.labels(
                    gpu_id=self.gpu_id, 
                    gpu_model=self.model, 
                    error_type="correctable"
                ).inc()

def update_metrics_loop(gpus):
    """Update all GPU metrics in a loop"""
    while True:
        for gpu in gpus:
            gpu.update_metrics()
        time.sleep(UPDATE_INTERVAL)

if __name__ == '__main__':
    # Initialize GPUs
    gpus = [GPU(i) for i in range(NUM_GPUS)]
    
    # Start metrics server
    start_http_server(PORT)
    print(f"GPU Simulator started on port {PORT}")
    
    # Start update thread
    update_thread = threading.Thread(target=update_metrics_loop, args=(gpus,))
    update_thread.daemon = True
    update_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down GPU Simulator")
