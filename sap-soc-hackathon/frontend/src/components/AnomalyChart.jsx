import { useMemo } from 'react'
import {
  LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'

export default function AnomalyChart({ anomalies }) {
  const data = useMemo(() => {
    if (!anomalies?.length) return []
    const counts = {}
    anomalies.forEach(a => {
      const hour = new Date(a.DETECTED_AT).getHours()
      const label = `${String(hour).padStart(2, '0')}:00`
      counts[label] = (counts[label] || 0) + 1
    })
    return Object.entries(counts)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([hora, cantidad]) => ({ hora, cantidad }))
  }, [anomalies])

  return (
    <div className="rounded-xl p-5 border border-slate-700 h-full" style={{ backgroundColor: '#1e293b' }}>
      <h2 className="text-white font-semibold text-lg mb-4">Anomalías Detectadas — Últimas 24h</h2>
      {data.length === 0 ? (
        <p className="text-slate-400 text-center py-16">Sin anomalías en el periodo</p>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="hora" stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#f1f5f9' }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Line
              type="monotone"
              dataKey="cantidad"
              stroke="#ef4444"
              strokeWidth={2}
              dot={{ fill: '#ef4444', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
