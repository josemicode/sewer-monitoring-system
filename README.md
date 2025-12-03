# Sewer Monitoring System

A resilient, distributed system for real-time sewer sensor monitoring, featuring automatic failover and high-throughput data processing.

## Prerequisites

- **Docker & Docker Compose** (for Infrastructure)
- **Python 3.8+** (for Backend)
- **Node.js 16+** (for Frontend)

## Installation

### 1. Infrastructure Setup

Clone the repo and configure the environment:

```bash
git clone https://github.com/your-username/sewer-monitoring-system.git
cd sewer-monitoring-system
cp .env.example .env
```

Start the core services (Kafka, Zookeeper, InfluxDB Primary & Secondary):

```bash
docker-compose up -d --build
```

### 2. Backend Setup

Navigate to the backend and install dependencies:

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend Setup

Navigate to the frontend and install dependencies:

```bash
cd ../frontend
npm install
```

## Running the System

### 1. Start Backend Services

Use the **Orchestrator** to manage API, Consumers, and Sensors automatically:

```bash
# From backend/ directory
python orchestrator.py
```

_The orchestrator handles process resurrection and logging (see `backend/logs/`)._

### 2. Start Frontend Client

Launch the React dashboard:

```bash
# From frontend/ directory
npm run dev
```

Access the dashboard at **http://localhost:5173**.

## User Manual

### Dashboard

- **Live Monitor**: View real-time sine wave data from 4 sensors via WebSockets.
- **Alerts**: Visual indicators trigger when values exceed the threshold (28.0).
- **History**: Use the date picker to query aggregated historical data from InfluxDB.

### API & Tools

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) - Test API endpoints directly.
- **InfluxDB UI**: [http://localhost:8086](http://localhost:8086) - Login with credentials from `.env`.
- **Portainer**: [http://localhost:9000](http://localhost:9000) - Manage Docker containers.

## Architecture Highlights

- **Resilience**: Consumer automatically fails over to Secondary InfluxDB on error.
- **Orchestration**: Python script monitors and restarts dead services.
- **Performance**: Multiprocessing for sensors, AsyncIO for API, and Kafka for buffering.
