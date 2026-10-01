const baseUrl = '/api/v1'

async function get(path) {
  const response = await fetch(`${baseUrl}${path}`)
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json()
}

export const fetchHealth = () => fetch('/health').then((response) => response.json())
export const fetchHistory = (symbol = 'XAUUSD', timeframe = 'M1') =>
  get(`/market/history?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=500`)
export const fetchOrders = () => get('/orders')
export const fetchNews = () => get('/news')