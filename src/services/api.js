import axios from 'axios'

// In development, Vite may serve the app without an API proxy; point to the
// running Flask backend directly. In production, keep relative '/api' paths.
const devBase = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.DEV)
  ? 'http://127.0.0.1:5001/api'
  : '/api'
const client = axios.create({ baseURL: devBase, timeout: 10000 })

export async function fetchKPIs() {
  const r = await client.get('/kpis')
  return r.data
}

export async function fetchInventory() {
  const r = await client.get('/inventory')
  const d = r.data
  // Normalize potential wrapper shapes to always return an array
  if (Array.isArray(d)) return d
  if (!d) return []
  // Common wrappers: { data: [...] } or { inventory: [...] }
  if (Array.isArray(d.data)) return d.data
  if (Array.isArray(d.inventory)) return d.inventory
  // If object has numeric keys like { '0': {...}, '1': {...} }, convert to values
  const keys = Object.keys(d)
  if (keys.length && keys.every(k => String(Number(k)) === String(k))) {
    return Object.keys(d).sort((a,b)=>Number(a)-Number(b)).map(k=>d[k])
  }
  // Fallback: wrap the object in an array
  return [d]
}

export async function fetchDemandTrends() {
  const r = await client.get('/demand-trends')
  const d = r.data
  if (Array.isArray(d)) return d
  if (d && Array.isArray(d.data)) return d.data
  return []
}

export async function fetchRecommendations() {
  const r = await client.get('/recommendations')
  return r.data
}

export default client
