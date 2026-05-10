import KPICards from './KPICards.jsx'
import AnomalyChart from './AnomalyChart.jsx'
import LLMMetrics from './LLMMetrics.jsx'
import IncidentTable from './IncidentTable.jsx'
import AttackerMap from './AttackerMap.jsx'

export default function Dashboard({ stats, anomalies, incidents, logs, loading }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-red-500"></div>
      </div>
    )
  }

  return (
    <main className="p-6 space-y-6">
      <KPICards stats={stats} />

      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-3">
          <AnomalyChart anomalies={anomalies} />
        </div>
        <div className="col-span-2">
          <LLMMetrics logs={logs} />
        </div>
      </div>

      <IncidentTable incidents={incidents} />
      <AttackerMap logs={logs} />
    </main>
  )
}
