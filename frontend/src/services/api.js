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

async function patch(path, body = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new Error(`API ${response.status}`)
  return response.json()
}

async function del(path) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'DELETE',
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

// Phase 03 Sprint 03: Multi-Conversation Chat & HITL Studio
export const fetchConversations = (includeArchived = false, limit = 50, offset = 0) =>
  get(`/chat/conversations?include_archived=${includeArchived}&limit=${limit}&offset=${offset}`)
export const createConversation = (data = {}) => post('/chat/conversations', data)
export const fetchConversation = (id) => get(`/chat/conversations/${id}`)
export const updateConversation = (id, data = {}) => patch(`/chat/conversations/${id}`, data)
export const deleteConversation = (id) => del(`/chat/conversations/${id}`)
export const fetchConversationMessages = (id, limit = 100, offset = 0) =>
  get(`/chat/conversations/${id}/messages?limit=${limit}&offset=${offset}`)
export const sendConversationMessage = (id, data = {}) =>
  post(`/chat/conversations/${id}/messages`, data)
export const exportConversation = (id, format = 'markdown') =>
  get(`/chat/conversations/${id}/export?format=${format}`)
export const respondChatApproval = (dialogueId, action) =>
  post('/chat/respond-approval', { dialogue_id: dialogueId, action })
export const fetchChatMarketContext = () => get('/chat/market-context')
export const fetchAgentPersonas = () => get('/chat/personas')

// Phase 03 Sprint 03: Knowledge Ingestion & Standardized Strategies (Agent [VECTOR])
export async function uploadKnowledgeFile(formData) {
  const response = await fetch(`${baseUrl}/knowledge/upload-file`, {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `API ${response.status}`)
  }
  return response.json()
}

export const ingestKnowledgeUrl = (data) => post('/knowledge/ingest-url', data)
export const ingestKnowledgeMarkdown = (data) => post('/knowledge/ingest-markdown', data)
export const fetchStandardizedStrategies = (school = '') =>
  get(`/knowledge/standardized-strategies${school ? `?school=${encodeURIComponent(school)}` : ''}`)
export const fetchStandardizedStrategyDetail = (slug) =>
  get(`/knowledge/standardized-strategies/${encodeURIComponent(slug)}`)
export const fetchKnowledgeDocuments = () => get('/knowledge/documents')
export const seedStandardizedStrategies = () => post('/knowledge/seed-strategies')

// Phase 03 Sprint 03: MetaTrader 5 Bridge & Data Integration
export const fetchMt5Status = () => get('/market/mt5/status')
export const reconnectMt5 = () => post('/market/mt5/reconnect')
export const seedMt5History = (symbol = 'XAUUSD', fromDate = '2026-01-01', deleteOld = true) =>
  post(`/market/mt5/seed?symbol=${encodeURIComponent(symbol)}&from_date=${encodeURIComponent(fromDate)}&delete_old=${deleteOld}`)