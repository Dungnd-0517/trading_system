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

async function put(path, body = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json()
}

export const fetchHealth = () => fetch('/health').then((response) => response.json())
export const fetchHistory = (symbol = 'XAUUSD', timeframe = 'M1') =>
  get(`/market/history?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=500`)
export const fetchMarketIntegrity = (symbol = 'XAUUSD') =>
  get(`/market/integrity?symbol=${encodeURIComponent(symbol)}`)
export const healMarketGaps = (symbol = 'XAUUSD', lookbackHours = 168) =>
  post(`/market/heal?symbol=${encodeURIComponent(symbol)}&lookback_hours=${lookbackHours}`)
export const fetchOrders = (limit = 200) => get(`/orders?limit=${limit}`)
export const createOrder = (data) => post('/orders', data)
export const closeOrder = (orderId, reason = 'MANUAL_CLOSE') => post(`/orders/${orderId}/close`, { reason })
export const partialCloseOrder = (orderId, ratio = 0.5, reason = 'MANUAL_PARTIAL_TP') =>
  post(`/orders/${orderId}/partial-close`, { ratio, reason })
export const fetchSimulationAccount = () => get('/simulation/account')
export const fetchNews = (limit = 200) => get(`/news?limit=${limit}`)
export const fetchEconomicEvents = (limit = 200) => get(`/news/events?limit=${limit}`)
export const fetchNewsEvents = fetchEconomicEvents
export const fetchNewsStatus = () => get('/news/status')
export const fetchNewsSentiment = (limit = 100) => get(`/news/sentiment?limit=${limit}`)
export const triggerNewsAnalysis = (limit = 200) => post(`/news/analyze?limit=${limit}`)
export const fetchMarketAnalysis = (symbol = 'XAUUSD') => get(`/market/analysis?symbol=${encodeURIComponent(symbol)}`)
export const fetchSignals = (limit = 50, status = '') =>
  get(`/strategy/signals?limit=${limit}${status ? `&status=${encodeURIComponent(status)}` : ''}`)
export const evaluateSignals = (symbol = 'XAUUSD') =>
  post(`/strategy/signals/evaluate?symbol=${encodeURIComponent(symbol)}`)
export const executeSignal = (signalId) =>
  post(`/strategy/signals/${signalId}/execute`)
export const fetchTradingConfig = () => get('/strategy/config')
export const updateTradingConfig = (data) => put('/strategy/config', data)
export const runBacktest = (data) => post('/strategy/backtest', data)