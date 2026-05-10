import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const fetchStats = () => client.get('/stats').then(r => r.data)
export const fetchAnomalies = () => client.get('/anomalies?limit=50&only_anomalies=true').then(r => r.data)
export const fetchIncidents = () => client.get('/incidents?limit=50').then(r => r.data)
export const fetchLogs = () => client.get('/logs?source=all&limit=100').then(r => r.data)
