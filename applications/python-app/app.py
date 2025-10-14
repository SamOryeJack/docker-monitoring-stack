# applications/python-app/app.py
from flask import Flask, jsonify, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry
import time
import random
import psutil
import threading

app = Flask(__name__)

# Create a custom registry
registry = CollectorRegistry()

# Define custom metrics similar to what CoreWeave might monitor
request_count = Counter(
    'app_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

request_duration = Histogram(
    'app_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

active_connections = Gauge(
    'app_active_connections',
    'Number of active connections',
    registry=registry
)

gpu_memory_usage = Gauge(
    'gpu_memory_usage_bytes',
    'Simulated GPU memory usage in bytes',
    ['gpu_id'],
    registry=registry
)

gpu_utilization = Gauge(
    'gpu_utilization_percent',
    'Simulated GPU utilization percentage',
    ['gpu_id'],
    registry=registry
)

gpu_temperature = Gauge(
    'gpu_temperature_celsius',
    'GPU temperature in Celsius',
    ['gpu_id'],
    registry=registry
)

model_inference_time = Histogram(
    'model_inference_duration_seconds',
    'Time taken for model inference',
    ['model_name'],
    registry=registry
)

queue_size = Gauge(
    'job_queue_size',
    'Number of jobs in queue',
    ['queue_type'],
    registry=registry
)

def update_gpu_metrics():
    while True:
        for gpu_id in range(4):  # Simulate 4 GPUs
            # KEEP ALL YOUR EXISTING CODE - GPU utilization
            if gpu_id == 0:
                gpu_utilization.labels(gpu_id=f'gpu_{gpu_id}').set(
                    random.randint(85, 99)  # GPU 0: Heavy load
                )
            elif gpu_id == 1:
                gpu_utilization.labels(gpu_id=f'gpu_{gpu_id}').set(
                    random.randint(40, 70)  # GPU 1: Medium load
                )
            else:
                gpu_utilization.labels(gpu_id=f'gpu_{gpu_id}').set(
                    random.randint(5, 25)  # GPUs 2-3: Light load
                )
            
            # KEEP ALL YOUR EXISTING CODE - Memory usage
            if gpu_id == 0:
                gpu_memory_usage.labels(gpu_id=f'gpu_{gpu_id}').set(
                    random.randint(14000000000, 16000000000)  # 14-16GB
                )
            else:
                gpu_memory_usage.labels(gpu_id=f'gpu_{gpu_id}').set(
                    random.randint(2000000000, 8000000000)  # 2-8GB
                )
            
            # NEW CODE - Add temperature based on utilization
            if gpu_id == 0:
                base_temp = 65  # GPU 0 runs hotter (busy GPU)
                current_util = random.randint(85, 99)  # Match the utilization range
                temp = base_temp + (current_util * 0.3) + random.randint(-3, 3)
            elif gpu_id == 1:
                base_temp = 50  # GPU 1 moderate temp
                current_util = random.randint(40, 70)
                temp = base_temp + (current_util * 0.2) + random.randint(-3, 3)
            else:
                base_temp = 40  # GPUs 2-3 cooler (idle)
                current_util = random.randint(5, 25)
                temp = base_temp + (current_util * 0.15) + random.randint(-3, 3)
            
            gpu_temperature.labels(gpu_id=f'gpu_{gpu_id}').set(temp)
            
        time.sleep(10)
        
# Start GPU metrics updater in background
gpu_thread = threading.Thread(target=update_gpu_metrics, daemon=True)
gpu_thread.start()

@app.route('/')
def home():
    start_time = time.time()
    active_connections.inc()
    
    try:
        # Simulate some processing
        time.sleep(random.uniform(0.01, 0.1))
        
        request_count.labels(method='GET', endpoint='/', status='200').inc()
        response = jsonify({
            'status': 'healthy',
            'service': 'python-api',
            'version': '1.0.0'
        })
        return response
    finally:
        active_connections.dec()
        request_duration.labels(method='GET', endpoint='/').observe(
            time.time() - start_time
        )

@app.route('/api/test')
def api_test():
    """
    Test endpoint that simulates:
    - Variable response times
    - GPU failures (5% chance GPU 3 dies)
    - Application errors (20% failure rate)
    """
    start_time = time.time()
    active_connections.inc()
    
    try:
        # Simulate varying response times (KEEP THIS)
        processing_time = random.uniform(0.05, 0.5)
        time.sleep(processing_time)
        
        # ADD THIS: Simulate GPU 3 going offline sometimes (NEW)
        if random.random() < 0.05:  # 5% chance GPU fails
            gpu_utilization.labels(gpu_id='gpu_3').set(0)
            gpu_memory_usage.labels(gpu_id='gpu_3').set(0)
        
        # CHANGE THIS: Increase failure rate to 20% (MODIFIED)
        if random.random() < 0.2:  # 20% failure rate (was 0.1)
            request_count.labels(method='GET', endpoint='/api/test', status='500').inc()
            return jsonify({'error': 'GPU memory overflow!'}), 500  # Changed error message
        
        # Success case (KEEP THIS)
        request_count.labels(method='GET', endpoint='/api/test', status='200').inc()
        return jsonify({
            'result': 'success',
            'processing_time': processing_time
        })
    finally:
        active_connections.dec()
        request_duration.labels(method='GET', endpoint='/api/test').observe(
            time.time() - start_time
        )
        
@app.route('/api/inference', methods=['POST'])
def inference():
    start_time = time.time()
    active_connections.inc()
    
    try:
        # Simulate model inference
        model_name = random.choice(['gpt-3', 'stable-diffusion', 'bert'])
        inference_time = random.uniform(0.1, 2.0)
        
        with model_inference_time.labels(model_name=model_name).time():
            time.sleep(inference_time)
        
        # NEW: Simulate realistic queue patterns based on time of day
        from datetime import datetime
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        
        # Business hours (9-5): High load
        if 9 <= current_hour < 17:
            # Spike during top of hour (meetings end, jobs submitted)
            if current_minute < 10:
                inference_queue = random.randint(50, 100)
                training_queue = random.randint(20, 40)
            else:
                inference_queue = random.randint(30, 70)
                training_queue = random.randint(10, 30)
        
        # Evening (5-9): Moderate load (researchers working late)
        elif 17 <= current_hour < 21:
            inference_queue = random.randint(15, 40)
            training_queue = random.randint(5, 20)
        
        # Night (9PM-9AM): Low load (batch jobs)
        else:
            inference_queue = random.randint(0, 15)
            training_queue = random.randint(0, 5)
        
        # Set the queue metrics
        queue_size.labels(queue_type='inference').set(inference_queue)
        queue_size.labels(queue_type='training').set(training_queue)
        
        request_count.labels(method='POST', endpoint='/api/inference', status='200').inc()
        return jsonify({
            'model': model_name,
            'inference_time': inference_time,
            'result': 'completed',
            'queue_depth': inference_queue  # NEW: Return queue info
        })
    finally:
        active_connections.dec()
        request_duration.labels(method='POST', endpoint='/api/inference').observe(
            time.time() - start_time
        )
        
@app.route('/metrics')
def metrics():
    # Return Prometheus metrics
    return Response(generate_latest(registry), mimetype='text/plain')

@app.route('/health')
def health():
    # Health check endpoint
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    
    # NEW: Check multiple alert conditions
    alerts = []
    
    # Check GPU 0 overheating
    gpu_0_temp = gpu_temperature.labels(gpu_id='gpu_0')._value.get()
    if gpu_0_temp > 85:
        alerts.append(f"GPU_0 CRITICAL TEMP: {gpu_0_temp}°C")
    
    # Check if any GPU is offline
    for i in range(4):
        util = gpu_utilization.labels(gpu_id=f'gpu_{i}')._value.get()
        if util == 0:
            alerts.append(f"GPU_{i} OFFLINE")
    
    # Check queue backup
    inference_queue = queue_size.labels(queue_type='inference')._value.get()
    if inference_queue > 75:
        alerts.append(f"QUEUE OVERLOAD: {inference_queue} jobs waiting")
    
    # Determine overall health
    if alerts:
        health_status = 'critical'
    elif cpu_percent > 80 or memory.percent > 80:
        health_status = 'degraded'
    else:
        health_status = 'healthy'
    
    return jsonify({
        'status': health_status,
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'active_connections': active_connections._value.get(),
        'alerts': alerts  # NEW: List of problems
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

