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
```

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
docker-compose up -d --build
```

This brings up the full stack including a local **Jenkins** with four
pre-configured pipeline jobs that POST to the backend webhook on every build.

| Service       | URL                                                  | Login           |
|---------------|------------------------------------------------------|-----------------|
| Frontend      | http://localhost:5173                                | —               |
| Backend / API | http://localhost:8000 (docs at `/docs`)              | —               |
| Jenkins       | http://localhost:8080                                | `admin` / `admin` |
| Postgres      | localhost:5432                                       | postgres / postgres |
| Elasticsearch | http://localhost:9200                                | —               |

## 🔧 Live Jenkins integration

The `jenkins/` folder builds a Jenkins-LTS image that:

  - installs `configuration-as-code`, `workflow-aggregator`, `job-dsl`, etc.
  - boots a single `admin/admin` user (no setup wizard)
  - seeds **four pipeline jobs**: `backend-tests`, `frontend-build`,
    `integration-tests`, `deploy-staging`
  - each job's `post { always }` step POSTs to
    `http://backend:8000/api/jenkins/webhook` so the platform reacts in
    real time — no polling.

End-to-end flow:

```text
                ┌─ Jenkins job finishes
                │
                ▼
POST /api/jenkins/webhook  ──►  ML pipeline runs on the log
                                │
                                ├─► JenkinsBuild row upserted
                                │
                                └─► Event broadcast on
                                    GET /api/jenkins/stream-live (SSE)
                                                │
                                                ▼
                                    Frontend "🪝 Webhooks" tab
                                    shows the build + ML verdict
                                    instantly.
```

Try it live:

  1. `docker-compose up -d --build`
  2. Open the frontend at http://localhost:5173, go to **🔧 Jenkins → 🪝 Webhooks**.
     The badge should flip to **📡 Webhook LIVE** within a few seconds.
  3. Click any **▶ job-name** button (or trigger from the Jenkins UI).
     The completed build appears in the Webhooks tab the moment Jenkins
     finishes — typically 2–4 seconds later.

Optional hardening: set `JENKINS_WEBHOOK_SECRET` in `docker-compose.yml`
and add `-H 'X-Webhook-Token: <secret>'` to the curl call inside each
`jenkins/jobs/*/config.xml`.

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
