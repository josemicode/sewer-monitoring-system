import os
import time
import json
from kafka import KafkaConsumer, TopicPartition
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

# Load environment variables from the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:29092'
TOPIC_NAME = 'sensor_stream'

# InfluxDB Config
INFLUXDB_URL_PRIMARY = "http://localhost:8086"
INFLUXDB_URL_SECONDARY = "http://localhost:8087"
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

def get_consumer_lag(consumer):
    """
    Calculates the consumer lag for all assigned partitions.
    """
    lag_info = {}
    # Get the set of partitions currently assigned to this consumer
    partitions = consumer.assignment()
    
    if not partitions:
        return {}

    # Get the end offsets (Highwater mark) for these partitions
    end_offsets = consumer.end_offsets(partitions)
    
    for partition in partitions:
        current_offset = consumer.position(partition)
        end_offset = end_offsets[partition]
        lag = end_offset - current_offset
        lag_info[partition.partition] = lag
        
    return lag_info

def main():
    current_influx_url = INFLUXDB_URL_PRIMARY
    
    # Initialize InfluxDB Client
    print(f"Connecting to InfluxDB at {current_influx_url}...")
    client = InfluxDBClient(url=current_influx_url, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    # Initialize Kafka Consumer
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='earliest', # Start from beginning if no offset found
        enable_auto_commit=False,     # Manual commit for reliability
        group_id='sensor_group',      # Consumer group ID
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    print(f"Consumer started. Listening to {TOPIC_NAME}...")
    print(f"Writing to InfluxDB Bucket: {INFLUXDB_BUCKET}")
    
    message_count = 0
    
    try:
        for message in consumer:
            data = message.value
            
            # Construct InfluxDB Point
            point = Point("sensor_reading") \
                .tag("sensor_id", data["sensor_id"]) \
                .field("value", float(data["value"])) \
                .time(data["timestamp"])
            
            # Resilience: Try to write to DB, retry if failed
            while True:
                try:
                    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
                    
                    # If successful, commit the offset in Kafka
                    consumer.commit()
                    break # Exit retry loop
                except Exception as e:
                    print(f"Error writing to InfluxDB at {current_influx_url}: {e}")
                    
                    # Switch URL
                    if current_influx_url == INFLUXDB_URL_PRIMARY:
                        current_influx_url = INFLUXDB_URL_SECONDARY
                    else:
                        current_influx_url = INFLUXDB_URL_PRIMARY
                        
                    print(f"⚠️ Switching InfluxDB to {current_influx_url}...")
                    
                    # Close old client and create new one
                    try:
                        client.close()
                    except:
                        pass
                        
                    client = InfluxDBClient(url=current_influx_url, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
                    write_api = client.write_api(write_options=SYNCHRONOUS)
                    
                    print("Retrying in 2 seconds...")
                    time.sleep(2)
            
            message_count += 1
            
            # Periodically print Consumer Lag (every 10 messages)
            if message_count % 10 == 0:
                lags = get_consumer_lag(consumer)
                print(f"Processed {message_count} messages. Consumer Lag per partition: {lags}")

    except KeyboardInterrupt:
        print("\nStopping consumer...")
    finally:
        client.close()
        consumer.close()

if __name__ == "__main__":
    main()
