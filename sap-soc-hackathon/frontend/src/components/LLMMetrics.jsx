import { useMemo } from 'react'

const STATUS_COLOR = {
  SUCCESS: 'text-green-400',
  ERROR: 'text-red-400',
  TIMEOUT: 'text-orange-400',
}

export default function LLMMetrics({ logs }) {
  const llmLogs = useMemo(() => (logs || []).filter(l => l.source_type === 'llm'), [logs])

  const metrics = useMemo(() => {
    if (!llmLogs.length) return null
    const errorCount = llmLogs.filter(l => l.LLM_STATUS !== 'SUCCESS').length
    const totalCost = llmLogs.reduce((s, l) => s + (l.LLM_COST_USD || 0), 0)
    const avgTime = llmLogs.reduce((s, l) => s + (l.LLM_RESPONSE_TIME_MS || 0), 0) / llmLogs.length
    return {
      errorRate: ((errorCount / llmLogs.length) * 100).toFixed(1),
      totalCost: totalCost.toFixed(3),
      avgTime: (avgTime / 1000).toFixed(1),
    }
  }, [llmLogs])

  const recent = useMemo(() => llmLogs.slice(-5).reverse(), [llmLogs])

  return (
    <div className="rounded-xl p-5 border border-slate-700 h-full" style={{ backgroundColor: '#1e293b' }}>
      <h2 className="text-white font-semibold text-lg mb-4">LLM Metrics</h2>
      {!llmLogs.length ? (
        <p className="text-slate-400 text-center py-8">No LLM data available</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="rounded-lg p-3 bg-slate-900 text-center">
              <div className="text-2xl font-bold text-red-400">{metrics.errorRate}%</div>
              <div className="text-slate-400 text-xs mt-1">Error Rate</div>
            </div>
            <div className="rounded-lg p-3 bg-slate-900 text-center">
              <div className="text-2xl font-bold text-green-400">${metrics.totalCost}</div>
              <div className="text-slate-400 text-xs mt-1">Total Cost</div>
            </div>
            <div className="rounded-lg p-3 bg-slate-900 text-center">
              <div className="text-2xl font-bold text-blue-400">{metrics.avgTime}s</div>
              <div className="text-slate-400 text-xs mt-1">Avg Response Time</div>
            </div>
          </div>
          <h3 className="text-slate-400 text-xs uppercase tracking-wider mb-2">Recent LLM Logs</h3>
          <div className="space-y-2">
            {recent.map((log, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-slate-900 rounded px-3 py-2">
                <span className="text-slate-300 truncate max-w-[100px]">{log.LLM_MODEL_ID || '—'}</span>
                <span className={STATUS_COLOR[log.LLM_STATUS] ?? 'text-slate-400'}>{log.LLM_STATUS}</span>
                <span className="text-slate-400">
                  {log.LLM_RESPONSE_TIME_MS != null ? `${log.LLM_RESPONSE_TIME_MS}ms` : '—'}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
