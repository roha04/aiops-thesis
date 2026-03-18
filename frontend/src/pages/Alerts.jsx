import { useEffect, useState } from 'react'
import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    API.get('/api/alerts?limit=20')
      .then(res => setAlerts(res.data))
      .catch(err => console.error('Error:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">🚨 Recent Alerts</h1>

      <div className="bg-gray-800 rounded border border-gray-700 overflow-hidden">
        <table className="w-full text-sm text-gray-300">
          <thead className="border-b border-gray-700 bg-gray-700">
            <tr>
              <th className="text-left py-3 px-4">Timestamp</th>
              <th className="text-left py-3 px-4">Pipeline</th>
              <th className="text-left py-3 px-4">Score</th>
              <th className="text-left py-3 px-4">Issue</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert, idx) => (
              <tr key={idx} className="border-b border-gray-700 hover:bg-gray-700/50">
                <td className="py-3 px-4">{alert._source.timestamp}</td>
                <td className="py-3 px-4">{alert._source.pipeline_id}</td>
                <td className="py-3 px-4">
                  <span className={`px-2 py-1 rounded ${Math.abs(alert._source.anomaly_score) > 0.7 ? 'bg-red-900 text-red-200' : 'bg-yellow-900 text-yellow-200'}`}>
                    {Math.abs(alert._source.anomaly_score).toFixed(2)}
                  </span>
                </td>
                <td className="py-3 px-4">{alert._source.log_snippet}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}