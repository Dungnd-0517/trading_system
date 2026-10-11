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
} from '../services/api'

export const agentStore = reactive({
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

  // RAG Knowledge State (Multi-School)
  knowledgeStats: {
    total_chunks: 18,
    categories: {},
  },
  knowledgeSchools: [],
  knowledgeSearchResults: [],
  searchingKnowledge: false,
  reindexing: false,
  submittingKnowledge: false,

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
      await this.refreshKnowledge()
      return res
    } finally {
      this.reindexing = false
    }
  },

  applyGovernorUpdate(event) {
    if (event.data) {
      this.runtimeParams = event.data
      if (this.consensus) {
        this.consensus.active_params = event.data
      }
    }
  },

  async refreshAll() {
    await Promise.all([
      this.refreshConsensus(),
      this.refreshDialogueHistory(),
      this.refreshMemories(),
      this.refreshKnowledge(),
    ])
  },
})
