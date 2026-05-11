import { useEffect, useState } from 'react'
import axios from 'axios'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ComposedChart, ScatterChart, Scatter
} from 'recharts'

const API = axios.create({ baseURL: 'http://localhost:8000' })

export default function Analytics() {
  const [rocData, setRocData] = useState(null)
  const [confusionMatrix, setConfusionMatrix] = useState(null)
  const [prData, setPrData] = useState(null)
  const [featureImportance, setFeatureImportance] = useState(null)
  const [modelComparison, setModelComparison] = useState(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        console.log('🔍 Starting Analytics fetch...')
        
        // Fetch all data
        const responses = await Promise.allSettled([
          API.get('/api/analytics/roc-curve'),
          API.get('/api/analytics/confusion-matrix'),
          API.get('/api/analytics/precision-recall'),
          API.get('/api/analytics/feature-importance'),
          API.get('/api/analytics/model-comparison'),
          API.get('/api/analytics/summary')
        ])

        console.log('📊 Responses:', responses)

        // Handle each response
        const [rocRes, cmRes, prRes, fiRes, mcRes, sumRes] = responses

        // ROC Curve
        if (rocRes.status === 'fulfilled') {
          console.log('✅ ROC Curve:', rocRes.value.data)
          setRocData(rocRes.value.data)
        } else {
          console.error('❌ ROC error:', rocRes.reason)
        }

        // Confusion Matrix
        if (cmRes.status === 'fulfilled') {
          console.log('✅ Confusion Matrix:', cmRes.value.data)
          setConfusionMatrix(cmRes.value.data)
        } else {
          console.error('❌ CM error:', cmRes.reason)
        }

        // Precision-Recall
        if (prRes.status === 'fulfilled') {
          console.log('✅ Precision-Recall:', prRes.value.data)
          setPrData(prRes.value.data)
        } else {
          console.error('❌ PR error:', prRes.reason)
        }

        // Feature Importance
        if (fiRes.status === 'fulfilled') {
          console.log('✅ Feature Importance:', fiRes.value.data)
          setFeatureImportance(fiRes.value.data)
        } else {
          console.error('❌ FI error:', fiRes.reason)
        }

        // Model Comparison
        if (mcRes.status === 'fulfilled') {
          console.log('✅ Model Comparison:', mcRes.value.data)
          setModelComparison(mcRes.value.data)
        } else {
          console.error('❌ MC error:', mcRes.reason)
        }

        // Summary
        if (sumRes.status === 'fulfilled') {
          console.log('✅ Summary:', sumRes.value.data)
          setSummary(sumRes.value.data)
        } else {
          console.error('❌ Summary error:', sumRes.reason)
        }

        setError(null)
      } catch (err) {
        console.error('❌ Critical error:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">📊 Розширена аналітика</h1>
        <div className="bg-blue-900/30 border border-blue-700 p-8 rounded text-center">
          <p className="text-blue-300">⏳ Завантаження аналітики...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">📊 Розширена аналітика</h1>
        <div className="bg-red-900/30 border border-red-700 p-8 rounded">
          <p className="text-red-300">❌ Помилка: {error}</p>
          <p className="text-red-300 text-sm mt-2">Перевірте консоль браузера (F12) та логи бекенду</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">📊 Розширена аналітика</h1>

      {/* Summary Cards */}
      {summary?.summary ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">Усього прогнозів</p>
            <p className="text-2xl font-bold mt-1">{summary.summary.total_predictions || 0}</p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">Частка аномалій</p>
            <p className="text-2xl font-bold mt-1 text-red-400">
              {typeof summary.summary.anomaly_rate === 'number' ? summary.summary.anomaly_rate.toFixed(1) : '0'}%
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">Точність моделі</p>
            <p className="text-2xl font-bold mt-1 text-green-400">
              {typeof summary.summary.model_accuracy === 'number' ? (summary.summary.model_accuracy * 100).toFixed(1) : '0'}%
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">F1-міра</p>
            <p className="text-2xl font-bold mt-1 text-blue-400">
              {typeof summary.summary.model_f1 === 'number' ? summary.summary.model_f1.toFixed(3) : '0'}
            </p>
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700">
            <p className="text-gray-400 text-xs">Усього сповіщень</p>
            <p className="text-2xl font-bold mt-1">{summary.summary.total_alerts || 0}</p>
          </div>
        </div>
      ) : (
        <div className="bg-gray-800 p-4 rounded border border-gray-700 text-gray-400">
          Дані зведення недоступні
        </div>
      )}

      {/* ROC Curve */}
      {rocData?.roc_curve && rocData.roc_curve.fpr && rocData.roc_curve.tpr ? (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-4">
            📈 ROC-крива (AUC = {rocData.roc_curve.auc?.toFixed(3) || '0.50'})
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis
                dataKey="x"
                type="number"
                label={{ value: 'Хибно-позитивна частка (FPR)', position: 'insideBottomRight', offset: -5 }}
                stroke="#666"
              />
              <YAxis
                dataKey="y"
                label={{ value: 'Істинно-позитивна частка (TPR)', angle: -90, position: 'insideLeft' }}
                stroke="#666"
              />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
              <Scatter
                name="ROC"
                data={rocData.roc_curve.fpr.map((x, i) => ({
                  x: parseFloat(x),
                  y: parseFloat(rocData.roc_curve.tpr[i])
                }))}
                stroke="#3b82f6"
                fill="#3b82f6"
              />
              <Scatter
                name="Випадковий"
                data={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                stroke="#666"
                fill="none"
                strokeDasharray="5 5"
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400">📈 Дані ROC-кривої недоступні</p>
        </div>
      )}

      {/* Precision-Recall Curve */}
      {prData?.precision_recall && prData.precision_recall.precision ? (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-4">
            📊 Precision-Recall (AP = {prData.precision_recall.average_precision?.toFixed(3) || '0.50'})
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={prData.precision_recall.recall.map((r, i) => ({
                recall: parseFloat(r).toFixed(2),
                precision: parseFloat(prData.precision_recall.precision[i]),
                f1: parseFloat(prData.precision_recall.f1_scores[i])
              }))}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis stroke="#666" dataKey="recall" label={{ value: 'Повнота', position: 'insideBottomRight', offset: -5 }} />
              <YAxis stroke="#666" label={{ value: 'Прецизійність', angle: -90, position: 'insideLeft' }} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
              <Legend />
              <Line type="monotone" dataKey="precision" stroke="#8b5cf6" strokeWidth={2} dot={false} name="Прецизійність" />
              <Line type="monotone" dataKey="f1" stroke="#ec4899" strokeWidth={2} dot={false} name="F1" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400">📊 Дані Precision-Recall недоступні</p>
        </div>
      )}

      {/* Confusion Matrix */}
      {confusionMatrix?.confusion_matrix ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gray-800 p-6 rounded border border-gray-700">
            <h2 className="text-xl font-bold mb-4">🔲 Матриця плутанини</h2>
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="bg-green-900/30 border border-green-700 p-4 rounded">
                <p className="text-xs text-gray-400">Істинно негативні</p>
                <p className="text-3xl font-bold text-green-400">{confusionMatrix.confusion_matrix.tn || 0}</p>
              </div>
              <div className="bg-red-900/30 border border-red-700 p-4 rounded">
                <p className="text-xs text-gray-400">Хибно позитивні</p>
                <p className="text-3xl font-bold text-red-400">{confusionMatrix.confusion_matrix.fp || 0}</p>
              </div>
              <div className="bg-red-900/30 border border-red-700 p-4 rounded">
                <p className="text-xs text-gray-400">Хибно негативні</p>
                <p className="text-3xl font-bold text-red-400">{confusionMatrix.confusion_matrix.fn || 0}</p>
              </div>
              <div className="bg-green-900/30 border border-green-700 p-4 rounded">
                <p className="text-xs text-gray-400">Істинно позитивні</p>
                <p className="text-3xl font-bold text-green-400">{confusionMatrix.confusion_matrix.tp || 0}</p>
              </div>
            </div>

            <div className="mt-6 space-y-2 text-sm">
              <div className="flex justify-between p-2 bg-gray-700/50 rounded">
                <span>TPR (чутливість):</span>
                <span className="font-bold">{typeof confusionMatrix.confusion_matrix.tpr === 'number' ? (confusionMatrix.confusion_matrix.tpr * 100).toFixed(1) : '0'}%</span>
              </div>
              <div className="flex justify-between p-2 bg-gray-700/50 rounded">
                <span>FPR:</span>
                <span className="font-bold">{typeof confusionMatrix.confusion_matrix.fpr === 'number' ? (confusionMatrix.confusion_matrix.fpr * 100).toFixed(1) : '0'}%</span>
              </div>
              <div className="flex justify-between p-2 bg-gray-700/50 rounded">
                <span>Специфічність:</span>
                <span className="font-bold">{typeof confusionMatrix.confusion_matrix.specificity === 'number' ? (confusionMatrix.confusion_matrix.specificity * 100).toFixed(1) : '0'}%</span>
              </div>
            </div>
          </div>

          {/* Feature Importance */}
          {featureImportance?.feature_importance && Array.isArray(featureImportance.feature_importance.features) ? (
            <div className="bg-gray-800 p-6 rounded border border-gray-700">
              <h2 className="text-xl font-bold mb-4">🎯 Важливість ознак</h2>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart
                  data={featureImportance.feature_importance.features.map((f, i) => ({
                    name: f,
                    importance: parseFloat(featureImportance.feature_importance.importance[i])
                  }))}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis type="number" stroke="#666" />
                  <YAxis dataKey="name" type="category" stroke="#666" width={120} tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} />
                  <Bar dataKey="importance" fill="#f59e0b" name="Важливість" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="bg-gray-800 p-6 rounded border border-gray-700">
              <p className="text-gray-400">🎯 Дані важливості ознак недоступні</p>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400">🔲 Дані матриці плутанини недоступні</p>
        </div>
      )}

      {/* Model Comparison */}
      {modelComparison?.comparison && modelComparison.comparison.length > 0 ? (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-1">📉 Порівняння класифікаторів (останній запуск)</h2>
          {modelComparison.training_run && (
            <p className="text-xs text-gray-400 mb-4">Запуск: {modelComparison.training_run}</p>
          )}
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={modelComparison.comparison}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis stroke="#666" dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis stroke="#666" domain={[0, 1]} tickFormatter={v => `${(v*100).toFixed(0)}%`} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                formatter={(value, name) => [`${(value * 100).toFixed(2)}%`, name]}
              />
              <Legend />
              <Bar dataKey="accuracy"  fill="#10b981" name="Точність" />
              <Bar dataKey="precision" fill="#f59e0b" name="Прецизійність" />
              <Bar dataKey="recall"    fill="#ef4444" name="Повнота" />
              <Line type="monotone" dataKey="f1_score"   stroke="#8b5cf6" strokeWidth={2} name="F1-міра" dot={{ r: 5 }} />
              <Line type="monotone" dataKey="roc_auc"    stroke="#06b6d4" strokeWidth={2} name="ROC-AUC" dot={{ r: 5 }} />
              <Line type="monotone" dataKey="cv_f1_mean" stroke="#f97316" strokeWidth={2} strokeDasharray="5 5" name="CV F1 (5-кратна)" dot={{ r: 4 }} />
            </ComposedChart>
          </ResponsiveContainer>

          {/* Per-model card summary */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mt-6">
            {modelComparison.comparison.map((m) => (
              <div
                key={m.name}
                className={`p-4 rounded border ${
                  m.is_best
                    ? 'border-green-500 bg-green-900/20'
                    : 'border-gray-600 bg-gray-700/30'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="font-semibold text-sm">{m.name}</p>
                  {m.is_best && (
                    <span className="text-xs bg-green-600 px-2 py-0.5 rounded">НАЙКРАЩА</span>
                  )}
                </div>
                <div className="space-y-1 text-xs text-gray-300">
                  <div className="flex justify-between">
                    <span>F1-міра</span>
                    <span className="font-bold text-white">{(m.f1_score * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>ROC-AUC</span>
                    <span className="font-bold text-cyan-400">{(m.roc_auc * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>CV F1 (5-кратна)</span>
                    <span className="font-bold text-orange-400">
                      {m.cv_f1_mean
                        ? `${(m.cv_f1_mean * 100).toFixed(2)}% ± ${m.cv_f1_std ? (m.cv_f1_std * 100).toFixed(2) : '?'}%`
                        : 'н/д (модель послідовностей)'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Точність</span>
                    <span>{(m.accuracy * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Прецизійність</span>
                    <span>{(m.precision * 100).toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Повнота</span>
                    <span>{(m.recall * 100).toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400">📉 Дані для порівняння моделей ще немає — спершу запустіть навчання.</p>
        </div>
      )}

      {/* Detailed Metrics Table */}
      {summary?.summary ? (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <h2 className="text-xl font-bold mb-4">📋 Детальні метрики</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-700">
                <tr>
                  <th className="text-left py-2 px-4">Метрика</th>
                  <th className="text-right py-2 px-4">Значення</th>
                  <th className="text-left py-2 px-4">Інтерпретація</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-700 hover:bg-gray-700/50">
                  <td className="py-2 px-4">Точність</td>
                  <td className="text-right font-bold">
                    {typeof summary.summary.model_accuracy === 'number' ? (summary.summary.model_accuracy * 100).toFixed(2) : '0'}%
                  </td>
                  <td className="text-gray-400">Частка правильних прогнозів від усіх</td>
                </tr>
                <tr className="border-b border-gray-700 hover:bg-gray-700/50">
                  <td className="py-2 px-4">F1-міра</td>
                  <td className="text-right font-bold">
                    {typeof summary.summary.model_f1 === 'number' ? summary.summary.model_f1.toFixed(3) : '0'}
                  </td>
                  <td className="text-gray-400">Баланс прецизійності та повноти</td>
                </tr>
                <tr className="border-b border-gray-700 hover:bg-gray-700/50">
                  <td className="py-2 px-4">Частка аномалій</td>
                  <td className="text-right font-bold">
                    {typeof summary.summary.anomaly_rate === 'number' ? summary.summary.anomaly_rate.toFixed(2) : '0'}%
                  </td>
                  <td className="text-gray-400">% прогнозів, позначених як аномалії</td>
                </tr>
                <tr className="border-b border-gray-700 hover:bg-gray-700/50">
                  <td className="py-2 px-4">Усього прогнозів</td>
                  <td className="text-right font-bold">{summary.summary.total_predictions || 0}</td>
                  <td className="text-gray-400">Кількість прогнозів у системі</td>
                </tr>
                <tr className="hover:bg-gray-700/50">
                  <td className="py-2 px-4">Тестових зразків</td>
                  <td className="text-right font-bold">{summary.summary.test_samples || 0}</td>
                  <td className="text-gray-400">Зразки, використані для оцінки</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-gray-800 p-6 rounded border border-gray-700">
          <p className="text-gray-400">📋 Детальні метрики недоступні</p>
        </div>
      )}

      {/* Footer */}
      <div className="bg-blue-900/30 border border-blue-700 p-4 rounded text-sm text-blue-300">
        <p>💡 <strong>Як використати ці дані в дипломній роботі:</strong></p>
        <ul className="mt-2 space-y-1 ml-4">
          <li>• ROC-крива: показує здатність моделі розрізняти класи</li>
          <li>• Матриця плутанини: розкладає істинно/хибно позитивні та негативні</li>
          <li>• Precision-Recall: компроміс між виявленням аномалій і хибними тривогами</li>
          <li>• Важливість ознак: показує, які ознаки логів найважливіші</li>
          <li>• Порівняння моделей: відстежує покращення з часом</li>
        </ul>
      </div>
    </div>
  )
}
