import { useMemo } from 'react'

export default function AttackerMap({ logs }) {
  const topIPs = useMemo(() => {
    const systemLogs = (logs || []).filter(l => l.source_type === 'system' && l.CLIENT_IP)
    const counts = {}
    systemLogs.forEach(l => { counts[l.CLIENT_IP] = (counts[l.CLIENT_IP] || 0) + 1 })
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
  }, [logs])

  const max = topIPs[0]?.[1] || 1

  return (
    <div className="rounded-xl p-5 border border-slate-700" style={{ backgroundColor: '#1e293b' }}>
      <h2 className="text-white font-semibold text-lg mb-4">Top IPs Atacantes</h2>
      {topIPs.length === 0 ? (
        <p className="text-slate-400 text-center py-8">Sin actividad registrada</p>
      ) : (
        <div className="space-y-3">
          {topIPs.map(([ip, count]) => (
            <div key={ip} className="flex items-center gap-3">
              <span className="text-slate-300 text-sm font-mono w-36 shrink-0">{ip}</span>
              <div className="flex-1 bg-slate-900 rounded-full h-3 overflow-hidden">
                <div
                  className="h-full rounded-full bg-red-600 transition-all duration-500"
                  style={{ width: `${(count / max) * 100}%` }}
                />
              </div>
              <span className="text-slate-400 text-sm w-10 text-right shrink-0">{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
