import requests
import time
import os
import random
import threading

TARGET_URLS = os.environ.get('TARGET_URLS', 'http://nginx').split(',')
REQUEST_INTERVAL = int(os.environ.get('REQUEST_INTERVAL', '5'))

def make_requests():
    while True:
        for url in TARGET_URLS:
            try:
                response = requests.get(url, timeout=5)
                print(f"Request to {url}: {response.status_code}")
                
                # Occasionally make POST requests
                if 'inference' in url and random.random() < 0.3:
                    response = requests.post(url, json={})
                    print(f"POST to {url}: {response.status_code}")
                    
            except Exception as e:
                print(f"Error requesting {url}: {e}")
        
        time.sleep(REQUEST_INTERVAL + random.uniform(-1, 1))

if __name__ == "__main__":
    print(f"Starting load generator for URLs: {TARGET_URLS}")
    make_requests()
