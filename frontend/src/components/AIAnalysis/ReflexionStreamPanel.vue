<script setup>
import { computed, ref } from 'vue'
import {
  AlertCircle,
  ArrowRight,
  BookMarked,
  CheckCircle2,
  Filter,
  History,
  Lightbulb,
  RefreshCw,
  Search,
  Sparkles,
  TrendingDown,
  TrendingUp,
  XCircle,
} from 'lucide-vue-next'
import { agentStore } from '../../stores/agentStore'

const selectedCategory = ref('ALL')
const searchQuery = ref('')

const memories = computed(() => {
  if (agentStore.memorySearchResults.length > 0 && searchQuery.value.trim()) {
    return agentStore.memorySearchResults
  }
  const list = agentStore.memories || []
  if (selectedCategory.value === 'ALL') return list
  return list.filter((m) => m.mistake_category === selectedCategory.value)
})

const stats = computed(() => agentStore.reflexionStats || {
  total_memories: 0,
  outcomes: {},
  mistake_categories: {},
})

const winCount = computed(() => stats.value.outcomes?.WIN || 0)
const lossCount = computed(() => stats.value.outcomes?.LOSS || 0)

const availableCategories = computed(() => {
  const cats = Object.keys(stats.value.mistake_categories || {})
  return ['ALL', ...cats]
})

function formatPnl(val) {
  if (val === null || val === undefined) return '$0.00'
  const num = Number(val)
  const sign = num > 0 ? '+' : ''
  return `${sign}$${num.toFixed(2)}`
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

async function refresh() {
  await agentStore.refreshMemories()
}

async function onSearch() {
  if (!searchQuery.value.trim()) {
    agentStore.memorySearchResults = []
    return
  }
  await agentStore.searchMemories(searchQuery.value)
}

function clearSearch() {
  searchQuery.value = ''
  agentStore.memorySearchResults = []
}
</script>

<template>
  <section class="reflexion-panel">
    <!-- Header -->
    <header class="panel-header">
      <div class="header-title">
        <span class="reflexion-icon"><Sparkles :size="15" /></span>
        <div>
          <h2>AI Reflexion &amp; Lessons</h2>
          <small>Episodic Trade Memory &middot; Post-Mortem</small>
        </div>
      </div>
      <div class="header-right">
        <div class="stat-pill-group">
          <span class="stat-pill win" title="Số lệnh Thắng đã học">
            <TrendingUp :size="10" /> {{ winCount }}W
          </span>
          <span class="stat-pill loss" title="Số lệnh Thua đã kiểm điểm">
            <TrendingDown :size="10" /> {{ lossCount }}L
          </span>
        </div>
        <button
          class="action-btn"
          :disabled="agentStore.loadingMemories"
          title="Tải lại danh sách bài học"
          @click="refresh"
        >
          <RefreshCw :size="12" :class="{ spinning: agentStore.loadingMemories }" />
        </button>
      </div>
    </header>

    <div class="panel-body">
      <!-- Search Box -->
      <div class="search-wrap">
        <Search :size="12" class="search-icon" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Tra cứu bài học (VD: Stop Loss, tin tức, quét râu...)"
          @keyup.enter="onSearch"
        />
        <button v-if="searchQuery" class="clear-search" @click="clearSearch">&times;</button>
      </div>

      <!-- Category Filter Tabs -->
      <div v-if="availableCategories.length > 1" class="category-filter-strip">
        <button
          v-for="cat in availableCategories"
          :key="cat"
          class="cat-chip"
          :class="{ active: selectedCategory === cat }"
          @click="selectedCategory = cat"
        >
          {{ cat }}
          <span v-if="cat !== 'ALL' && stats.mistake_categories[cat]" class="cat-count">
            {{ stats.mistake_categories[cat] }}
          </span>
        </button>
      </div>

      <!-- Memories Stream List -->
      <div v-if="memories.length > 0" class="memory-stream">
        <article
          v-for="item in memories"
          :key="item.id || item.order_id"
          class="memory-card"
          :class="`outcome-${(item.outcome || 'BE').toLowerCase()}`"
        >
          <div class="card-top">
            <div class="ticket-group">
              <span class="ticket-badge">LỆNH #{{ item.order_id || item.id }}</span>
              <span
                class="outcome-badge"
                :class="`badge-${(item.outcome || 'BE').toLowerCase()}`"
              >
                {{ item.outcome }} ({{ formatPnl(item.realized_pnl) }})
              </span>
            </div>
            <span v-if="item.created_at" class="timestamp">{{ formatDate(item.created_at) }}</span>
          </div>

          <div v-if="item.mistake_category && item.mistake_category !== 'NONE'" class="mistake-row">
            <span class="mistake-tag">
              <AlertCircle :size="10" />
              {{ item.mistake_category }}
            </span>
          </div>

          <!-- Root cause & Lesson -->
          <div class="card-content">
            <div v-if="item.root_cause" class="content-row">
              <strong class="row-label">Nguyên nhân:</strong>
              <p class="row-text">{{ item.root_cause }}</p>
            </div>

            <div v-if="item.lesson_learned" class="content-row highlight">
              <strong class="row-label lesson">
                <Lightbulb :size="11" />
                Bài học rút ra:
              </strong>
              <p class="row-text">{{ item.lesson_learned }}</p>
            </div>

            <div v-if="item.rule_to_add" class="content-row rule-box">
              <strong class="row-label rule">
                <BookMarked :size="11" />
                Quy tắc đề xuất cho Governor:
              </strong>
              <p class="row-text rule-text">{{ item.rule_to_add }}</p>
            </div>
          </div>
        </article>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <div class="empty-icon-wrap">
          <History :size="20" />
        </div>
        <h4>Chưa có nhật ký kiểm điểm</h4>
        <p>
          Khi một lệnh (Win hoặc Loss) đóng, Reflexion Engine sẽ tự động đánh giá nguyên nhân gốc rễ và lưu bài học 1536-dim vào bộ nhớ ký ức.
        </p>
        <div class="mock-tip">
          <Lightbulb :size="12" />
          <span>Hệ thống tự động nới SL hoặc tạm dừng lệnh nếu phát hiện chuỗi sai lầm lặp lại.</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.reflexion-panel {
  overflow: hidden;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  background: #f8faf6;
  font-family: inherit;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.04);
}

