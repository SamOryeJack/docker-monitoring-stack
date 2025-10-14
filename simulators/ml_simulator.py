#!/usr/bin/env python3
"""
ML Workload Simulator
Simulates machine learning training and inference workloads
"""

import time
import random
import math
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import threading

# Configuration
PORT = 9500
UPDATE_INTERVAL = 10

# Metrics definitions
training_loss = Gauge('training_loss', 'Current training loss', ['model_name', 'job_id'])
training_accuracy = Gauge('training_accuracy', 'Current training accuracy', ['model_name', 'job_id'])
training_epoch = Gauge('training_epoch', 'Current epoch number', ['model_name', 'job_id'])
training_throughput = Gauge('training_throughput_samples_per_second', 'Training throughput', ['model_name'])
batch_processing_time = Histogram('batch_processing_time_seconds', 'Time to process a batch', ['model_name'])
inference_requests = Counter('inference_requests_total', 'Total inference requests', ['model_name', 'status'])
inference_latency = Histogram('inference_latency_seconds', 'Inference latency', ['model_name'])
job_queue_depth = Gauge('ml_job_queue_depth', 'Number of jobs in queue', ['queue_type'])
checkpoint_saves = Counter('checkpoint_saves_total', 'Total checkpoint saves', ['model_name'])
gpu_memory_allocated = Gauge('ml_gpu_memory_allocated_gb', 'GPU memory allocated for ML', ['job_id'])

class TrainingJob:
    def __init__(self, job_id, model_name):
        self.job_id = job_id
        self.model_name = model_name
        self.epoch = 0
        self.initial_loss = random.uniform(2.0, 4.0)
        self.convergence_rate = random.uniform(0.01, 0.05)
        self.max_epochs = random.randint(50, 200)
        
    def update_metrics(self):
        self.epoch += 1
        
        # Simulate loss decay (exponential decay with noise)
        current_loss = self.initial_loss * math.exp(-self.convergence_rate * self.epoch)
        current_loss += random.uniform(-0.1, 0.1)  # Add noise
        current_loss = max(0.01, current_loss)  # Floor at 0.01
        
        # Accuracy increases as loss decreases
        accuracy = min(0.99, 1 - current_loss/self.initial_loss) * 100
        
        # Throughput varies with batch processing
        throughput = random.uniform(1000, 5000)
        
        # Set metrics
        training_loss.labels(model_name=self.model_name, job_id=self.job_id).set(current_loss)
        training_accuracy.labels(model_name=self.model_name, job_id=self.job_id).set(accuracy)
        training_epoch.labels(model_name=self.model_name, job_id=self.job_id).set(self.epoch)
        training_throughput.labels(model_name=self.model_name).set(throughput)
        
        # Batch processing time
        batch_time = random.uniform(0.5, 2.0)
        batch_processing_time.labels(model_name=self.model_name).observe(batch_time)
        
        # GPU memory allocation
        gpu_memory_allocated.labels(job_id=self.job_id).set(random.uniform(10, 35))
        
        # Checkpoint saves every 10 epochs
        if self.epoch % 10 == 0:
            checkpoint_saves.labels(model_name=self.model_name).inc()
        
        # Complete job after max epochs
        if self.epoch >= self.max_epochs:
            return True
        return False

def simulate_inference():
    """Simulate inference requests"""
    models = ['bert-base', 'gpt-3', 'resnet50', 'yolov5']
    
    for model in models:
        # Generate some inference requests
        if random.random() < 0.7:  # 70% chance of requests
            num_requests = random.randint(10, 100)
            for _ in range(num_requests):
                # Simulate success/failure
                if random.random() < 0.95:  # 95% success rate
                    inference_requests.labels(model_name=model, status='success').inc()
                    latency = random.uniform(0.01, 0.5)
                    inference_latency.labels(model_name=model).observe(latency)
                else:
                    inference_requests.labels(model_name=model, status='error').inc()

def update_metrics_loop():
    """Main metrics update loop"""
    training_jobs = []
    job_counter = 0
    
    while True:
        # Start new training jobs randomly
        if random.random() < 0.1 and len(training_jobs) < 4:
            models = ['transformer', 'cnn', 'rnn', 'gan']
            job = TrainingJob(f"job_{job_counter}", random.choice(models))
            training_jobs.append(job)
            job_counter += 1
        
        # Update training jobs
        completed_jobs = []
        for job in training_jobs:
            if job.update_metrics():
                completed_jobs.append(job)
        
        # Remove completed jobs
        for job in completed_jobs:
            training_jobs.remove(job)
        
        # Update queue depth
        job_queue_depth.labels(queue_type='training').set(len(training_jobs))
        job_queue_depth.labels(queue_type='inference').set(random.randint(0, 50))
        
        # Simulate inference
        simulate_inference()
        
        time.sleep(UPDATE_INTERVAL)

if __name__ == '__main__':
    # Start metrics server
    start_http_server(PORT)
    print(f"ML Workload Simulator started on port {PORT}")
    
    # Start update thread
    update_thread = threading.Thread(target=update_metrics_loop)
    update_thread.daemon = True
    update_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Shutting down ML Simulator")
