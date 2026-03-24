/**
 * MSW (Mock Service Worker) request handlers.
 * Intercept all axios calls to http://localhost:8000 during unit tests.
 */
import { http, HttpResponse } from 'msw'

const BASE = 'http://localhost:8000'

// ── Fixture data ────────────────────────────────────────────────────────────

export const DASHBOARD_STATS = {
  total_alerts: 12,
  critical_issues: 3,
  avg_lead_time: '4m 12s',
  anomalies_trend: [
    { date: '2026-03-18', count: 2 },
    { date: '2026-03-19', count: 4 },
    { date: '2026-03-20', count: 1 },
  ],
}

export const METRICS = {
  accuracy: 0.92,
  precision: 0.90,
  recall: 0.89,
  f1_score: 0.895,
  test_samples: 200,
  true_positives: 89,
  false_positives: 10,
  model_version: 'v1.0',
  trained_at: '2026-03-20T10:00:00',
}

export const ALERTS = [
  {
    _id: '1',
    _source: {
      timestamp: '2026-03-24T09:00:00',
      pipeline_id: 'jenkins-deploy',
      severity: 'CRITICAL',
      message: 'Database connection timeout',
      is_resolved: false,
    },
  },
  {
    _id: '2',
    _source: {
      timestamp: '2026-03-24T08:30:00',
      pipeline_id: 'jenkins-test',
      severity: 'WARNING',
      message: 'Memory usage high',
      is_resolved: true,
    },
  },
]

export const PREDICTIONS = [
  {
    id: 1,
    pipeline_id: 'jenkins-build-123',
    risk_level: 'HIGH',
    anomaly_score: 0.85,
    predicted_failures: 3,
    created_at: '2026-03-24T09:00:00',
  },
  {
    id: 2,
    pipeline_id: 'jenkins-test-456',
    risk_level: 'LOW',
    anomaly_score: 0.10,
    predicted_failures: 0,
    created_at: '2026-03-24T08:00:00',
  },
]

export const PREDICTION_RESULT = {
  pipeline_id: 'jenkins-build-123',
  prediction_id: 42,
  timestamp: '2026-03-24T10:00:00',
  prediction: {
    risk_level: 'HIGH',
    score: 0.82,
    recommendation: '🔴 CRITICAL: Anomaly detected. Check logs immediately!',
    details: {
      log_anomaly: { is_anomaly: true, anomaly_score: -0.8, confidence: 0.9 },
      failure_forecast: { predicted_failures: 3, upper_bound: 5, lower_bound: 1, error: null },
    },
  },
}

export const ANALYTICS_SUMMARY = {
  summary: {
    total_predictions: 150,
    total_anomalies: 30,
    anomaly_rate: 20.0,
    total_alerts: 45,
    model_accuracy: 0.92,
    model_f1: 0.895,
    test_samples: 200,
  },
}

export const JENKINS_JOBS = {
  jobs: [
    { name: 'deploy-prod', url: 'http://jenkins/job/deploy-prod', color: 'blue' },
    { name: 'run-tests', url: 'http://jenkins/job/run-tests', color: 'red' },
  ],
}

// ── Handlers ────────────────────────────────────────────────────────────────

export const handlers = [
  http.get(`${BASE}/health`, () =>
    HttpResponse.json({ status: 'ok', service: 'AIOps Backend', version: '1.0.0' })
  ),

  http.get(`${BASE}/api/dashboard`, () =>
    HttpResponse.json(DASHBOARD_STATS)
  ),

  http.get(`${BASE}/api/metrics`, () =>
    HttpResponse.json(METRICS)
  ),

  http.get(`${BASE}/api/alerts`, () =>
    HttpResponse.json(ALERTS)
  ),

  http.get(`${BASE}/api/predictions`, () =>
    HttpResponse.json(PREDICTIONS)
  ),

  http.post(`${BASE}/api/predict`, () =>
    HttpResponse.json(PREDICTION_RESULT)
  ),

  http.get(`${BASE}/api/analytics/summary`, () =>
    HttpResponse.json(ANALYTICS_SUMMARY)
  ),

  http.get(`${BASE}/api/analytics/roc-curve`, () =>
    HttpResponse.json({
      roc_curve: {
        fpr: [0.0, 0.1, 0.3, 0.5, 1.0],
        tpr: [0.0, 0.5, 0.75, 0.9, 1.0],
        auc: 0.88,
        thresholds: [1.0, 0.8, 0.6, 0.4, 0.0],
      },
    })
  ),

  http.get(`${BASE}/api/analytics/training-history`, () =>
    HttpResponse.json({
      training_history: [
        { epoch: 1, accuracy: 0.80, f1_score: 0.78, loss: 0.5 },
        { epoch: 2, accuracy: 0.85, f1_score: 0.83, loss: 0.4 },
        { epoch: 3, accuracy: 0.90, f1_score: 0.88, loss: 0.3 },
      ],
    })
  ),

  http.get(`${BASE}/api/jenkins/jobs`, () =>
    HttpResponse.json(JENKINS_JOBS)
  ),
]
