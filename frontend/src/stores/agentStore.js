import { reactive } from 'vue'
import {
  evaluateGovernor as evaluateGovernorApi,
  fetchGovernorConsensus,
  fetchGovernorRuntimeParams,
  fetchKnowledgeStats,
  fetchReflexionMemories,
  fetchReflexionStats,
  overrideGovernor as overrideGovernorApi,
  reindexKnowledge as reindexKnowledgeApi,
  searchKnowledge as searchKnowledgeApi,
  searchReflexionMemories as searchReflexionMemoriesApi,
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

  // Reflexion State
  memories: [],
  reflexionStats: {
    total_memories: 0,
    outcomes: {},
    mistake_categories: {},
  },
  loadingMemories: false,
  memorySearchResults: [],
  searchingMemories: false,

  // RAG Knowledge State
  knowledgeStats: {
    total_chunks: 18,
    categories: {},
  },
  knowledgeSearchResults: [],
  searchingKnowledge: false,
  reindexing: false,

  // Actions
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

  async refreshMemories(limit = 20) {
    this.loadingMemories = true
    try {
      const [list, stats] = await Promise.all([
        fetchReflexionMemories(limit).catch(() => []),
        fetchReflexionStats().catch(() => ({ total_memories: 0, outcomes: {}, mistake_categories: {} })),
      ])
      this.memories = list || []
      this.reflexionStats = stats || { total_memories: 0, outcomes: {}, mistake_categories: {} }
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

  async refreshKnowledge() {
    try {
      const stats = await fetchKnowledgeStats()
      this.knowledgeStats = stats
    } catch {
      // Keep default
    }
  },

  async searchKnowledge(query, category = '') {
    if (!query?.trim()) {
      this.knowledgeSearchResults = []
      return
    }
    this.searchingKnowledge = true
    try {
      this.knowledgeSearchResults = await searchKnowledgeApi(query, category, 6)
    } finally {
      this.searchingKnowledge = false
    }
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
      this.refreshMemories(),
      this.refreshKnowledge(),
    ])
  },
})