.panel-header {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #e4e9e3;
  background: #ffffff;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reflexion-icon {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: #7c3aed;
  color: #ede9fe;
}

.header-title h2 {
  margin: 0;
  font-size: 11px;
  font-weight: 800;
  color: #1b2a23;
  letter-spacing: -0.01em;
}

.header-title small {
  display: block;
  font: 8px 'DM Mono', monospace;
  color: #718277;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-pill-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  border-radius: 4px;
  font: 9px 'DM Mono', monospace;
  font-weight: 800;
}

.stat-pill.win {
  background: #dcfce7;
  color: #15803d;
}

.stat-pill.loss {
  background: #fee2e2;
  color: #b91c1c;
}

.action-btn {
  height: 25px;
  width: 25px;
  display: grid;
  place-items: center;
  border: 1px solid #d0ded0;
  border-radius: 5px;
  background: #f2f6f1;
  color: #435449;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: #e1ebe0;
  color: #225c43;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.panel-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Search wrap */
.search-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 8px;
  color: #718277;
  pointer-events: none;
}

.search-wrap input {
  width: 100%;
  height: 28px;
  padding: 0 24px 0 26px;
  border: 1px solid #d0ded0;
  border-radius: 5px;
  background: #ffffff;
  color: #1b2a23;
  font-size: 10px;
}

.search-wrap input:focus {
  outline: none;
  border-color: #7c3aed;
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.15);
}

.clear-search {
  position: absolute;
  right: 6px;
  border: none;
  background: transparent;
  color: #718277;
  font-size: 14px;
  cursor: pointer;
}

/* Filter strip */
.category-filter-strip {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 4px;
  border: 1px solid #d5ded6;
  background: #ffffff;
  color: #55665b;
  font: 8px 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.cat-chip:hover {
  background: #f0f4ef;
}

.cat-chip.active {
  background: #7c3aed;
  color: #ffffff;
  border-color: #7c3aed;
}

.cat-count {
  background: rgba(0, 0, 0, 0.1);
  padding: 0 3px;
  border-radius: 3px;
  font-size: 7px;
}

/* Memory stream */
.memory-stream {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 380px;
  overflow-y: auto;
  padding-right: 2px;
}

.memory-card {
  background: #ffffff;
  border: 1px solid #dce4dc;
  border-radius: 6px;
  padding: 9px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.15s ease;
}

.memory-card:hover {
  border-color: #b8cfb8;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04);
}

.memory-card.outcome-loss {
  border-left: 3px solid #ef4444;
}

.memory-card.outcome-win {
  border-left: 3px solid #10b981;
}

.memory-card.outcome-be {
  border-left: 3px solid #6b7280;
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ticket-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ticket-badge {
  font: 9px 'DM Mono', monospace;
  font-weight: 800;
  color: #1b2a23;
}

.outcome-badge {
  font: 8px 'DM Mono', monospace;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 3px;
}

.badge-win {
  background: #dcfce7;
  color: #15803d;
}

.badge-loss {
  background: #fee2e2;
  color: #b91c1c;
}

.badge-be {
  background: #f3f4f6;
  color: #4b5563;
}

.timestamp {
  font: 8px 'DM Mono', monospace;
  color: #94a397;
}

.mistake-row {
  display: flex;
}

.mistake-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #fef2f2;
  border: 1px solid #fee2e2;
  color: #dc2626;
  font: 8px 'DM Mono', monospace;
  font-weight: 800;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 10px;
}

.content-row {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.content-row.highlight {
  background: #faf5ff;
  border-radius: 4px;
  padding: 5px 6px;
  border: 1px solid #f3e8ff;
}

.content-row.rule-box {
  background: #f0fdf4;
  border-radius: 4px;
  padding: 5px 6px;
  border: 1px solid #dcfce7;
}

.row-label {
  font-size: 8px;
  text-transform: uppercase;
  color: #6d7f73;
}

.row-label.lesson {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #7c3aed;
  font-weight: 800;
}

.row-label.rule {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #15803d;
  font-weight: 800;
}

.row-text {
  margin: 0;
  line-height: 1.35;
  color: #27372d;
}

.rule-text {
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  font-weight: 700;
  color: #166534;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 16px 12px;
  background: #ffffff;
  border-radius: 6px;
  border: 1px dashed #cedcce;
}

.empty-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f3f4f6;
  display: grid;
  place-items: center;
  color: #7c3aed;
  margin-bottom: 8px;
}

.empty-state h4 {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 800;
  color: #1b2a23;
}

.empty-state p {
  margin: 0 0 10px;
  font-size: 9px;
  color: #65756a;
  line-height: 1.4;
  max-width: 250px;
}

.mock-tip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 8px;
  background: #fdfaf3;
  border: 1px solid #fbeed4;
  border-radius: 4px;
  color: #8c5b05;
  font-size: 9px;
}
</style>
