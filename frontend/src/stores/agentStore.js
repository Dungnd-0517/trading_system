import { reactive } from 'vue'
import {
  classifyKnowledge as classifyKnowledgeApi,
  evaluateGovernor as evaluateGovernorApi,
  fetchDialogueHistory as fetchDialogueHistoryApi,
  fetchExecutiveBriefing as fetchExecutiveBriefingApi,
  fetchGovernorConsensus,
  fetchGovernorRuntimeParams,
  fetchKnowledgeSchools as fetchKnowledgeSchoolsApi,
  fetchKnowledgeStats,
  fetchReflexionAnalytics as fetchReflexionAnalyticsApi,
  fetchReflexionMemories,
  fetchReflexionStats,
  overrideGovernor as overrideGovernorApi,
  promoteReflexionRule as promoteReflexionRuleApi,
  reindexKnowledge as reindexKnowledgeApi,
  respondTradeApproval as respondTradeApprovalApi,
  searchKnowledge as searchKnowledgeApi,
  searchReflexionMemories as searchReflexionMemoriesApi,
  sendGovernorDialogue as sendGovernorDialogueApi,
  submitKnowledge as submitKnowledgeApi,
  uploadKnowledgeFile as uploadKnowledgeFileApi,
  ingestKnowledgeUrl as ingestKnowledgeUrlApi,
  ingestKnowledgeMarkdown as ingestKnowledgeMarkdownApi,
  fetchStandardizedStrategies as fetchStandardizedStrategiesApi,
  fetchStandardizedStrategyDetail as fetchStandardizedStrategyDetailApi,
  fetchKnowledgeDocuments as fetchKnowledgeDocumentsApi,
  seedStandardizedStrategies as seedStandardizedStrategiesApi,
  fetchAgentCouncilStateApi,
} from '../services/api'

