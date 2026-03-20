import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Predictor from './pages/Predictor'
import Analytics from './pages/Analytics'
import Alerts from './pages/Alerts'
import AnalyticsHistory from './pages/Analytics_History'
import axios from 'axios'

function App() {
  const [page, setPage] = useState('dashboard')
  const [backendOnline, setBackendOnline] = useState(false)

  useEffect(() => {
    // Check backend health
    const checkHealth = async () => {
      try {
        await axios.get('http://localhost:8000/health')
        setBackendOnline(true)
      } catch {
        setBackendOnline(false)
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Layout page={page} setPage={setPage} backendOnline={backendOnline}>
      {page === 'dashboard' && <Dashboard />}
      {page === 'predictor' && <Predictor />}
      {page === 'analytics' && <Analytics />}
      {page === 'alerts' && <Alerts />}
      {page === 'analytics-history' && <AnalyticsHistory />}  // ✨ ADD
    </Layout>
  )
}

export default App