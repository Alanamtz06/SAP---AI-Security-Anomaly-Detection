import { useState } from 'react'

const SEVERITY_STYLES = {
  CRITICAL: 'bg-red-900 text-red-300',
  HIGH: 'bg-orange-900 text-orange-300',
  MEDIUM: 'bg-yellow-900 text-yellow-300',
  LOW: 'bg-green-900 text-green-300',
}

function WebhookBadge({ status }) {
  if (status === 'SUCCESS') return <span className="text-green-400 font-medium">✓ OK</span>
  if (status === 'FAILED') return <span className="text-red-400 font-medium">✗ FAILED</span>
  return <span className="text-yellow-400 font-medium">⏳ PENDING</span>
}

export default function IncidentTable({ incidents }) {
  const [filter, setFilter] = useState('ALL')

  const sorted = [...(incidents || [])]
    .sort((a, b) => {
      if (!a.RESOLVED && b.RESOLVED) return -1
      if (a.RESOLVED && !b.RESOLVED) return 1
      return 0
    })
    .filter(inc => filter === 'ALL' || inc.SEVERITY === filter)
    .slice(0, 50)

  return (
    <div className="rounded-xl p-5 border border-slate-700" style={{ backgroundColor: '#1e293b' }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-semibold text-lg">Recent Incidents</h2>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="bg-slate-900 border border-slate-600 text-slate-300 text-sm rounded px-3 py-1"
        >
          <option value="ALL">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
      </div>
      {sorted.length === 0 ? (
        <p className="text-slate-400 text-center py-8">No active incidents</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400 text-left">
                <th className="pb-3 pr-4 font-medium">ID</th>
                <th className="pb-3 pr-4 font-medium">Severity</th>
                <th className="pb-3 pr-4 font-medium">Attack Type</th>
                <th className="pb-3 pr-4 font-medium">Score</th>
                <th className="pb-3 pr-4 font-medium">Source</th>
                <th className="pb-3 pr-4 font-medium">Webhook</th>
                <th className="pb-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(inc => (
                <tr key={inc.ID} className="border-b border-slate-800 hover:bg-slate-800 transition-colors">
                  <td className="py-3 pr-4 text-slate-300">{inc.ID}</td>
                  <td className="py-3 pr-4">
                    <span className={`px-2 py-1 rounded text-xs font-semibold ${SEVERITY_STYLES[inc.SEVERITY] ?? 'text-slate-300'}`}>
                      {inc.SEVERITY}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-slate-300">{inc.ATTACK_TYPE || '—'}</td>
                  <td className="py-3 pr-4 text-slate-300">{inc.ANOMALY_SCORE?.toFixed(2) ?? '—'}</td>
                  <td className="py-3 pr-4 text-slate-300">{inc.SOURCE_TABLE || '—'}</td>
                  <td className="py-3 pr-4">
                    <WebhookBadge status={inc.WEBHOOK_STATUS} />
                  </td>
                  <td className="py-3 text-slate-400 text-xs">
                    {inc.CREATED_AT ? new Date(inc.CREATED_AT).toLocaleString('en-US') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
