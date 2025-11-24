# Sewer Monitoring System

Installation Guide:

1. Clone the repository:

```bash
git clone https://github.com/your-username/sewer-monitoring-system.git
cd sewer-monitoring-system
```

2. Create a .env file based on the example:

```bash
cp .env.example .env
```

3. Build and run the containers:

```bash
docker-compose up --build
```

4. Access the application:
   (curl for testing)

```bash
curl -I http://localhost:8086/health; docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

- InfluxDB: http://localhost:8086
- Portainer: http://localhost:9000

5. Install backend dependencies:

- Go to backend and run this command to get a virtual enviroment for pip packages.
(And source it to use it)

```bash
python -m venv venv
```
```bash
source venv/bin/activate
```

- Now install the libraries
```bash
pip install -r requirements.txt
```

6. Run both the consumer and producer:

```bash
python consumer.py
```
(in another terminal)
```bash
python producers.py
```

You may now check system.log or run the following command to directly query InfluxDB:
```bash
docker exec -it influxdb influx query 'from(bucket: "${INFLUXDB_BUCKET}") |> range(start: -1h)'
```