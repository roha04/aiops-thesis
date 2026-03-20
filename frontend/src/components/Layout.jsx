import { Menu, X, Activity } from 'lucide-react'
import { useState } from 'react'

export default function Layout({ children, page, setPage, backendOnline }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const menuItems = [
  { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
  { id: 'predictor', label: '🔮 Predictor', icon: '🔮' },
  { id: 'analytics', label: '📈 Analytics', icon: '📈' },
  { id: 'analytics-history', label: '📚 History', icon: '📚' },
  { id: 'alerts', label: '🚨 Alerts', icon: '🚨' },
]

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-20'} bg-gray-800 border-r border-gray-700 transition-all duration-300 flex flex-col`}>
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          {sidebarOpen && <h1 className="text-xl font-bold">🤖 AIOps</h1>}
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-2 hover:bg-gray-700 rounded">
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`w-full text-left px-4 py-2 rounded transition-colors ${
                page === item.id
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-gray-700 text-gray-300'
              }`}
            >
              <span className="text-xl">{sidebarOpen ? item.label : item.icon}</span>
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center gap-2">
            <Activity size={16} className={`${backendOnline ? 'text-green-500' : 'text-red-500'} animate-pulse`} />
            {sidebarOpen && <span className="text-sm">{backendOnline ? 'Online' : 'Offline'}</span>}
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-gray-800 border-b border-gray-700 p-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold">AIOps Platform</h1>
          <div className={`px-3 py-1 rounded-full text-sm flex items-center gap-2 ${backendOnline ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
            <span className={`w-2 h-2 rounded-full animate-pulse ${backendOnline ? 'bg-green-500' : 'bg-red-500'}`}></span>
            Backend {backendOnline ? 'Online' : 'Offline'}
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  )
}