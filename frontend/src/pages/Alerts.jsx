import { useEffect, useState } from 'react'
import axios from 'axios'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await API.get('/api/alerts?limit=50')
        console.log('Alerts:', res.data)
        setAlerts(res.data)
        setError(null)
      } catch (err) {
        console.error('Error fetching alerts:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchAlerts()
    // Refresh every 5 seconds
    const interval = setInterval(fetchAlerts, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="text-center p-8">⏳ Loading alerts...</div>
  if (error) return <div className="text-red-400 p-8">❌ Error: {error}</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">🚨 Recent Alerts</h1>

      {alerts.length === 0 ? (
        <div className="bg-green-900/30 border border-green-700 p-6 rounded text-center">
          <p className="text-green-300">✅ No alerts - all systems normal!</p>
        </div>
      ) : (
        <div className="bg-gray-800 rounded border border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-700 bg-gray-700 sticky top-0">
                <tr>
                  <th className="text-left py-3 px-4">Timestamp</th>
                  <th className="text-left py-3 px-4">Pipeline</th>
                  <th className="text-left py-3 px-4">Severity</th>
                  <th className="text-left py-3 px-4">Message</th>
                  <th className="text-left py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert, idx) => (
                  <tr key={idx} className="border-b border-gray-700 hover:bg-gray-700/50 transition-colors">
                    <td className="py-3 px-4 text-gray-300 text-xs">
                      {new Date(alert._source.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono text-blue-400">
                      {alert._source.pipeline_id}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-3 py-1 rounded text-xs font-semibold ${
                        alert._source.severity === 'CRITICAL'
                          ? 'bg-red-900 text-red-200'
                          : alert._source.severity === 'WARNING'
                          ? 'bg-yellow-900 text-yellow-200'
                          : 'bg-blue-900 text-blue-200'
                      }`}>
                        {alert._source.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-xs max-w-xs truncate">
                      {alert._source.message}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-3 py-1 rounded text-xs font-semibold ${
                        alert._source.is_resolved
                          ? 'bg-green-900 text-green-200'
                          : 'bg-orange-900 text-orange-200'
                      }`}>
                        {alert._source.is_resolved ? 'Resolved' : 'Open'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-red-900/30 border border-red-700 p-4 rounded">
          <p className="text-red-300 text-sm">🚨 Critical Alerts</p>
          <p className="text-2xl font-bold mt-2">
            {alerts.filter(a => a._source.severity === 'CRITICAL').length}
          </p>
        </div>
        <div className="bg-yellow-900/30 border border-yellow-700 p-4 rounded">
          <p className="text-yellow-300 text-sm">⚠️ Warnings</p>
          <p className="text-2xl font-bold mt-2">
            {alerts.filter(a => a._source.severity === 'WARNING').length}
          </p>
        </div>
        <div className="bg-blue-900/30 border border-blue-700 p-4 rounded">
          <p className="text-blue-300 text-sm">ℹ️ Info</p>
          <p className="text-2xl font-bold mt-2">
            {alerts.filter(a => a._source.severity === 'INFO').length}
          </p>
        </div>
      </div>
    </div>
  )
}