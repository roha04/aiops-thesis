import { useState } from 'react'
import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export default function Predictor() {
  const [pipelineId, setPipelineId] = useState('jenkins-build-123')
  const [logs, setLogs] = useState('ERROR: Database timeout')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handlePredict = async () => {
    setLoading(true)
    try {
      const res = await API.post(`/api/predict?pipeline_id=${pipelineId}&logs=${logs}`)
      setResult(res.data)
    } catch (err) {
      console.error('Error:', err)
    }
    setLoading(false)
  }

  const getRiskColor = (level) => {
    if (level === 'HIGH') return 'bg-red-900 text-red-300'
    if (level === 'MEDIUM') return 'bg-yellow-900 text-yellow-300'
    return 'bg-green-900 text-green-300'
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
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded text-white"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Logs Sample</label>
          <textarea
            value={logs}
            onChange={(e) => setLogs(e.target.value)}
            rows="4"
            className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded text-white"
          />
        </div>

        <button
          onClick={handlePredict}
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-4 py-2 rounded font-semibold"
        >
          {loading ? '⏳ Analyzing...' : '🚀 Predict'}
        </button>
      </div>

      {result && (
        <div className={`${getRiskColor(result.prediction.risk_level)} p-6 rounded border-2 border-current`}>
          <h2 className="text-2xl font-bold mb-2">{result.prediction.risk_level}</h2>
          <p className="mb-2">Score: {(result.prediction.score * 100).toFixed(1)}%</p>
          <p className="font-semibold">{result.prediction.recommendation}</p>
        </div>
      )}
    </div>
  )
}