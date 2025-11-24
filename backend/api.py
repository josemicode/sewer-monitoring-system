import json
import os
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from aiokafka import AIOKafkaConsumer
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:29092'
TOPIC_NAME = 'sensor_stream'
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
ALERT_THRESHOLD = 28.0  # Trigger alert if value > 28.0 (Sine wave max is 30)

# Database Setup (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./alerts.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

class AlarmLog(Base):
    __tablename__ = "alarm_logs"
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True)
    value = Column(Float)
    threshold = Column(Float)
    acknowledged = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- FastAPI App ---
app = FastAPI(title="Sewer Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_influx_query_api():
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    return client.query_api()

# --- Helpers ---
async def log_alarm(db: Session, sensor_id: str, value: float):
    """Log an alarm to SQLite if it's a new high value."""
    # Simple logic: Log every violation. In production, you might debounce this.
    alarm = AlarmLog(
        sensor_id=sensor_id,
        value=value,
        threshold=ALERT_THRESHOLD,
        acknowledged=False,
        timestamp=datetime.utcnow()
    )
    db.add(alarm)
    db.commit()
    db.refresh(alarm)
    return alarm

# --- Endpoints ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    
    # Create a unique consumer group for this websocket so it gets all messages
    # or use no group_id to act as a standalone consumer
    consumer = AIOKafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"ws-client-{random.randint(1, 10000)}",
        auto_offset_reset='latest'
    )
    
    await consumer.start()
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            value = float(data.get("value", 0))
            sensor_id = data.get("sensor_id")
            
            # Check Threshold
            alert_triggered = False
            if value > ALERT_THRESHOLD:
                alert_triggered = True
                # Log to DB (Synchronous DB call in async loop - ideally run in executor, but SQLite is fast enough for demo)
                # We need a new DB session or handle concurrency carefully. 
                # For simplicity here, we just mark the flag. 
                # To strictly follow requirements "log it to SQLite", we do it here.
                # Note: 'db' dependency in WebSocket is tricky because of session lifecycle.
                # We'll create a fresh session for the log to be safe.
                with SessionLocal() as log_session:
                    await asyncio.to_thread(log_alarm, log_session, sensor_id, value)
            
            # Append Alert Flag
            response_data = {
                **data,
                "is_alert": alert_triggered,
                "threshold": ALERT_THRESHOLD
            }
            
            await websocket.send_json(response_data)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        await consumer.stop()

@app.get("/history")
def get_history(
    start_date: str, # ISO Format expected
    aggregation: str = "hour", # minute, hour, day
    query_api = Depends(get_influx_query_api)
):
    """
    Query InfluxDB for aggregated statistics.
    start_date example: '-1d', '-1h' or ISO string.
    For simplicity in Flux, we'll accept relative time strings like '-24h', '-1h' or use start_date directly if it parses.
    """
    
    # Map aggregation to Flux window period
    window_map = {
        "minute": "1m",
        "hour": "1h",
        "day": "1d"
    }
    window_period = window_map.get(aggregation, "1h")
    
    # Construct Flux Query
    # We'll assume start_date is a relative duration string for simplicity (e.g., "-24h")
    # If the user passes a specific date, we'd need to format it.
    # Let's support simple relative ranges for now as it's robust.
    
    # If start_date doesn't start with '-', assume it's absolute time? 
    # Let's just treat it as the 'start' parameter in range().
    
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {start_date})
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
      |> window(every: {window_period})
      |> reduce(fn: (r, accumulator) => ({{
          count: r._value + accumulator.count,
          total: r._value + accumulator.total,
          min: if r._value < accumulator.min then r._value else accumulator.min,
          max: if r._value > accumulator.max then r._value else accumulator.max
        }}),
        identity: {{count: 0.0, total: 0.0, min: 1000000.0, max: -1000000.0}}
      )
      |> map(fn: (r) => ({{
          r with
          avg: r.total / r.count
        }}))
    '''
    
    # Note: The above reduce is complex. A simpler way is using standard aggregate functions.
    # Let's use standard mean, min, max for simplicity.
    
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {start_date})
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
      |> aggregateWindow(every: {window_period}, fn: mean, createEmpty: false)
      |> yield(name: "mean")
    '''
    
    # To get min, max, and avg together, we need to pivot or run multiple queries.
    # For this assignment, let's just return the MEAN (avg) to keep it working reliably.
    # Or we can do a fieldsAsCols approach if we had multiple fields.
    
    # Better approach for "min, max, avg":
    query = f'''
    data = from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {start_date})
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
    
    min = data |> aggregateWindow(every: {window_period}, fn: min, createEmpty: false)
    max = data |> aggregateWindow(every: {window_period}, fn: max, createEmpty: false)
    mean = data |> aggregateWindow(every: {window_period}, fn: mean, createEmpty: false)
    
    join(tables: {{min: min, max: max, mean: mean}}, on: ["_time", "sensor_id"])
    '''
    
    #result = query_api.query(query=query, org=INFLUXDB_ORG)

    base = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {start_date})
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
      |> group(columns: ["sensor_id"])
      |> aggregateWindow(every: {window_period}, fn: {{fn}}, createEmpty: false)
    '''

    min_result = query_api.query(query=base.format(fn="min"), org=INFLUXDB_ORG)
    max_result = query_api.query(query=base.format(fn="max"), org=INFLUXDB_ORG)
    mean_result = query_api.query(query=base.format(fn="mean"), org=INFLUXDB_ORG)

    ''' 
    output = []
    for table in result:
        for record in table.records:
            output.append({
                "time": record.get_time(),
                "sensor_id": record.values.get("sensor_id"),
                "min": record.values.get("_value_min"),
                "max": record.values.get("_value_max"),
                "avg": record.values.get("_value_mean")
            })
    '''

    # Merge results by timestamp
    output = []
    for m, x, a in zip(min_result[0].records, max_result[0].records, mean_result[0].records):
        output.append({
            "time": m.get_time(),
            "sensor_id": m.values.get("sensor_id"),
            "min": m.get_value(),
            "max": x.get_value(),
            "avg": a.get_value()
        })
            
    return output

@app.post("/acknowledge/{alarm_id}")
def acknowledge_alarm(alarm_id: int, db: Session = Depends(get_db)):
    alarm = db.query(AlarmLog).filter(AlarmLog.id == alarm_id).first()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    alarm.acknowledged = True
    db.commit()
    return {"status": "success", "message": f"Alarm {alarm_id} acknowledged"}

@app.post("/users/")
def create_user(username: str, password_hash: str, db: Session = Depends(get_db)):
    # Very basic user creation
    user = User(username=username, password_hash=password_hash)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="User already exists")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
