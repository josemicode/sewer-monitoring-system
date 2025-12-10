import multiprocessing
import time
import json
import math
import os
from kafka import KafkaProducer
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:29092'
TOPIC_NAME = 'sensor_stream'

def sensor_simulation(sensor_id, lock):
    """
    Simulates a sensor generating sine wave data.
    Runs in a separate process.
    """
    # Initialize Kafka Producer per process (best practice for multiprocessing)
    # KafkaProducer is not fork-safe, so we create it inside the process
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    log_file = "logs/sine_data.log"
    
    print(f"Sensor {sensor_id} started.")
    
    try:
        while True:
            # Align timestamp to the nearest second for graph alignment
            now = datetime.now(timezone.utc)
            timestamp = now.replace(microsecond=0).isoformat()
            # Generate Sine wave value based on time
            # Using time.time() ensures the wave progresses
            # Restore phase shift as per user request, but keep amplitude variation
            value = math.sin(time.time() + sensor_id) * (10 + sensor_id * 2) + 20 # Base 20, amplitude 10
            
            data = {
                "sensor_id": f"sensor_{sensor_id}",
                "timestamp": timestamp,
                "value": value
            }
            
            # Send to Kafka
            producer.send(TOPIC_NAME, data)
            producer.flush() # Ensure it's sent immediately for this simulation
            
            # Log to file with Lock to prevent race conditions
            with lock:
                with open(log_file, "a") as f:
                    f.write(f"[{timestamp}] Process-{sensor_id}: Sent value {value:.2f}\n")
            
            # Simulate sampling rate (1 Hz)
            time.sleep(1)
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        with lock:
            with open(log_file, "a") as f:
                f.write(f"Process-{sensor_id} Error: {str(e)}\n")
    finally:
        producer.close()

if __name__ == "__main__":
    # Create a shared lock for file writing
    file_lock = multiprocessing.Lock()
    
    processes = []
    num_sensors = 4
    
    print(f"Starting {num_sensors} sensor processes...")
    print("Press Ctrl+C to stop.")
    
    # Spawn processes
    for i in range(num_sensors):
        p = multiprocessing.Process(target=sensor_simulation, args=(i, file_lock))
        p.start()
        processes.append(p)
        
    try:
        # Keep main process alive to monitor children
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\nStopping processes...")
        for p in processes:
            p.terminate()
            p.join()
        print("All processes stopped.")
