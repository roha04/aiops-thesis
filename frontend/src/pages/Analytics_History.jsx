import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ComposedChart, Area, AreaChart
} from 'recharts'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export default function AnalyticsHistory() {
  const [trainingHistory, setTrainingHistory] = useState(null)
  const [accuracyTrend, setAccuracyTrend] = useState(null)
  const [anomalyRate, setAnomalyRate] = useState(null)
  const [alertEffectiveness, setAlertEffectiveness] = useState(null)
  const [systemHealth, setSystemHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchHistoricalData = async () => {
      try {
        console.log('📚 Fetching historical analytics...')
        
        // Fetch all data
        const [trainingRes, accuracyRes, anomalyRes, alertRes, healthRes] = await Promise.all([
          API.get('/api/analytics/training-history'),
          API.get('/api/analytics/prediction-accuracy-trend?days=30'),
          API.get('/api/analytics/anomaly-detection-rate?days=30'),
          API.get('/api/analytics/alert-effectiveness'),
          API.get('/api/analytics/system-health')
        ])

        console.log('✅ Training history:', trainingRes.data)
        console.log('✅ Accuracy trend:', accuracyRes.data)
        console.log('✅ Anomaly rate:', anomalyRes.data)
        console.log('✅ Alert effectiveness:', alertRes.data)
        console.log('✅ System health:', healthRes.data)

        setTrainingHistory(trainingRes.data)
        setAccuracyTrend(accuracyRes.data)
        setAnomalyRate(anomalyRes.data)
        setAlertEffectiveness(alertRes.data)
        setSystemHealth(healthRes.data)
        setError(null)
        
      } catch (err) {
        console.error('❌ Error fetching data:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchHistoricalData()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">📚 Історична аналітика</h1>
        <div className="bg-blue-900/30 border border-blue-700 p-8 rounded text-center">
          <p className="text-blue-300">⏳ Завантаження історичних даних...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">📚 Історична аналітика</h1>
        <div className="bg-red-900/30 border border-red-700 p-8 rounded">
          <p className="text-red-300">❌ Помилка: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">📚 Історична аналітика — Метрики в часі</h1>

      {/* System Health Cards */}
      {systemHealth?.system_health && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">Відсоток успіху</p>
            <p className="text-2xl font-bold text-green-400 mt-1">
              {systemHealth.system_health.success_rate.toFixed(1)}%
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">Сер. час передбачення</p>
            <p className="text-2xl font-bold text-blue-400 mt-1">
              {systemHealth.system_health.avg_prediction_time_ms.toFixed(0)}ms
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">Розмір бази даних</p>
            <p className="text-2xl font-bold text-purple-400 mt-1">
              {systemHealth.system_health.db_size_mb.toFixed(1)}MB
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">Всього передбачень</p>
            <p className="text-2xl font-bold text-orange-400 mt-1">
              {systemHealth.system_health.total_predictions}
            </p>
          </div>
        </div>
      )}

      {/* Training History */}
      {trainingHistory?.training_history && trainingHistory.training_history.length > 0 ? (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-4">🎓 Історія навчання — Покращення моделі в часі</h2>
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={trainingHistory.training_history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis 
                stroke="#666" 
                dataKey="epoch" 
                label={{ value: 'Epoch', position: 'insideBottomRight', offset: -5 }} 
              />
              <YAxis stroke="#666" />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
              <Legend />
              <Bar dataKey="accuracy" fill="#10b981" name="Accuracy" />
              <Line type="monotone" dataKey="f1_score" stroke="#8b5cf6" strokeWidth={2} name="F1 Score" />
              <Line type="monotone" dataKey="train_loss" stroke="#ef4444" strokeWidth={2} name="Training Loss" />
            </ComposedChart>
          </ResponsiveContainer>
          <p className="text-gray-400 text-sm mt-2">Всього епох: {trainingHistory.training_history.length}</p>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400">🎓 Історія навчання ще недоступна. Спочатку запустіть навчання.</p>
        </div>
      )}

      {/* Prediction Accuracy Trend */}
      {accuracyTrend?.accuracy_trend && accuracyTrend.accuracy_trend.length > 0 ? (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-4">📈 Тренд точності передбачень (останні 30 днів)</h2>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={accuracyTrend.accuracy_trend}>
              <defs>
                <linearGradient id="colorAccuracy" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis stroke="#666" dataKey="day" />
              <YAxis stroke="#666" />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
              <Legend />
              <Area type="monotone" dataKey="accuracy" stroke="#10b981" fillOpacity={1} fill="url(#colorAccuracy)" name="Accuracy" />
              <Line type="monotone" dataKey="precision" stroke="#f59e0b" name="Precision" />
            </AreaChart>
          </ResponsiveContainer>
          <p className="text-gray-400 text-sm mt-2">Днів з даними: {accuracyTrend.accuracy_trend.length}</p>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400">📈 Тренд Accuracy недоступний</p>
        </div>
      )}

      {/* Anomaly Detection Rate */}
      {anomalyRate?.anomaly_rate_trend && anomalyRate.anomaly_rate_trend.length > 0 ? (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-4">🔍 Тренд рівня виявлення аномалій</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={anomalyRate.anomaly_rate_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis stroke="#666" dataKey="day" />
              <YAxis stroke="#666" label={{ value: 'Рівень аномалій (%)', angle: -90, position: 'insideLeft' }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
              <Legend />
              <Bar dataKey="anomaly_rate" fill="#ef4444" name="Рівень аномалій (%)" />
              <Bar dataKey="anomalies_detected" fill="#f97316" name="Виявлено аномалій" />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-gray-400 text-sm mt-2">Відстежено днів: {anomalyRate.anomaly_rate_trend.length}</p>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400">🔍 Дані рівня аномалій недоступні</p>
        </div>
      )}

      {/* Alert Effectiveness */}
      {alertEffectiveness?.alert_effectiveness && (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-4">🚨 Ефективність системи сповіщень</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-gray-400 text-sm">Всього сповіщень</p>
              <p className="text-3xl font-bold text-red-400 mt-2">
                {alertEffectiveness.alert_effectiveness.total_alerts}
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Вирішено</p>
              <p className="text-3xl font-bold text-green-400 mt-2">
                {alertEffectiveness.alert_effectiveness.resolved_alerts}
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Відсоток вирішення</p>
              <p className="text-3xl font-bold text-blue-400 mt-2">
                {alertEffectiveness.alert_effectiveness.resolution_rate.toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Сер. час вирішення</p>
              <p className="text-3xl font-bold text-purple-400 mt-2">
                {alertEffectiveness.alert_effectiveness.avg_resolution_time_hours.toFixed(1)}h
              </p>
            </div>
          </div>
          <div className="mt-4 p-4 bg-gray-700/50 rounded">
            <p className="text-sm text-gray-300">
              <strong>Типи сповіщень:</strong> Anomaly: {alertEffectiveness.alert_effectiveness.alert_types.ANOMALY} | 
              Forecast: {alertEffectiveness.alert_effectiveness.alert_types.FORECAST}
            </p>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="bg-blue-900/30 border border-blue-700 p-4 rounded text-sm text-blue-300">
        <p>💡 <strong>Для дипломної роботи:</strong></p>
        <ul className="mt-2 space-y-1 ml-4">
          <li>• Історія навчання: показує покращення моделі з часом</li>
          <li>• Тренди Accuracy: демонструє надійність передбачень в часі</li>
          <li>• Рівні аномалій: підтверджує здатність системи виявляти аномалії</li>
          <li>• Ефективність сповіщень: підтверджує практичну цінність для DevOps команд</li>
          <li>• Стан системи: показує метрики масштабованості та продуктивності</li>
        </ul>
      </div>
    </div>
  )
}