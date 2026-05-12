import { useState, useEffect } from 'react'
import Dashboard from './components/Dashboard.jsx'
import { fetchStats, fetchAnomalies, fetchIncidents, fetchLogs } from './services/api.js'

export default function App() {
  const [stats, setStats] = useState(null)
  const [anomalies, setAnomalies] = useState([])
  const [incidents, setIncidents] = useState([])
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)

  const loadData = async () => {
    try {
      const [s, a, i, l] = await Promise.all([
        fetchStats(),
        fetchAnomalies(),
        fetchIncidents(),
        fetchLogs(),
      ])
      setStats(s)
      setAnomalies(a)
      setIncidents(i)
      setLogs(l)
      setError(null)
      setLastRefresh(new Date())
    } catch (err) {
      console.error('Error fetching data:', err)
      setError('Connection lost — retrying...')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#0f172a' }}>
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
        <div className="flex items-center gap-4">
          <span className="text-2xl font-bold text-white tracking-wider">SAP SOC</span>
          <span className="text-slate-400 text-lg">AI Security Dashboard</span>
        </div>
        <div className="flex items-center gap-4">
          {lastRefresh && (
            <span className="text-slate-500 text-xs">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${error ? 'bg-red-400' : 'bg-green-400'} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${error ? 'bg-red-500' : 'bg-green-500'}`}></span>
            </span>
            <span className={`text-sm font-semibold tracking-widest ${error ? 'text-red-400' : 'text-green-400'}`}>
              {error ? 'ERROR' : 'LIVE'}
            </span>
          </div>
        </div>
      </header>
      {error && (
        <div className="bg-red-900 border-b border-red-700 px-6 py-2 text-red-300 text-sm flex items-center gap-2">
          <span>⚠</span>
          <span>{error}</span>
        </div>
      )}
      <Dashboard
        stats={stats}
        anomalies={anomalies}
        incidents={incidents}
        logs={logs}
        loading={loading}
      />
    </div>
  )
}
