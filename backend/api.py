import json
import os
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
#from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from aiokafka import AIOKafkaConsumer
from influxdb_client import InfluxDBClient
from dotenv import load_dotenv

import uvicorn

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
LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
#? Why does it use yield?
# In this case, it's used to create a generator that can be used to iterate over a sequence of database sessions.
# The generator is then used to yield the database session to the endpoint. This pattern is called "dependency injection".
# If we didn't use yield, we would need to create a new session for each request, which would be less efficient.
def get_db() -> Session:
    db = LocalSession()
    try:
        yield db
    finally:
        db.close()

def get_influx_query_api():
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    return client.query_api()

#* --- Helpers ---
#? Why is it async?
# Because it's a database operation, which is an I/O operation and can block the event loop.
async def log_alarm(db: Session, sensor_id: str, value: float) -> AlarmLog:
    #* Log an alarm to SQLite if it's a new high value.
    # Simple logic: Log every violation. If it was in production, I might debounce this.
    alarm = AlarmLog(sensor_id=sensor_id, value=value, threshold=ALERT_THRESHOLD, acknowledged=False, timestamp=datetime.utcnow())
    db.add(alarm)
    db.commit()
    db.refresh(alarm)
    return alarm

#* --- Endpoints ---
#? When is this code run?
# When a client connects to the WebSocket endpoint, every time a new message is received, and when the client disconnects.
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    
    '''
    Create a unique consumer group for this websocket so it gets all messages
    or use no group_id to act as a standalone consumer
    '''
    consumer = AIOKafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=f"ws-client-{random.randint(1, 10000)}",
        auto_offset_reset='latest'
    )
    
    try:
        await consumer.start()
    except Exception as e:
        print(f"Error starting Kafka consumer: {e}")
        await websocket.close(code=1011)
        return

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
                with LocalSession() as log_session:
                    await asyncio.to_thread(log_alarm, log_session, sensor_id, value)
            
            # Append Alert Flag
            response_data = {
                **data,
                "is_alert": alert_triggered,
                "threshold": ALERT_THRESHOLD
            }
            #? Why does data have **?
            # because data is a dictionary and **data unpacks it into a new dictionary
            # so we can add new key-value pairs to it
            # otherwise we would have to do something like this:
            # response_data = data.copy()
            # response_data["is_alert"] = alert_triggered
            # response_data["threshold"] = ALERT_THRESHOLD
            
            await websocket.send_json(response_data)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        print("Stopping WebSocket consumer...")
        await consumer.stop()


'''
Params:
    start_date: str, # ISO Format expected
    aggregation: str = "hour", # minute, hour, day
    query_api: QueryApi = Depends(get_influx_query_api) # InfluxDB Query API dependency
'''
@app.get("/history/aggregated")
def get_history_aggregated(start_date: str, aggregation: str = "hour", query_api = Depends(get_influx_query_api)):
    '''
    Query InfluxDB for aggregated statistics.
    start_date example: '-1d', '-1h' or ISO string.
    '''
    
    # Map aggregation to Flux window period
    window_map = {"minute": "1m", "hour": "1h", "day": "1d"}
    window_period = window_map.get(aggregation, "1h")
    
    # Construct Flux Query
    # Use union and pivot to get all stats in one go and ensure time alignment
    query = f'''
    base = from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {start_date})
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
      |> group(columns: ["sensor_id"])

    min = base |> aggregateWindow(every: {window_period}, fn: min, createEmpty: false) |> map(fn: (r) => ({{r with _field: "min"}}))
    max = base |> aggregateWindow(every: {window_period}, fn: max, createEmpty: false) |> map(fn: (r) => ({{r with _field: "max"}}))
    mean = base |> aggregateWindow(every: {window_period}, fn: mean, createEmpty: false) |> map(fn: (r) => ({{r with _field: "mean"}}))
    std = base |> aggregateWindow(every: {window_period}, fn: stddev, createEmpty: false) |> map(fn: (r) => ({{r with _field: "std"}}))

    union(tables: [min, max, mean, std])
      |> pivot(rowKey:["_time", "sensor_id"], columnKey: ["_field"], valueColumn: "_value")
    '''

    result = query_api.query(query=query, org=INFLUXDB_ORG)

    if not result:
        # I should raise an exception here. 404 Not Found, meaning no data was found for the specified time range
        raise HTTPException(status_code=404, detail="No data found for the specified time range. Ensure producers.py is running.")

    output = []
    for table in result:
        for record in table.records:
            output.append({
                "time": record.get_time(),
                "sensor_id": record.values.get("sensor_id"),
                "min": record.values.get("min"),
                "max": record.values.get("max"),
                "avg": record.values.get("mean"),
                "std": record.values.get("std")
            })
    
    #? Why do we raise the same exception here?
    # In case the query returns an empty list.
    if not output:
         raise HTTPException(status_code=404, detail="No data found for the specified time range. Ensure producers.py is running.")

    return output

@app.get("/history/raw")
def get_history_raw(sensor_id: str, start_date: str, query_api = Depends(get_influx_query_api)):
    '''
    Query InfluxDB for raw sensor data.
    '''
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {start_date})
      |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
      |> filter(fn: (r) => r["_field"] == "value")
      |> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")
    '''
    
    result = query_api.query(query=query, org=INFLUXDB_ORG)
    
    if not result:
        raise HTTPException(status_code=404, detail="No data found for the specified time range and sensor. Are producers.py running?")

    output = []
    for table in result:
        for record in table.records:
            output.append({
                "time": record.get_time(),
                "value": record.get_value()
            })
            
    if not output:
        raise HTTPException(status_code=404, detail="No data found for the specified time range and sensor. Ensure producers.py is running.")
        
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
#? How to create a user?
# curl -X POST "http://localhost:8000/users/" -H "Content-Type: application/json" -d '{"username": "testuser", "password_hash": "testpass"}'
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

#? Why use Pydantic models?
# It benefits from type checking and validation
class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()

    if not user or user.password_hash != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"username": user.username, "id": user.id}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
