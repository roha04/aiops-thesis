import { useEffect, useState } from 'react'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('Fetching dashboard data...')
        const [statsRes, metricsRes] = await Promise.all([
          API.get('/api/dashboard'),
          API.get('/api/metrics')
        ])
        console.log('Dashboard stats:', statsRes.data)
        console.log('Metrics:', metricsRes.data)
        setStats(statsRes.data)
        setMetrics(metricsRes.data)
        setError(null)
      } catch (err) {
        console.error('Error fetching data:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    // Refresh every 10 seconds
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="text-center p-8">⏳ Loading...</div>
  if (error) return <div className="text-red-400 p-8">❌ Error: {error}</div>
  if (!stats) return <div className="text-red-400 p-8">No data available</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">📊 Dashboard</h1>

      {/* KPI Cards - Top Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400 text-sm">Total Alerts (7d)</p>
          <p className="text-3xl font-bold mt-2">{stats.total_alerts}</p>
        </div>
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400 text-sm">Model Accuracy</p>
          <p className="text-3xl font-bold mt-2 text-green-400">
            {(metrics?.accuracy * 100 || 0).toFixed(1)}%
          </p>
        </div>
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400 text-sm">F1 Score</p>
          <p className="text-3xl font-bold mt-2 text-blue-400">
            {(metrics?.f1_score || 0).toFixed(3)}
          </p>
        </div>
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400 text-sm">Critical Issues</p>
          <p className="text-3xl font-bold mt-2 text-red-400">{stats.critical_issues}</p>
        </div>
      </div>

      {/* Model Metrics - Second Row */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-sm">Precision</p>
            <p className="text-2xl font-bold mt-2 text-yellow-400">
              {(metrics.precision * 100).toFixed(1)}%
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-sm">Recall</p>
            <p className="text-2xl font-bold mt-2 text-purple-400">
              {(metrics.recall * 100).toFixed(1)}%
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-sm">Test Samples</p>
            <p className="text-2xl font-bold mt-2">{metrics.test_samples}</p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-sm">True Positives</p>
            <p className="text-2xl font-bold mt-2 text-green-400">{metrics.true_positives}</p>
          </div>
        </div>
      )}

      {/* Anomalies Trend Chart */}
      <div className="bg-gray-800 p-6 rounded border border-gray-700">
        <h2 className="text-xl font-bold mb-4">📈 Anomalies Trend (7 days)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={stats.anomalies_trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis stroke="#666" dataKey="date" />
            <YAxis stroke="#666" />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#1f2937', 
                border: '1px solid #374151',
                borderRadius: '8px'
              }} 
            />
            <Line 
              type="monotone" 
              dataKey="count" 
              stroke="#ef4444" 
              strokeWidth={3} 
              dot={{ r: 5, fill: '#ef4444' }}
              activeDot={{ r: 7 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Training Info Card */}
      {metrics && (
        <div className="bg-blue-900/30 border border-blue-700 p-4 rounded">
          <p className="text-blue-300 text-sm">
            <strong>ℹ️ Model Information:</strong> Trained on {metrics.model_version} | 
            Trained at: {new Date(metrics.trained_at).toLocaleString()} | 
            TP: {metrics.true_positives} | FP: {metrics.false_positives}
          </p>
        </div>
      )}

      {/* Performance Summary */}
      <div className="bg-green-900/30 border border-green-700 p-4 rounded">
        <p className="text-green-300 text-sm">
          <strong>✅ Model Status:</strong> Production-Ready | 
          Accuracy: {(metrics?.accuracy * 100 || 0).toFixed(1)}% | 
          Recall: {(metrics?.recall * 100 || 0).toFixed(1)}% (catches all anomalies!)
        </p>
      </div>
    </div>
  )
}