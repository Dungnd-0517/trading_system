const baseUrl = '/api/v1'

async function get(path) {
  const response = await fetch(`${baseUrl}${path}`)
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json()
}

async function post(path, body = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json()
}

export const fetchHealth = () => fetch('/health').then((response) => response.json())
export const fetchHistory = (symbol = 'XAUUSD', timeframe = 'M1') =>
  get(`/market/history?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=500`)
export const fetchOrders = (limit = 200) => get(`/orders?limit=${limit}`)
export const createOrder = (data) => post('/orders', data)
export const closeOrder = (orderId, reason = 'MANUAL_CLOSE') => post(`/orders/${orderId}/close`, { reason })
export const fetchSimulationAccount = () => get('/simulation/account')
export const fetchNews = (limit = 200) => get(`/news?limit=${limit}`)
export const fetchEconomicEvents = (limit = 200) => get(`/news/events?limit=${limit}`)
export const fetchNewsEvents = fetchEconomicEvents
export const fetchNewsStatus = () => get('/news/status')
export const fetchMarketAnalysis = (symbol = 'XAUUSD') => get(`/market/analysis?symbol=${encodeURIComponent(symbol)}`)