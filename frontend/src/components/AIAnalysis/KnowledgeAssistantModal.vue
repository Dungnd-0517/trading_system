<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  BookOpen,
  Database,
  ExternalLink,
  Layers,
  RefreshCw,
  Search,
  Sparkles,
  Tag,
  Zap,
} from 'lucide-vue-next'
import { agentStore } from '../../stores/agentStore'

const props = defineProps({
  show: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const searchQuery = ref('')
const selectedCategory = ref('')
const reindexMessage = ref('')

const quickQueries = [
  { label: 'Liquidity Sweep & Turtle Soup', query: 'liquidity sweep turtle soup' },
  { label: 'BOS vs CHoCH cấu trúc', query: 'BOS CHoCH market structure' },
  { label: 'Quy chế tin tức 3 sao USD', query: 'high impact macro events circuit breaker' },
  { label: 'Xử lý lỗi SL Too Tight', query: 'SL_TOO_TIGHT ATR multiplier' },
  { label: 'Order Block & FVG Discount', query: 'Order block fair value gap discount' },
]

const results = computed(() => agentStore.knowledgeSearchResults)
const stats = computed(() => agentStore.knowledgeStats || { total_chunks: 18, categories: {} })

onMounted(() => {
  agentStore.refreshKnowledge()
})

async function onSearch() {
  if (!searchQuery.value.trim()) return
  await agentStore.searchKnowledge(searchQuery.value, selectedCategory.value)
}

function selectQuickQuery(q) {
  searchQuery.value = q
  onSearch()
}

async function triggerReindex() {
  reindexMessage.value = ''
  try {
    const res = await agentStore.triggerReindex()
    reindexMessage.value = `Đã nạp thành công ${res.chunks_ingested || 18} chunks tri thức!`
    setTimeout(() => { reindexMessage.value = '' }, 3000)
  } catch (err) {
    reindexMessage.value = 'Lỗi khi tái lập chỉ mục tri thức'
  }
}
</script>

<template>
  <div v-if="show" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-dialog">
      <!-- Modal Header -->
      <header class="modal-header">
        <div class="header-left">
          <span class="rag-badge"><Database :size="15" /></span>
          <div>
            <h3>RAG Knowledge Assistant</h3>
            <small>Vector Database (1536-dim) &middot; SMC / Wyckoff / Macro Risk</small>
          </div>
        </div>
        <div class="header-right">
          <button
            class="reindex-btn"
            :disabled="agentStore.reindexing"
            title="Đọc lại toàn bộ tài liệu và nạp lại Vector DB"
            @click="triggerReindex"
          >
            <RefreshCw :size="11" :class="{ spinning: agentStore.reindexing }" />
            <span>Re-index ({{ stats.total_chunks || 18 }} chunks)</span>
          </button>
          <button class="close-btn" @click="emit('close')">&times;</button>
        </div>
      </header>

      <!-- Search & Filters Bar -->
      <div class="modal-search-bar">
        <div class="input-wrap">
          <Search :size="14" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Tìm kiếm ngữ nghĩa tri thức (VD: Order Block, Pin Bar, CPI, Quét thanh khoản...)"
            @keyup.enter="onSearch"
          />
          <button
            class="submit-search"
            :disabled="agentStore.searchingKnowledge"
            @click="onSearch"
          >
            <Sparkles :size="12" />
            <span>Tìm kiếm</span>
          </button>
        </div>

        <div class="category-pills">
          <button
            class="cat-btn"
            :class="{ active: selectedCategory === '' }"
            @click="selectedCategory = ''; onSearch()"
          >
            Tất cả ({{ stats.total_chunks || 18 }})
          </button>
          <button
            v-for="(count, cat) in stats.categories"
            :key="cat"
            class="cat-btn"
            :class="{ active: selectedCategory === cat }"
            @click="selectedCategory = cat; onSearch()"
          >
            {{ cat }} ({{ count }})
          </button>
        </div>

        <!-- Quick Query Presets -->
        <div class="quick-queries">
          <span class="quick-label">Gợi ý nhanh:</span>
          <button
            v-for="qq in quickQueries"
            :key="qq.label"
            class="qq-btn"
            @click="selectQuickQuery(qq.query)"
          >
            {{ qq.label }}
          </button>
        </div>

        <div v-if="reindexMessage" class="reindex-alert">
          {{ reindexMessage }}
        </div>
      </div>

      <!-- Results Body -->
      <div class="modal-body">
        <div v-if="agentStore.searchingKnowledge" class="loading-state">
          <RefreshCw :size="20" class="spinning" />
          <span>Đang truy vấn không gian Vector 1536 chiều qua Cosine Similarity...</span>
        </div>

        <div v-else-if="results.length > 0" class="results-list">
          <article v-for="item in results" :key="item.id" class="result-card">
            <header class="result-header">
              <div class="result-meta">
                <span class="cat-tag" :class="`cat-${item.category?.toLowerCase()}`">
                  {{ item.category }}
                </span>
                <h4 class="result-title">{{ item.title }}</h4>
              </div>
              <span class="similarity-score" :title="`Khoảng cách Cosine: ${item.distance}`">
                Độ tương đồng: <b>{{ Math.round((item.similarity || 0) * 100) }}%</b>
              </span>
            </header>
            <div class="result-content">
              <pre>{{ item.content }}</pre>
            </div>
            <footer v-if="item.metadata" class="result-footer">
              <span class="source-tag">Nguồn: {{ item.metadata.source_file }}</span>
              <span v-if="item.metadata.section" class="section-tag">&middot; {{ item.metadata.section }}</span>
            </footer>
          </article>
        </div>

        <!-- Default or Empty State -->
        <div v-else class="empty-docs-guide">
          <div class="guide-header">
            <BookOpen :size="24" class="guide-icon" />
            <h4>Cơ Sở Dữ Liệu Tri Thức Chuẩn Hóa</h4>
            <p>
              Tài liệu được phân tích cú pháp thành 18 Knowledge Chunks và nạp vào PostgreSQL với extension <code>pgvector</code>.
              AI Agents (Technical RAG, Governor, Reflexion) truy xuất tài liệu này để ra quyết định và kẹp tham số.
            </p>
          </div>
          <div class="playbook-grid">
            <div class="playbook-item" @click="selectQuickQuery('Smart money concepts trading rules')">
              <strong>SMC Trading Rules</strong>
              <small>6 chunks &middot; Dealing Range, Equilibrium, OB, FVG, BOS/CHoCH</small>
            </div>
            <div class="playbook-item" @click="selectQuickQuery('Price action candlestick patterns wyckoff')">
              <strong>Price Action &amp; Wyckoff</strong>
              <small>3 chunks &middot; Pin Bar, Engulfing, Accumulation Phase C</small>
            </div>
            <div class="playbook-item" @click="selectQuickQuery('Macro risk news circuit breaker CPI FOMC')">
              <strong>Macro Risk Playbook</strong>
              <small>3 chunks &middot; Tin đỏ 3 sao, Cooldown 30m, Volatility Dilator</small>
            </div>
            <div class="playbook-item" @click="selectQuickQuery('Post mortem mistake taxonomy rules')">
              <strong>Post-Mortem Playbook</strong>
              <small>6 chunks &middot; SL_TOO_TIGHT, EARLY_ENTRY, FOMO, NEWS_SPIKE</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 20, 0.65);
  backdrop-filter: blur(3px);
  display: grid;
  place-items: center;
  z-index: 9999;
  padding: 20px;
}

