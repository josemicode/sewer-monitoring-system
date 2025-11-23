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
