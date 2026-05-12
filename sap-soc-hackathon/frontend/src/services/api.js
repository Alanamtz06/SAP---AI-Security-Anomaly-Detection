import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const client = axios.create({ baseURL: `${BASE_URL}/api` })

export const fetchStats = () => client.get('/stats').then(r => r.data)
export const fetchAnomalies = () => client.get('/anomalies?limit=50&only_anomalies=true').then(r => r.data)
export const fetchIncidents = () => client.get('/incidents?limit=50').then(r => r.data)
export const fetchLogs = () => client.get('/logs?source=all&limit=100').then(r => r.data)