.modal-dialog {
  width: 100%;
  max-width: 760px;
  max-height: 85vh;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #ccdccb;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: #f4f8f3;
  border-bottom: 1px solid #e1e9df;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rag-badge {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: #0284c7;
  color: #ffffff;
}

.header-left h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 800;
  color: #1b2a23;
}

.header-left small {
  display: block;
  font: 9px 'DM Mono', monospace;
  color: #65776d;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reindex-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border: 1px solid #c9d9c8;
  border-radius: 5px;
  background: #ffffff;
  color: #3e5246;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
}

.reindex-btn:hover {
  background: #e2ede0;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  color: #6d7f73;
  cursor: pointer;
  line-height: 1;
}

.close-btn:hover {
  color: #1b2a23;
}

/* Search bar */
.modal-search-bar {
  padding: 12px 16px;
  background: #f9fbf8;
  border-bottom: 1px solid #e5ebe4;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: #718277;
  pointer-events: none;
}

.input-wrap input {
  flex: 1;
  height: 34px;
  padding: 0 12px 0 32px;
  border: 1px solid #c8d7c7;
  border-radius: 6px;
  font-size: 12px;
  background: #ffffff;
}

.input-wrap input:focus {
  outline: none;
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.submit-search {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 34px;
  padding: 0 14px;
  border: none;
  border-radius: 6px;
  background: #0284c7;
  color: #ffffff;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.submit-search:hover {
  background: #0369a1;
}

.category-pills {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.cat-btn {
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #d5ded6;
  background: #ffffff;
  color: #55665b;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
}

.cat-btn.active {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}

.quick-queries {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  font-size: 10px;
}

.quick-label {
  color: #78897e;
  font-size: 9px;
  font-weight: 600;
}

.qq-btn {
  padding: 1px 6px;
  border-radius: 3px;
  background: #edf3ec;
  border: 1px solid #d4e0d3;
  color: #3b4e42;
  font-size: 9px;
  cursor: pointer;
}

.qq-btn:hover {
  background: #225c43;
  color: #ffffff;
}

.reindex-alert {
  padding: 5px 8px;
  background: #dcfce7;
  color: #15803d;
  font-size: 10px;
  border-radius: 4px;
}

/* Modal body */
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #ffffff;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #0284c7;
  gap: 12px;
  font-size: 11px;
  font-weight: 600;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  border: 1px solid #dce4dc;
  border-radius: 8px;
  padding: 12px;
  background: #fafcfa;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.cat-tag {
  font: 8px 'DM Mono', monospace;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}

.cat-smc { background: #e0f2fe; color: #0369a1; }
.cat-price_action { background: #fef3c7; color: #92400e; }
.cat-macro { background: #fee2e2; color: #b91c1c; }
.cat-post_mortem { background: #ede9fe; color: #6d28d9; }

.result-title {
  margin: 0;
  font-size: 12px;
  font-weight: 800;
  color: #1b2a23;
}

.similarity-score {
  font: 9px 'DM Mono', monospace;
  color: #059669;
  background: #ecfdf5;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.result-content pre {
  margin: 0;
  font-family: inherit;
  font-size: 11px;
  line-height: 1.5;
  color: #27372d;
  white-space: pre-wrap;
  background: #ffffff;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #e5ebe4;
}

.result-footer {
  font: 9px 'DM Mono', monospace;
  color: #7a8b80;
}

/* Empty guide */
.empty-docs-guide {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 12px 0;
}

.guide-header {
  text-align: center;
  max-width: 520px;
  margin: 0 auto;
}

.guide-icon {
  color: #0284c7;
  margin-bottom: 6px;
}

.guide-header h4 {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 800;
  color: #1b2a23;
}

.guide-header p {
  margin: 0;
  font-size: 11px;
  color: #617367;
  line-height: 1.45;
}

.guide-header code {
  background: #edf2eb;
  padding: 1px 4px;
  border-radius: 3px;
  font-family: 'DM Mono', monospace;
}

.playbook-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.playbook-item {
  border: 1px solid #dbe3db;
  border-radius: 8px;
  padding: 12px;
  background: #f8faf6;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.playbook-item:hover {
  border-color: #0284c7;
  background: #f0f9ff;
  transform: translateY(-1px);
}

.playbook-item strong {
  font-size: 11px;
  color: #1b2a23;
}

.playbook-item small {
  font-size: 9px;
  color: #65776d;
}
</style>
