import { useState } from 'react'
import axios from 'axios'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'

const API = axios.create({ baseURL: 'http://localhost:8000' })

// Map English risk-level enum values from the backend to Ukrainian labels.
const RISK_LABEL = {
  HIGH:   'ВИСОКИЙ РИЗИК',
  MEDIUM: 'СЕРЕДНІЙ РИЗИК',
  LOW:    'НИЗЬКИЙ РИЗИК',
}

export default function Predictor() {
  const [pipelineId, setPipelineId] = useState('jenkins-build-123')
  const [logs, setLogs] = useState('ERROR: Database connection timeout')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handlePredict = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await API.post(
        `/api/predict?pipeline_id=${encodeURIComponent(pipelineId)}&logs=${encodeURIComponent(logs)}`
      )
      console.log('Prediction result:', response.data)
      setResult(response.data)
    } catch (err) {
      console.error('Error:', err)
      setError(err.response?.data?.detail || err.message)
    }
    setLoading(false)
  }

  const getRiskColor = (level) => {
    if (level === 'HIGH') return 'bg-red-900 text-red-300 border-red-700'
    if (level === 'MEDIUM') return 'bg-yellow-900 text-yellow-300 border-yellow-700'
    return 'bg-green-900 text-green-300 border-green-700'
  }

  const getRiskIcon = (level) => {
    if (level === 'HIGH') return '🚨'
    if (level === 'MEDIUM') return '⚠️'
    return '✅'
  }

  // SHAP explanation comes from /api/predict in `result.prediction.shap_explanation`.
  // Each entry: { feature, shap_value, direction: 'anomaly'|'normal', tfidf }
  const shap = result?.prediction?.shap_explanation
  const shapFeatures = Array.isArray(shap?.features) ? shap.features : []
  const shapChartData = shapFeatures.map((f) => ({
    feature:    f.feature,
    shap_value: Number(f.shap_value),
    direction:  f.direction,
    tfidf:      Number(f.tfidf ?? 0),
  }))

  // Drain-parsed structured metadata.
  // Comes from /api/predict in `result.prediction.parsed_log`.
  const parsedLog = result?.prediction?.parsed_log

  const levelColor = (lvl) => {
    if (!lvl) return 'bg-gray-700 text-gray-200'
    if (lvl === 'ERROR' || lvl === 'FATAL' || lvl === 'CRITICAL') return 'bg-red-900 text-red-200'
    if (lvl === 'WARNING') return 'bg-yellow-900 text-yellow-200'
    if (lvl === 'INFO')    return 'bg-blue-900 text-blue-200'
    if (lvl === 'DEBUG')   return 'bg-gray-700 text-gray-300'
    return 'bg-gray-700 text-gray-200'
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-3xl font-bold">🔮 Прогноз</h1>

      <div className="bg-gray-800 p-6 rounded border border-gray-700 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">ID пайплайну</label>
          <input
            type="text"
            value={pipelineId}
            onChange={(e) => setPipelineId(e.target.value)}
            placeholder="напр., jenkins-build-123"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Зразок логів</label>
          <textarea
            value={logs}
            onChange={(e) => setLogs(e.target.value)}
            placeholder="Вставте логи сюди..."
            rows="6"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono text-sm"
          />
        </div>

        <button
          onClick={handlePredict}
          disabled={loading || !pipelineId || !logs}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-3 rounded font-semibold text-lg transition-colors"
        >
          {loading ? '⏳ Аналіз...' : '🚀 Прогнозувати'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 p-4 rounded">
          <p className="text-red-300">❌ Помилка: {error}</p>
        </div>
      )}

      {result && (
        <div className={`${getRiskColor(result.prediction.risk_level)} p-6 rounded border-2 border-current`}>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-4xl">{getRiskIcon(result.prediction.risk_level)}</span>
            <h2 className="text-3xl font-bold">
              {RISK_LABEL[result.prediction.risk_level] || result.prediction.risk_level}
            </h2>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between">
              <span>Бал ризику:</span>
              <span className="font-bold">{(result.prediction.score * 100).toFixed(1)}%</span>
            </div>

            <div className="flex justify-between">
              <span>Виявлено аномалію:</span>
              <span className="font-bold">{result.prediction.details.log_anomaly.is_anomaly ? 'ТАК ⚠️' : 'НІ ✅'}</span>
            </div>

            <div className="flex justify-between">
              <span>Впевненість:</span>
              <span className="font-bold">{(result.prediction.details.log_anomaly.confidence * 100).toFixed(1)}%</span>
            </div>

            <div className="border-t border-current opacity-50 pt-3 mt-3">
              <p className="text-sm font-semibold mb-2">Рекомендація:</p>
              <p className="text-sm">{result.prediction.recommendation}</p>
            </div>
          </div>

          <div className="mt-4 text-xs opacity-75">
            ID прогнозу: {result.prediction_id} | 
            Час: {new Date(result.timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}

      {result && parsedLog && (
        <div
          data-testid="parsed-log-card"
          className="bg-gray-800 p-6 rounded border border-gray-700"
        >
          <h2 className="text-xl font-bold mb-1">🧩 Розібраний лог (Drain)</h2>
          <p className="text-sm text-gray-400 mb-4">
            Структурні ознаки, видобуті алгоритмом Drain — подаються до
            класифікатора разом із TF-IDF.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">
                Шаблон події
              </p>
              <code
                data-testid="parsed-template"
                className="block bg-gray-900 text-gray-100 px-3 py-2 rounded font-mono text-xs break-all"
              >
                {parsedLog.template || '—'}
              </code>
              <p className="text-gray-500 text-xs mt-1">
                ID:{' '}
                <span data-testid="parsed-event-id" className="text-gray-300">
                  {parsedLog.event_id}
                </span>
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase text-gray-400 w-20">Рівень</span>
                <span
                  data-testid="parsed-level"
                  className={`px-2 py-0.5 rounded text-xs font-semibold ${levelColor(parsedLog.log_level)}`}
                >
                  {parsedLog.log_level}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase text-gray-400 w-20">Сервіс</span>
                <span data-testid="parsed-service" className="text-gray-200 font-mono text-xs">
                  {parsedLog.service || <em className="text-gray-500">немає</em>}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase text-gray-400 w-20">Δ часу</span>
                <span className="text-gray-200 font-mono text-xs">
                  {parsedLog.timestamp_delta_sec != null
                    ? `${parsedLog.timestamp_delta_sec.toFixed(2)} с`
                    : <em className="text-gray-500">—</em>}
                </span>
              </div>
            </div>
          </div>

          {Array.isArray(parsedLog.parameters) && parsedLog.parameters.length > 0 && (
            <div className="mt-4">
              <p className="text-gray-400 text-xs uppercase tracking-wider mb-2">
                Видобуті параметри
              </p>
              <div data-testid="parsed-parameters" className="flex flex-wrap gap-2">
                {parsedLog.parameters.map((p, i) => (
                  <code
                    key={`param-${i}`}
                    className="px-2 py-1 bg-gray-900 text-amber-300 rounded text-xs font-mono"
                  >
                    {p}
                  </code>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-1">🔍 Чому таке передбачення?</h2>
          <p className="text-sm text-gray-400 mb-4">
            Найвпливовіші ознаки моделі Random Forest
            <span className="text-red-400"> — червоні стовпці зміщують у бік аномалії</span>,
            <span className="text-green-400"> зелені — у бік норми</span>.
          </p>

          {shapChartData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={Math.max(180, 60 * shapChartData.length)}>
                <BarChart
                  data={shapChartData}
                  layout="vertical"
                  margin={{ top: 8, right: 24, left: 24, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis type="number" stroke="#aaa" tick={{ fontSize: 11 }} />
                  <YAxis
                    type="category"
                    dataKey="feature"
                    stroke="#ddd"
                    tick={{ fontSize: 12 }}
                    width={120}
                  />
                  <ReferenceLine x={0} stroke="#666" />
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151' }}
                    formatter={(v, _name, p) => [
                      `${Number(v).toFixed(4)}  (${p.payload.direction === 'anomaly' ? 'аномалія' : 'норма'})`,
                      'SHAP-значення',
                    ]}
                    labelStyle={{ color: '#e5e7eb' }}
                  />
                  <Bar dataKey="shap_value">
                    {shapChartData.map((entry, idx) => (
                      <Cell
                        key={`shap-cell-${idx}`}
                        fill={entry.direction === 'anomaly' ? '#ef4444' : '#10b981'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              {typeof shap?.base_value === 'number' && (
                <p className="mt-3 text-xs text-gray-500">
                  Модель: <span className="text-gray-300">{shap.model || 'Random Forest'}</span>
                  {' · '}
                  Базова ймовірність аномалії:&nbsp;
                  <span className="text-gray-300">
                    {(shap.base_value * 100).toFixed(1)}%
                  </span>
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-500">
              SHAP-пояснення недоступне — спочатку навчіть модель
              (POST <code className="text-gray-300">/api/train</code>).
            </p>
          )}
        </div>
      )}

      {/* Example logs */}
      <div className="bg-gray-800 p-4 rounded border border-gray-700">
        <p className="text-sm text-gray-400 mb-3">💡 Спробуйте ці приклади логів:</p>
        <div className="space-y-2 text-xs">
          <button
            onClick={() => setLogs('ERROR: Database connection timeout after 30s')}
            className="block w-full text-left p-2 hover:bg-gray-700 rounded text-red-400"
          >
            → ERROR: Database connection timeout after 30s
          </button>
          <button
            onClick={() => setLogs('WARNING: High memory usage detected (85%)')}
            className="block w-full text-left p-2 hover:bg-gray-700 rounded text-yellow-400"
          >
            → WARNING: High memory usage detected (85%)
          </button>
          <button
            onClick={() => setLogs('INFO: Build started for branch main')}
            className="block w-full text-left p-2 hover:bg-gray-700 rounded text-green-400"
          >
            → INFO: Build started for branch main
          </button>
        </div>
      </div>
    </div>
  )
}
