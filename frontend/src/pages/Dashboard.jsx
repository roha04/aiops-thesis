import { useEffect, useState } from 'react'
import axios from 'axios'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.get('/api/dashboard')
      .then(res => setStats(res.data))
      .catch(err => console.error('Error:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center">Loading...</div>
  if (!stats) return <div className="text-red-400">Error loading data</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">📊 Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <p className="text-gray-400">Total Alerts (7d)</p>
          <p className="text-2xl font-bold">{stats.total_alerts}</p>
        </div>
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <p className="text-gray-400">Model Accuracy</p>
          <p className="text-2xl font-bold">{(stats.model_accuracy * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <p className="text-gray-400">Avg Lead Time</p>
          <p className="text-2xl font-bold">{stats.avg_lead_time}</p>
        </div>
        <div className="bg-gray-800 p-4 rounded border border-gray-700">
          <p className="text-gray-400">Critical Issues</p>
          <p className="text-2xl font-bold text-red-400">{stats.critical_issues}</p>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-gray-800 p-4 rounded border border-gray-700">
        <h2 className="text-xl font-bold mb-4">Anomalies Trend</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={stats.anomalies_trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis stroke="#666" dataKey="date" />
            <YAxis stroke="#666" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
            <Line type="monotone" dataKey="count" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}