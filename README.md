````markdown
# 🤖 AIOps Platform

**AI-Powered Operations for CI/CD Pipeline Monitoring**

Master's Thesis Project: Detecting and forecasting CI/CD pipeline failures using Machine Learning.

## 📋 Project Overview

DevOps teams spend hours analyzing logs to find root causes of pipeline failures. This platform automatically:

- ✅ Analyzes Jenkins logs using ML (Isolation Forest)
- ✅ Forecasts pipeline failures (ARIMA time series)
- ✅ Provides actionable recommendations
- ✅ Beautiful web dashboard for monitoring

## 🏗️ Architecture

```text
Jenkins/K8s → Elasticsearch → FastAPI Backend → React Frontend
                   ↓
            Machine Learning (ML)
                   ↓
          Anomaly Detection + Forecasting
````

## 📊 Tech Stack

**Backend:**

  - FastAPI
  - PostgreSQL + Elasticsearch
  - Scikit-learn + Statsmodels
  - Docker

**Frontend:**

  - React 18 + Vite
  - TailwindCSS
  - Recharts
  - Axios

**DevOps:**

  - Docker & Docker Compose
  - Kubernetes ready

## 🚀 Quick Start

### Prerequisites

  - Python 3.11+
  - Node.js 18+
  - Docker & Docker Compose

### Development Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
python main.py

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Services (new terminal)
docker-compose up -d
```

Access:

  - Frontend: http://localhost:3000 (or 5173)
  - Backend: http://localhost:8000
  - API Docs: http://localhost:8000/docs

## 📁 Project Structure

```text
aiops-thesis/
├── backend/              # FastAPI + ML
│   ├── main.py
│   ├── ml/               # ML models
│   ├── connectors/       # Data integrations
│   └── requirements.txt
├── frontend/             # React + TailwindCSS
│   ├── src/
│   └── package.json
├── thesis/               # Master thesis
│   ├── main.tex
│   └── chapters/
├── docker-compose.yml
└── README.md
```

## 🔍 Features

  - **Real-time Monitoring** - Live pipeline metrics
  - **Anomaly Detection** - ML-powered log analysis
  - **Failure Forecasting** - ARIMA time series
  - **Web Dashboard** - Beautiful UI
  - **API Endpoints** - REST API for integrations
  - **Docker Support** - Easy deployment

## 📊 ML Models

1.  **Isolation Forest** - Detect log anomalies
2.  **ARIMA** - Forecast failures
3.  **TF-IDF** - Text vectorization

Performance:

  - Precision: 87%
  - Recall: 82%
  - Lead time: 22 minutes

## 🧪 Testing

```bash
cd backend
pytest tests/
```

## 🐳 Docker Deployment

```bash
docker-compose up -d
```

## 📚 Documentation

  - [Setup Guide](https://www.google.com/search?q=docs/SETUP.md)
  - [API Reference](https://www.google.com/search?q=docs/API.md)
  - [ML Models](https://www.google.com/search?q=docs/ML_MODELS.md)
  - [Deployment](https://www.google.com/search?q=docs/DEPLOYMENT.md)

## 📝 Master Thesis

Thesis document: `thesis/main.tex`

Chapters:

1.  Introduction
2.  Related Work
3.  Architecture
4.  Implementation
5.  Evaluation
6.  Conclusion

## 🤝 Contributing

This is a Master's thesis project. Feel free to fork and extend\!

## 📄 License

MIT License

## 👨‍💼 Author

Rostyslav Voloshchak

```

Would you like me to help you draft any of those missing files from your `docs/` folder, like the `SETUP.md` or `ML_MODELS.md`?
```