export const agentStore = reactive({
  // Council Deck (Bàn điều hành 4 Agent - Phase 03 Sprint 04)
  dashboard: {
    arbiter: {
      permission: 'ALLOWED',
      current_risk_percent: 1.0,
      sl_multiplier: 1.5,
      daily_drawdown_pct: 0.0,
      regime_tag: 'COMPRESSION_CHOP',
      reason_summary: 'Chờ phân tích hội đồng',
      hard_breaker_active: false,
    },
    sentinel: {
      sentiment_score: 0.0,
      circuit_breaker_active: false,
      circuit_breaker_status: 'NORMAL',
      dxy_bias: 'NEUTRAL',
      next_event: null,
      recent_news: [],
    },
    vector: {
      bias: 'NEUTRAL',
      regime: 'COMPRESSION_CHOP',
      confidence: 50,
      rag_similarity: 0,
      pattern_match: '',
      primary_school: 'GENERAL',
      suggested_trade_setup: null,
      action_recommendation: '',
    },
    scribe: {
      last_trade: null,
      active_memory_rules: [],
    },
    lastUpdated: null,
    loading: false,
  },

  // Governor State
  consensus: null,
  runtimeParams: null,
  loadingConsensus: false,
  evaluating: false,
  overriding: false,
  consensusError: null,
  lastEvaluatedAt: null,

  // Governor Dialogue & Cockpit State (Task 5)
  dialogueHistory: [],
  executiveBriefing: null,
  loadingDialogue: false,
  sendingDialogue: false,
  loadingBriefing: false,
  dialogueError: null,

  // Reflexion State
  memories: [],
  reflexionStats: {
    total_memories: 0,
    outcomes: {},
    mistake_categories: {},
  },
  learningAnalytics: null,
  loadingMemories: false,
  memorySearchResults: [],
  searchingMemories: false,
  promotingRuleId: null,

  // RAG Knowledge State (Multi-School & Standardized Strategies)
  knowledgeStats: {
    total_chunks: 18,
    categories: {},
  },
  knowledgeSchools: [],
  knowledgeSearchResults: [],
  searchingKnowledge: false,
  reindexing: false,
  submittingKnowledge: false,

  // Standardized Trading Strategies & Ingestion State
  standardizedStrategies: [],
  selectedStrategyDetail: null,
  knowledgeDocuments: [],
  loadingStrategies: false,
  loadingDocuments: false,
  ingestingKnowledge: false,
  ingestionResult: null,
  ingestionError: null,

  // Actions: Governor Consensus
  async refreshConsensus() {
    this.loadingConsensus = true
    this.consensusError = null
    try {
      const data = await fetchGovernorConsensus()
      this.consensus = data
      this.runtimeParams = data.active_params
      this.lastEvaluatedAt = new Date()
    } catch (err) {
      this.consensusError = err.message || 'Không thể tải đồng thuận Governor'
    } finally {
      this.loadingConsensus = false
    }
  },

  async evaluateConsensus() {
    this.evaluating = true
    this.consensusError = null
    try {
      const data = await evaluateGovernorApi()
      this.consensus = data
      this.runtimeParams = data.active_params
      this.lastEvaluatedAt = new Date()
      return data
    } catch (err) {
      this.consensusError = err.message || 'Lỗi khi kích hoạt đánh giá Governor'
      throw err
    } finally {
      this.evaluating = false
    }
  },

  async overrideParams(payload) {
    this.overriding = true
    try {
      const res = await overrideGovernorApi(payload)
      if (res?.active_params) {
        this.runtimeParams = res.active_params
        if (this.consensus) {
          this.consensus.active_params = res.active_params
        }
      }
      return res
    } finally {
      this.overriding = false
    }
  },

  // Actions: Trader - Governor Dialogue & Human-in-the-Loop
  async refreshDialogueHistory(limit = 50) {
    this.loadingDialogue = true
    this.dialogueError = null
    try {
      const history = await fetchDialogueHistoryApi(limit)
      this.dialogueHistory = history || []
    } catch (err) {
      this.dialogueError = err.message || 'Không thể tải lịch sử đối thoại'
    } finally {
      this.loadingDialogue = false
    }
  },

  async sendDialogue(message, isTest = false) {
    if (!message?.trim()) return
    this.sendingDialogue = true
    this.dialogueError = null
    try {
      const res = await sendGovernorDialogueApi(message, isTest)
      // Thêm ngay lập tức hoặc làm tươi lại lịch sử đối thoại
      await this.refreshDialogueHistory()
      if (res?.active_params) {
        this.runtimeParams = res.active_params
        if (this.consensus) {
          this.consensus.active_params = res.active_params
        }
      }
      return res
    } catch (err) {
      this.dialogueError = err.message || 'Lỗi khi gửi thông điệp tới Governor'
      throw err
    } finally {
      this.sendingDialogue = false
    }
  },

  async loadExecutiveBriefing() {
    this.loadingBriefing = true
    try {
      const briefing = await fetchExecutiveBriefingApi()
      this.executiveBriefing = briefing
      await this.refreshDialogueHistory()
      return briefing
    } catch (err) {
      console.error('Lỗi khi tải Executive Briefing:', err)
      throw err
    } finally {
      this.loadingBriefing = false
    }
  },

  async respondApproval(dialogueId, action, isTest = false) {
    try {
      const res = await respondTradeApprovalApi(dialogueId, action, isTest)
      await this.refreshDialogueHistory()
      return res
    } catch (err) {
      console.error('Lỗi khi phản hồi phê duyệt lệnh:', err)
      throw err
    }
  },

  applyDialogueMessage(event) {
    if (event?.dialogue) {
      const exists = this.dialogueHistory.some((m) => m.id === event.dialogue.id)
      if (!exists) {
        this.dialogueHistory.push(event.dialogue)
      }
    } else if (event?.governor_message) {
      this.refreshDialogueHistory()
    }
  },

  // Actions: Reflexion Agent & Rule Promotion
  async refreshMemories(limit = 20) {
    this.loadingMemories = true
    try {
      const [list, stats, analytics] = await Promise.all([
        fetchReflexionMemories(limit).catch(() => []),
        fetchReflexionStats().catch(() => ({ total_memories: 0, outcomes: {}, mistake_categories: {} })),
        fetchReflexionAnalyticsApi().catch(() => null),
      ])
      this.memories = list || []
      this.reflexionStats = stats || { total_memories: 0, outcomes: {}, mistake_categories: {} }
      this.learningAnalytics = analytics
    } finally {
      this.loadingMemories = false
    }
  },

  async searchMemories(query) {
    if (!query?.trim()) {
      this.memorySearchResults = []
      return
    }
    this.searchingMemories = true
    try {
      this.memorySearchResults = await searchReflexionMemoriesApi(query, 5)
    } finally {
      this.searchingMemories = false
    }
  },

  async promoteRule(memoryId) {
    this.promotingRuleId = memoryId
    try {
      const res = await promoteReflexionRuleApi(memoryId)
      await Promise.all([this.refreshMemories(), this.refreshKnowledge()])
      return res
    } finally {
      this.promotingRuleId = null
    }
  },

  // Actions: Technical RAG Multi-School Knowledge
  async refreshKnowledge() {
    try {
      const [stats, schools] = await Promise.all([
        fetchKnowledgeStats().catch(() => ({ total_chunks: 18, categories: {} })),
        fetchKnowledgeSchoolsApi().catch(() => []),
      ])
      this.knowledgeStats = stats
      this.knowledgeSchools = schools || []
    } catch {
      // Keep default
    }
  },

  async searchKnowledge(query, category = '', limit = 6) {
    if (!query?.trim()) {
      this.knowledgeSearchResults = []
      return
    }
    this.searchingKnowledge = true
    try {
      this.knowledgeSearchResults = await searchKnowledgeApi(query, category, limit)
    } finally {
      this.searchingKnowledge = false
    }
  },

  async submitKnowledgeDoc(doc) {
    this.submittingKnowledge = true
    try {
      const res = await submitKnowledgeApi(doc)
      await this.refreshKnowledge()
      return res
    } finally {
      this.submittingKnowledge = false
    }
  },

  async classifyText(text) {
    return await classifyKnowledgeApi(text)
  },

  async triggerReindex() {
    this.reindexing = true
    try {
      const res = await reindexKnowledgeApi()
      await Promise.all([this.refreshKnowledge(), this.refreshKnowledgeDocuments(), this.refreshStandardizedStrategies()])
      return res
    } finally {
      this.reindexing = false
    }
  },

  // Actions: Phase 03 Sprint 03 - Standardized Trading Strategies & Ingestion
  async refreshStandardizedStrategies(school = '') {
    this.loadingStrategies = true
    try {
      const data = await fetchStandardizedStrategiesApi(school)
      this.standardizedStrategies = data || []
    } catch {
      this.standardizedStrategies = []
    } finally {
      this.loadingStrategies = false
    }
  },

  async loadStrategyDetail(slug) {
    try {
      const data = await fetchStandardizedStrategyDetailApi(slug)
      this.selectedStrategyDetail = data
      return data
    } catch {
      return null
    }
  },

  async refreshKnowledgeDocuments() {
    this.loadingDocuments = true
    try {
      const data = await fetchKnowledgeDocumentsApi()
      this.knowledgeDocuments = data || []
    } catch {
      this.knowledgeDocuments = []
    } finally {
      this.loadingDocuments = false
    }
  },

  async uploadFile(formData) {
    this.ingestingKnowledge = true
    this.ingestionError = null
    try {
      const res = await uploadKnowledgeFileApi(formData)
      this.ingestionResult = res
      await Promise.all([
        this.refreshKnowledge(),
        this.refreshKnowledgeDocuments(),
        this.refreshStandardizedStrategies(),
      ])
      return res
    } catch (err) {
      this.ingestionError = err.message || 'Lỗi khi tải lên file tài liệu'
      throw err
    } finally {
      this.ingestingKnowledge = false
    }
  },

  async ingestUrl(payload) {
    this.ingestingKnowledge = true
    this.ingestionError = null
    try {
      const res = await ingestKnowledgeUrlApi(payload)
      this.ingestionResult = res
      await Promise.all([
        this.refreshKnowledge(),
        this.refreshKnowledgeDocuments(),
        this.refreshStandardizedStrategies(),
      ])
      return res
    } catch (err) {
      this.ingestionError = err.message || 'Lỗi khi nạp liên kết tài liệu'
      throw err
    } finally {
      this.ingestingKnowledge = false
    }
  },

  async ingestMarkdown(payload) {
    this.ingestingKnowledge = true
    this.ingestionError = null
    try {
      const res = await ingestKnowledgeMarkdownApi(payload)
      this.ingestionResult = res
      await Promise.all([
        this.refreshKnowledge(),
        this.refreshKnowledgeDocuments(),
        this.refreshStandardizedStrategies(),
      ])
      return res
    } catch (err) {
      this.ingestionError = err.message || 'Lỗi khi nạp nội dung Markdown'
      throw err
    } finally {
      this.ingestingKnowledge = false
    }
  },

  async seedBaselineStrategies() {
    try {
      const res = await seedStandardizedStrategiesApi()
      await Promise.all([
        this.refreshKnowledge(),
        this.refreshKnowledgeDocuments(),
        this.refreshStandardizedStrategies(),
      ])
      return res
    } catch {
      return null
    }
  },

  // Actions: Council Deck (Bàn điều hành 4 Agent - Sprint 04)
  async hydrateCouncilState(includeTest = false) {
    this.dashboard.loading = true
    try {
      const data = await fetchAgentCouncilStateApi(includeTest)
      if (data?.payload) {
        this.updateAgentDashboardState(data.payload)
      }
      return data
    } catch (err) {
      console.warn('Lỗi khi nạp Council State ban đầu:', err)
      return null
    } finally {
      this.dashboard.loading = false
    }
  },

  updateAgentDashboardState(payload) {
    if (!payload) return
    if (payload.arbiter) Object.assign(this.dashboard.arbiter, payload.arbiter)
    if (payload.sentinel) Object.assign(this.dashboard.sentinel, payload.sentinel)
    if (payload.vector) Object.assign(this.dashboard.vector, payload.vector)
    if (payload.scribe) Object.assign(this.dashboard.scribe, payload.scribe)
    this.dashboard.lastUpdated = new Date()
  },

  async toggleEmergencyHalt(reason = 'Khóa khẩn cấp từ Bàn điều hành Trader') {
    const isCurrentlyAllowed = this.dashboard.arbiter.permission === 'ALLOWED'
    const newAllowedState = !isCurrentlyAllowed
    this.dashboard.arbiter.permission = newAllowedState ? 'ALLOWED' : 'BLOCKED'
    return await this.overrideParams({
      trading_allowed: newAllowedState,
      halt_reason: newAllowedState ? null : reason,
    })
  },

  applyGovernorUpdate(event) {
    if (event.data) {
      this.runtimeParams = event.data
      if (this.consensus) {
        this.consensus.active_params = event.data
      }
      if (event.data.trading_allowed !== undefined) {
        this.dashboard.arbiter.permission = event.data.trading_allowed ? 'ALLOWED' : 'BLOCKED'
      }
      if (event.data.risk_per_trade_percent !== undefined) {
        this.dashboard.arbiter.current_risk_percent = event.data.risk_per_trade_percent
      }
      if (event.data.atr_sl_multiplier !== undefined) {
        this.dashboard.arbiter.sl_multiplier = event.data.atr_sl_multiplier
      }
    }
  },

  async refreshAll() {
    await Promise.all([
      this.hydrateCouncilState(),
      this.refreshConsensus(),
      this.refreshDialogueHistory(),
      this.refreshMemories(),
      this.refreshKnowledge(),
      this.refreshStandardizedStrategies(),
      this.refreshKnowledgeDocuments(),
    ])
  },
})

