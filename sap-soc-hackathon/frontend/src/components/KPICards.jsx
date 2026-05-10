function scoreColor(score) {
  if (score == null) return 'text-white'
  if (score > 0.8) return 'text-red-400'
  if (score > 0.6) return 'text-orange-400'
  return 'text-green-400'
}

function Card({ icon, label, value, valueClass }) {
  return (
    <div className="rounded-xl p-5 border border-slate-700" style={{ backgroundColor: '#1e293b' }}>
      <div className="text-2xl mb-2">{icon}</div>
      <div className={`text-3xl font-bold ${valueClass ?? 'text-white'}`}>{value}</div>
      <div className="text-slate-400 text-sm mt-1">{label}</div>
    </div>
  )
}

export default function KPICards({ stats }) {
  if (!stats) return null

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <Card
        icon="📊"
        label="Total Logs"
        value={stats.total_logs?.toLocaleString('es-MX') ?? '—'}
      />
      <Card
        icon="⚠️"
        label="Anomalías"
        value={stats.total_anomalies ?? '—'}
        valueClass={stats.total_anomalies > 0 ? 'text-red-400' : 'text-white'}
      />
      <Card
        icon="🚨"
        label="Incidentes Abiertos"
        value={stats.open_incidents ?? '—'}
        valueClass={stats.open_incidents > 0 ? 'text-orange-400' : 'text-white'}
      />
      <Card
        icon="📨"
        label="Alertas Enviadas"
        value={stats.alerts_sent ?? '—'}
        valueClass="text-green-400"
      />
      <Card
        icon="🎯"
        label="Score Promedio"
        value={stats.avg_anomaly_score != null ? stats.avg_anomaly_score.toFixed(2) : '—'}
        valueClass={scoreColor(stats.avg_anomaly_score)}
      />
      <Card
        icon="⏱️"
        label="MTTD"
        value={stats.mttd_seconds != null ? `${stats.mttd_seconds}s` : '—'}
      />
    </div>
  )
}
