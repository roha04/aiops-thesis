import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Predictor from './pages/Predictor'
import Alerts from './pages/Alerts'
import axios from 'axios'

function App() {
  const [page, setPage] = useState('dashboard')
  const [backendOnline, setBackendOnline] = useState(false)

  useEffect(() => {
    // Check backend health
    axios.get('http://localhost:8000/health')
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false))
  }, [])

  return (
    <Layout page={page} setPage={setPage} backendOnline={backendOnline}>
      {page === 'dashboard' && <Dashboard />}
      {page === 'predictor' && <Predictor />}
      {page === 'alerts' && <Alerts />}
    </Layout>
  )
}

export default App