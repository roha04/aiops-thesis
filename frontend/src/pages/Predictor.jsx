import { useState } from 'react'
import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

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

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-3xl font-bold">🔮 Predictor</h1>

      <div className="bg-gray-800 p-6 rounded border border-gray-700 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Pipeline ID</label>
          <input
            type="text"
            value={pipelineId}
            onChange={(e) => setPipelineId(e.target.value)}
            placeholder="e.g., jenkins-build-123"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Logs Sample</label>
          <textarea
            value={logs}
            onChange={(e) => setLogs(e.target.value)}
            placeholder="Paste log output here..."
            rows="6"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono text-sm"
          />
        </div>

        <button
          onClick={handlePredict}
          disabled={loading || !pipelineId || !logs}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-3 rounded font-semibold text-lg transition-colors"
        >
          {loading ? '⏳ Analyzing...' : '🚀 Predict'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 p-4 rounded">
          <p className="text-red-300">❌ Error: {error}</p>
        </div>
      )}

      {result && (
        <div className={`${getRiskColor(result.prediction.risk_level)} p-6 rounded border-2 border-current`}>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-4xl">{getRiskIcon(result.prediction.risk_level)}</span>
            <h2 className="text-3xl font-bold">{result.prediction.risk_level} RISK</h2>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between">
              <span>Risk Score:</span>
              <span className="font-bold">{(result.prediction.score * 100).toFixed(1)}%</span>
            </div>

            <div className="flex justify-between">
              <span>Anomaly Detected:</span>
              <span className="font-bold">{result.prediction.details.log_anomaly.is_anomaly ? 'YES ⚠️' : 'NO ✅'}</span>
            </div>

            <div className="flex justify-between">
              <span>Confidence:</span>
              <span className="font-bold">{(result.prediction.details.log_anomaly.confidence * 100).toFixed(1)}%</span>
            </div>

            <div className="border-t border-current opacity-50 pt-3 mt-3">
              <p className="text-sm font-semibold mb-2">Recommendation:</p>
              <p className="text-sm">{result.prediction.recommendation}</p>
            </div>
          </div>

          <div className="mt-4 text-xs opacity-75">
            Prediction ID: {result.prediction_id} | 
            Time: {new Date(result.timestamp).toLocaleTimeString()}
          </div>
        </div>
      )}

      {/* Example logs */}
      <div className="bg-gray-800 p-4 rounded border border-gray-700">
        <p className="text-sm text-gray-400 mb-3">💡 Try these log examples:</p>
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