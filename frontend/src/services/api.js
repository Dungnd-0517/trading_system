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

// Phase 03: TradingAgents LLM Services (Governor, Reflexion, Knowledge RAG)
export const fetchGovernorConsensus = () => get('/agents/governor/consensus')
export const fetchGovernorRuntimeParams = () => get('/agents/governor/runtime-params')
export const evaluateGovernor = () => post('/agents/governor/evaluate')
export const overrideGovernor = (data) => post('/agents/governor/override', data)
export const fetchExecutiveBriefing = () => get('/agents/governor/briefing')
export const sendGovernorDialogue = (message, isTest = false) =>
  post('/agents/governor/dialogue', { message, is_test: isTest })
export const respondTradeApproval = (dialogueId, action, isTest = false) =>
  post('/agents/governor/respond-approval', { dialogue_id: dialogueId, action, is_test: isTest })
export const fetchDialogueHistory = (limit = 50) =>
  get(`/agents/governor/dialogue/history?limit=${limit}`)

// Phase 03 Sprint 02: News & Event Agent
export const fetchNewsMacroReport = () => get('/agents/news/macro-report')
export const triggerNewsScan = () => post('/agents/news/trigger-scan')
export const fetchCircuitBreakerStatus = () => get('/agents/news/circuit-breaker-status')

// Phase 03 Sprint 02: Technical RAG Agent (Multi-School)
export const fetchTechnicalAnalysis = () => get('/agents/technical/analysis')
export const submitKnowledge = (data) => post('/agents/technical/knowledge/submit', data)
export const classifyKnowledge = (text) => post('/agents/technical/knowledge/classify', { text })
export const fetchKnowledgeSchools = () => get('/agents/technical/knowledge/schools')
export const seedKnowledge = () => post('/agents/technical/knowledge/seed')

// Phase 03 Sprint 02: Reflexion Agent (Rule Promotion)
export const fetchReflexionMemories = (limit = 20) => get(`/reflexion/memories?limit=${limit}`)
export const fetchReflexionStats = () => get('/reflexion/stats')
export const searchReflexionMemories = (query, limit = 5) =>
  get(`/reflexion/search?query=${encodeURIComponent(query)}&limit=${limit}`)
export const analyzeReflexionOrder = (orderId) => post(`/reflexion/analyze/${orderId}`)
export const fetchReflexionAnalytics = () => get('/agents/reflexion/analytics')
export const promoteReflexionRule = (memoryId) => post(`/agents/reflexion/promote-rule/${memoryId}`)
export const fetchReflexionFeedbackReport = (orderId) =>
  get(`/agents/reflexion/feedback-report/${orderId}`)

export const fetchKnowledgeStats = () => get('/knowledge/stats')
export const searchKnowledge = (query, category = '', limit = 5) =>
  get(`/knowledge/search?query=${encodeURIComponent(query)}${category ? `&category=${encodeURIComponent(category)}` : ''}&limit=${limit}`)
export const reindexKnowledge = () => post('/knowledge/reindex')