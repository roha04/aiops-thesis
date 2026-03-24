import { useEffect, useState, useRef, useCallback } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, Cell,
} from 'recharts'

const API = axios.create({ baseURL: 'http://localhost:8000' })

// ── colour helpers ────────────────────────────────────────────────────────────
const riskColour = (level) => ({
  HIGH: 'text-red-400',
  MEDIUM: 'text-yellow-400',
  LOW: 'text-green-400',
}[level] ?? 'text-gray-400')

const statusBadge = (status) => ({
  SUCCESS: 'bg-green-800 text-green-200',
  FAILURE: 'bg-red-800 text-red-200',
  ABORTED: 'bg-gray-700 text-gray-300',
  IN_PROGRESS: 'bg-blue-800 text-blue-200',
}[status] ?? 'bg-gray-700 text-gray-300')

const correctBadge = (correct) =>
  correct === true
    ? 'bg-green-800 text-green-200'
    : correct === false
      ? 'bg-red-800 text-red-200'
      : 'bg-gray-700 text-gray-400'

// ─────────────────────────────────────────────────────────────────────────────

export default function Jenkins() {
  const [jenkinsMode, setJenkinsMode] = useState('demo')
  const [overview, setOverview] = useState(null)
  const [comparison, setComparison] = useState([])
  const [builds, setBuilds] = useState([])
  const [jobs, setJobs] = useState([])
  const [selectedJob, setSelectedJob] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [streamLog, setStreamLog] = useState([])
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('overview') // overview | builds | comparison | stream
  const esRef = useRef(null)
  const streamEndRef = useRef(null)

  // ── data fetchers ─────────────────────────────────────────────────────────

  const fetchStatus = useCallback(async () => {
    try {
      const r = await API.get('/api/jenkins/status')
      setJenkinsMode(r.data.mode)
    } catch { /* silent */ }
  }, [])

  const fetchOverview = useCallback(async () => {
    try {
      const r = await API.get('/api/jenkins/overview')
      setOverview(r.data)
    } catch (e) {
      setError(e.message)
    }
  }, [])

  const fetchComparison = useCallback(async () => {
    try {
      const r = await API.get('/api/jenkins/comparison')
      setComparison(r.data.comparison)
    } catch { /* silent */ }
  }, [])

  const fetchHistory = useCallback(async () => {
    const params = selectedJob ? `?job_name=${encodeURIComponent(selectedJob)}` : ''
    try {
      const r = await API.get(`/api/jenkins/history${params}&limit=50`)
      setBuilds(r.data.builds)
    } catch { /* silent */ }
  }, [selectedJob])

  const fetchJobs = useCallback(async () => {
    try {
      const r = await API.get('/api/jenkins/jobs')
      setJobs(r.data.jobs)
    } catch { /* silent */ }
  }, [])

  const refreshAll = useCallback(async () => {
    await Promise.all([fetchOverview(), fetchComparison(), fetchHistory(), fetchJobs()])
  }, [fetchOverview, fetchComparison, fetchHistory, fetchJobs])

  useEffect(() => {
    fetchStatus()
    refreshAll()
    const iv = setInterval(refreshAll, 30_000)
    return () => clearInterval(iv)
  }, [refreshAll, fetchStatus])

  // re-fetch history when job filter changes
  useEffect(() => { fetchHistory() }, [fetchHistory])

  // scroll stream to bottom
  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamLog])

  // ── actions ───────────────────────────────────────────────────────────────

  const syncBuilds = async () => {
    setSyncing(true)
    setError(null)
    try {
      const params = selectedJob ? `?job_name=${encodeURIComponent(selectedJob)}&count=10` : '?count=10'
      await API.post(`/api/jenkins/sync${params}`)
      await refreshAll()
    } catch (e) {
      setError(e.message)
    } finally {
      setSyncing(false)
    }
  }

  const startStream = () => {
    if (esRef.current) {
      esRef.current.close()
    }
    setStreamLog([])
    setStreaming(true)
    setActiveTab('stream')

    const es = new EventSource('http://localhost:8000/api/jenkins/stream-demo')
    esRef.current = es

    es.onmessage = (ev) => {
      const data = JSON.parse(ev.data)
      if (data.done) {
        es.close()
        setStreaming(false)
        refreshAll()
        return
      }
      setStreamLog((prev) => [data, ...prev].slice(0, 50))
    }
    es.onerror = () => {
      es.close()
      setStreaming(false)
    }
  }

  const stopStream = () => {
    esRef.current?.close()
    setStreaming(false)
  }

  // cleanup on unmount
  useEffect(() => () => esRef.current?.close(), [])

  // ── chart data ────────────────────────────────────────────────────────────

  const chartData = comparison.map((c) => ({
    name: c.job_name.replace(/-/g, ' '),
    'Actual Failures': c.actual_failures,
    'Predicted Failures': c.predicted_failures,
    'FP': c.false_positives,
    'FN': c.false_negatives,
  }))

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">🔧 Jenkins Integration</h1>
          <p className="text-gray-400 text-sm mt-1">
            Real-time CI/CD monitoring · ML predictions · Failure tracking
          </p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Mode badge */}
          <span className={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${
            jenkinsMode === 'live' ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'
          }`}>
            {jenkinsMode === 'live' ? '🟢 Live Jenkins' : '🟡 Demo Mode'}
          </span>

          {/* Job filter */}
          <select
            value={selectedJob}
            onChange={(e) => setSelectedJob(e.target.value)}
            className="bg-gray-800 border border-gray-600 rounded px-3 py-1 text-sm"
          >
            <option value="">All Jobs</option>
            {jobs.map((j) => (
              <option key={j.name} value={j.name}>{j.name}</option>
            ))}
          </select>

          <button
            onClick={syncBuilds}
            disabled={syncing}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-4 py-2 rounded text-sm font-semibold"
          >
            {syncing ? '⏳ Syncing…' : '🔄 Sync Builds'}
          </button>

          <button
            onClick={streaming ? stopStream : startStream}
            className={`${streaming ? 'bg-red-600 hover:bg-red-700' : 'bg-purple-600 hover:bg-purple-700'} px-4 py-2 rounded text-sm font-semibold`}
          >
            {streaming ? '⏹ Stop Demo' : '▶ Live Demo'}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded">
          ❌ {error}
        </div>
      )}

      {/* Overview KPIs */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { label: 'Total Builds', value: overview.total_builds, color: 'text-white' },
            { label: 'Actual Failures', value: overview.actual_failures, color: 'text-red-400' },
            { label: 'Predicted Failures', value: overview.predicted_failures, color: 'text-yellow-400' },
            { label: 'Correct Predictions', value: overview.correct_predictions, color: 'text-green-400' },
            { label: 'Overall Accuracy', value: `${(overview.overall_accuracy * 100).toFixed(1)}%`, color: 'text-blue-400' },
            { label: 'High-Risk Builds', value: overview.high_risk_builds, color: 'text-red-300' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-800 p-4 rounded border border-gray-700">
              <p className="text-gray-400 text-xs">{label}</p>
              <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-gray-700">
        {[
          { id: 'overview', label: '📊 Chart' },
          { id: 'builds', label: '📋 Build History' },
          { id: 'comparison', label: '🎯 Comparison Table' },
          { id: 'stream', label: `📡 Live Stream${streaming ? ' 🔴' : ''}` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'border-b-2 border-blue-500 text-blue-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-4">Actual vs Predicted Failures per Job</h2>
          {chartData.length === 0 ? (
            <p className="text-gray-400 text-center py-8">
              No data yet. Click <strong>Sync Builds</strong> or run the <strong>Live Demo</strong>.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: '#1f2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#f9fafb' }}
                />
                <Legend />
                <Bar dataKey="Actual Failures" fill="#ef4444" radius={[3, 3, 0, 0]} />
                <Bar dataKey="Predicted Failures" fill="#f59e0b" radius={[3, 3, 0, 0]} />
                <Bar dataKey="FP" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
                <Bar dataKey="FN" fill="#ec4899" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

      {activeTab === 'builds' && (
        <div className="bg-gray-800 rounded border border-gray-700 overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-lg font-bold">Build History{selectedJob ? ` — ${selectedJob}` : ''}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-gray-400 text-left">
                  <th className="px-4 py-3">Job</th>
                  <th className="px-4 py-3">#</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Risk</th>
                  <th className="px-4 py-3">Predicted Fail</th>
                  <th className="px-4 py-3">Actual Fail</th>
                  <th className="px-4 py-3">Correct?</th>
                  <th className="px-4 py-3">Recommendation</th>
                  <th className="px-4 py-3">Time</th>
                </tr>
              </thead>
              <tbody>
                {builds.length === 0 && (
                  <tr>
                    <td colSpan={9} className="text-center text-gray-500 py-8">
                      No builds synced yet. Click <strong>Sync Builds</strong>.
                    </td>
                  </tr>
                )}
                {builds.map((b) => (
                  <tr key={b.id} className="border-b border-gray-700 hover:bg-gray-750">
                    <td className="px-4 py-2 font-mono text-xs">{b.job_name}</td>
                    <td className="px-4 py-2">
                      {b.build_url ? (
                        <a href={b.build_url} target="_blank" rel="noreferrer"
                          className="text-blue-400 hover:underline">#{b.build_number}</a>
                      ) : `#${b.build_number}`}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${statusBadge(b.status)}`}>
                        {b.status}
                      </span>
                    </td>
                    <td className={`px-4 py-2 font-semibold ${riskColour(b.risk_level)}`}>
                      {b.risk_level ?? '—'}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {b.predicted_failure == null ? '—' : b.predicted_failure ? '🔴 Yes' : '🟢 No'}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {b.actual_failure == null ? '—' : b.actual_failure ? '🔴 Yes' : '🟢 No'}
                    </td>
                    <td className="px-4 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded text-xs ${correctBadge(b.prediction_correct)}`}>
                        {b.prediction_correct == null ? '—' : b.prediction_correct ? '✓' : '✗'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-400 max-w-xs truncate">
                      {b.recommendation ?? '—'}
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">
                      {b.build_timestamp
                        ? new Date(b.build_timestamp).toLocaleString()
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'comparison' && (
        <div className="bg-gray-800 rounded border border-gray-700 overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-lg font-bold">Prediction vs Reality — Per Job</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-gray-400 text-left">
                  <th className="px-4 py-3">Job</th>
                  <th className="px-4 py-3 text-center">Total Builds</th>
                  <th className="px-4 py-3 text-center">Actual Failures</th>
                  <th className="px-4 py-3 text-center">Predicted Failures</th>
                  <th className="px-4 py-3 text-center">Correct</th>
                  <th className="px-4 py-3 text-center">False Positives</th>
                  <th className="px-4 py-3 text-center">False Negatives</th>
                  <th className="px-4 py-3 text-center">Accuracy</th>
                </tr>
              </thead>
              <tbody>
                {comparison.length === 0 && (
                  <tr>
                    <td colSpan={8} className="text-center text-gray-500 py-8">
                      No comparison data yet. Sync builds first.
                    </td>
                  </tr>
                )}
                {comparison.map((c) => (
                  <tr key={c.job_name} className="border-b border-gray-700 hover:bg-gray-750">
                    <td className="px-4 py-2 font-mono text-xs">{c.job_name}</td>
                    <td className="px-4 py-2 text-center">{c.total_builds}</td>
                    <td className="px-4 py-2 text-center text-red-400">{c.actual_failures}</td>
                    <td className="px-4 py-2 text-center text-yellow-400">{c.predicted_failures}</td>
                    <td className="px-4 py-2 text-center text-green-400">{c.correct_predictions}</td>
                    <td className="px-4 py-2 text-center text-purple-400">{c.false_positives}</td>
                    <td className="px-4 py-2 text-center text-pink-400">{c.false_negatives}</td>
                    <td className="px-4 py-2 text-center">
                      <span className={`font-bold ${
                        c.accuracy >= 0.75 ? 'text-green-400' :
                        c.accuracy >= 0.5 ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {(c.accuracy * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'stream' && (
        <div className="space-y-3">
          <div className="bg-gray-800 p-4 rounded border border-gray-700 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold">📡 Real-Time Build Stream</h2>
              <p className="text-xs text-gray-400 mt-1">
                SSE feed — each event is a Jenkins build with instant ML prediction.
              </p>
            </div>
            {streaming && (
              <span className="flex items-center gap-2 text-red-400 text-sm animate-pulse">
                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                LIVE
              </span>
            )}
          </div>

          {streamLog.length === 0 && !streaming && (
            <div className="bg-gray-800 p-8 rounded border border-gray-700 text-center text-gray-500">
              Press <strong>▶ Live Demo</strong> to start streaming real-time builds with ML predictions.
            </div>
          )}

          <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
            {streamLog.map((b, idx) => (
              <div
                key={`${b.job_name}-${b.build_number}-${idx}`}
                className="bg-gray-800 border border-gray-700 rounded p-4 grid grid-cols-1 md:grid-cols-5 gap-3 items-center"
              >
                <div>
                  <p className="text-xs text-gray-400">Job</p>
                  <p className="font-mono text-sm">{b.job_name}</p>
                  <p className="text-xs text-gray-500">#{b.build_number}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Status</p>
                  <span className={`px-2 py-0.5 rounded text-xs ${statusBadge(b.status)}`}>
                    {b.status}
                  </span>
                </div>
                <div>
                  <p className="text-xs text-gray-400">ML Prediction</p>
                  <p className="text-sm">
                    {b.predicted_failure ? '🔴 Failure' : '🟢 Success'}
                    {b.prediction_confidence != null && (
                      <span className="text-xs text-gray-500 ml-1">
                        ({(b.prediction_confidence * 100).toFixed(0)}%)
                      </span>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Risk</p>
                  <p className={`font-semibold text-sm ${riskColour(b.risk_level)}`}>
                    {b.risk_level ?? '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Correct?</p>
                  <span className={`px-2 py-0.5 rounded text-xs ${correctBadge(b.prediction_correct)}`}>
                    {b.prediction_correct == null ? '—' : b.prediction_correct ? '✓ Yes' : '✗ No'}
                  </span>
                </div>
              </div>
            ))}
            <div ref={streamEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
