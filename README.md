# Sentinel Stream

## 🛡️ Enterprise Real-Time Fraud Detection Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-7.5-red.svg)](https://kafka.apache.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A production-grade, real-time fraud detection system that processes **50+ transactions per second** with **sub-2ms latency**, using Apache Kafka, Machine Learning, and a modern React dashboard.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🚀 **Real-Time Processing** | Stream processing with Apache Kafka at 50+ TPS |
| 🤖 **ML-Based Detection** | Isolation Forest anomaly detection |
| ⚡ **Velocity Detection** | Sliding window algorithm for burst attacks |
| 📊 **Live Dashboard** | Next.js dashboard with WebSocket updates |
| 📁 **Case Management** | Investigation workflows with SLA tracking |
| 📈 **Analytics** | KPIs, trends, and risk distribution |

---

## 🎯 Performance Metrics

| Metric | Value |
|--------|-------|
| **Throughput** | 50+ transactions/second |
| **Latency** | < 2ms average |
| **Risk Levels** | CRITICAL, HIGH, MEDIUM, LOW |
| **Uptime** | 99.9% availability |

---

## 🏗️ Architecture

```
┌──────────────┐     ┌─────────┐     ┌─────────────────┐     ┌────────────┐
│   Producer   │────▶│  Kafka  │────▶│  Fraud Engine   │────▶│ PostgreSQL │
│  (50 TPS)    │     │ Cluster │     │  (ML + Velocity)│     │  Database  │
└──────────────┘     └─────────┘     └────────┬────────┘     └────────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────┐
              │                               │                           │
              ▼                               ▼                           ▼
       ┌────────────┐                ┌────────────┐               ┌────────────┐
       │   Redis    │                │   Cases    │               │  Analytics │
       │   Cache    │                │   API      │               │    API     │
       └────────────┘                └────────────┘               └────────────┘
                                              │
                                              ▼
                                     ┌────────────────┐
                                     │   Dashboard    │
                                     │   (Next.js)    │
                                     └────────────────┘
```

---

## �️ Tech Stack

### Backend
- **Python 3.12** - Core language
- **FastAPI** - High-performance async API framework
- **Apache Kafka** - Distributed event streaming
- **PostgreSQL 16** - Relational database
- **Redis 7** - Caching layer

### Machine Learning
- **scikit-learn** - Isolation Forest model
- **NumPy/pandas** - Feature engineering

### Frontend
- **Next.js 14** - React framework
- **Recharts** - Data visualization
- **WebSocket** - Real-time updates

### Infrastructure
- **Docker & Docker Compose** - Container orchestration

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB RAM minimum

### Run the Platform

```bash
# Clone repository
git clone https://github.com/yourusername/sentinel-stream.git
cd sentinel-stream

# Start all services
docker-compose up -d --build

# Open dashboard
open http://localhost:3000
```

### Service Endpoints

| Service | Port | URL |
|---------|------|-----|
| Dashboard | 3000 | http://localhost:3000 |
| Consumer API | 8000 | http://localhost:8000 |
| Case Service | 8001 | http://localhost:8001 |
| Analytics | 8002 | http://localhost:8002 |
| Kafka | 9092 | localhost:9092 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |

---

## 📊 Dashboard Preview

The platform includes a **multi-page dashboard**:

- **Dashboard**: Real-time KPIs, live alerts, charts
- **Alerts**: Full alert table with filtering
- **Cases**: Investigation workflow management
- **Analytics**: Trends, distributions, reports
- **Customers**: 360° risk profiles

---

## 🔍 How It Works

### 1. Transaction Ingestion
Transactions flow into Kafka at 50+ TPS with realistic patterns.

### 2. Feature Engineering
Each transaction is transformed into ML features:
- Amount normalization
- Time-based features
- Velocity metrics
- Location risk scoring

### 3. Fraud Detection
Two-layer detection approach:
- **ML Model**: Isolation Forest for anomaly detection
- **Velocity Check**: Sliding window for burst attacks

### 4. Risk Classification

| Risk Level | Score | Velocity |
|------------|-------|----------|
| CRITICAL | ≥ 0.85 | 10+ txns/60s |
| HIGH | ≥ 0.70 | 8-9 txns/60s |
| MEDIUM | ≥ 0.55 | 6-7 txns/60s |
| LOW | ≥ 0.50 | 3-5 txns/60s |

### 5. Alert & Case Creation
- Alerts broadcast via WebSocket
- High-risk alerts auto-create investigation cases

---

## 📁 Project Structure

```
sentinel-stream/
├── services/
│   ├── consumer/        # Fraud detection engine
│   ├── producer/        # Transaction generator
│   ├── case-service/    # Case management
│   └── analytics-service/  # Analytics API
├── dashboard/           # Next.js frontend
├── database/            # SQL schemas
├── docker-compose.yml   # Orchestration
└── README.md
```

---

## � Configuration

Key environment variables:

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/db

# Detection Thresholds
FRAUD_SCORE_THRESHOLD=0.5
VELOCITY_THRESHOLD=3
VELOCITY_WINDOW_SECONDS=60
```

---

## 📝 API Examples

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Recent Alerts
```bash
curl http://localhost:8000/alerts/recent?limit=10
```

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/alerts');
ws.onmessage = (event) => {
    console.log(JSON.parse(event.data));
};
```

---

## 🧪 Running Tests

```bash
# Unit tests
pytest services/consumer/tests/

# Load testing
locust -f tests/load_test.py
```

---

## 🚀 Future Enhancements

- [ ] Graph-based fraud ring detection
- [ ] Geographic velocity (impossible travel)
- [ ] Deep learning models (LSTM/Transformer)
- [ ] Kubernetes deployment
- [ ] Mobile app

---

## 📜 License

MIT License - feel free to use for personal and commercial projects.

---

## 👨‍💻 Author

Muhammad Faozan Mujtaba

- LinkedIn: https://www.linkedin.com/in/fozan-mujtaba-6a85802a2/
- GitHub: https://github.com/fozanmujtaba
- Email: fozanmujtaba.480@gmail.com

---

## 🙏 Acknowledgments

- Apache Kafka team for the streaming platform
- scikit-learn contributors for ML tools
- Next.js team for the React framework

---
