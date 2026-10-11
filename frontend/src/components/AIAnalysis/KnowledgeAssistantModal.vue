<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  BookOpen,
  CheckCircle2,
  Database,
  ExternalLink,
  Layers,
  PlusCircle,
  RefreshCw,
  Search,
  Sparkles,
  Tag,
  Wand2,
  Zap,
} from 'lucide-vue-next'
import { agentStore } from '../../stores/agentStore'

const props = defineProps({
  show: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const activeSubTab = ref('search') // 'search' | 'ingest'
const searchQuery = ref('')
const selectedCategory = ref('')
const selectedSchool = ref('')
const reindexMessage = ref('')

// Ingestion Form State
const ingestForm = ref({
  title: '',
  school_of_thought: 'WYCKOFF',
  category: 'ACCUMULATION_SCHEMATIC',
  sub_categories: '',
  tags: '',
  academic_reference: '',
  core_rule: '',
  content: '',
})
const classifying = ref(false)
const ingestSuccessMsg = ref('')
const ingestErrorMsg = ref('')

const quickQueries = [
  { label: 'Wyckoff Phase C Spring', query: 'Wyckoff Phase C Spring Volume Spread Absorption' },
  { label: 'ICT Judas Swing & OTE', query: 'ICT Judas Swing London Open OTE Fib 62%' },
  { label: 'CMT Intermarket Gold/DXY', query: 'CMT Dow Theory Intermarket Analysis XAUUSD USD Yield' },
  { label: 'Inducement & Trap Sweeps', query: 'Inducement IDM Engineered Liquidity Turtle Soup trap' },
  { label: 'SMC Order Block & FVG', query: 'Order block fair value gap discount equilibrium' },
  { label: 'Quy chế tin tức 3 sao USD', query: 'high impact macro events circuit breaker' },
]

const schoolOptions = [
  { value: 'WYCKOFF', label: '1. Wyckoff Method (Cội nguồn Smart Money)' },
  { value: 'ICT', label: '2. ICT Methodology (IPDA & Judas Swing)' },
  { value: 'CMT', label: '3. CMT Academic (Chuẩn mực Phân tích Quốc tế)' },
  { value: 'INDUCEMENT_TRAPS', label: '4. Inducement & Trap Trading' },
  { value: 'SMC', label: '5. Smart Money Concepts (BOS, CHoCH, OB)' },
  { value: 'PRICE_ACTION', label: '6. Pure Price Action' },
  { value: 'MACRO', label: '7. Macro Economics & News' },
  { value: 'POST_MORTEM', label: '8. Post-Mortem Lessons' },
]

const results = computed(() => agentStore.knowledgeSearchResults)
const stats = computed(() => agentStore.knowledgeStats || { total_chunks: 18, categories: {} })
const schools = computed(() => agentStore.knowledgeSchools || [])

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

async function handleAutoClassify() {
  const text = ingestForm.value.content || ingestForm.value.title
  if (!text.trim()) {
    ingestErrorMsg.value = 'Vui lòng nhập tiêu đề hoặc nội dung để AI tự động phân loại'
    return
  }
  classifying.value = true
  ingestErrorMsg.value = ''
  try {
    const res = await agentStore.classifyText(text)
    if (res) {
      ingestForm.value.school_of_thought = res.suggested_school
      ingestForm.value.category = res.suggested_category
      if (res.suggested_tags?.length) {
        ingestForm.value.tags = res.suggested_tags.join(', ')
      }
      ingestSuccessMsg.value = `AI đã phân loại: Trường phái ${res.suggested_school} &middot; Danh mục ${res.suggested_category} (Độ tin cậy: ${Math.round(res.confidence * 100)}%)`
      setTimeout(() => { ingestSuccessMsg.value = '' }, 4000)
    }
  } catch (err) {
    ingestErrorMsg.value = err.message || 'Lỗi khi tự động phân loại tri thức'
  } finally {
    classifying.value = false
  }
}

async function handleSubmitIngestion() {
  if (!ingestForm.value.title.trim() || !ingestForm.value.content.trim()) {
    ingestErrorMsg.value = 'Tiêu đề và nội dung tri thức không được để trống'
    return
  }
  ingestErrorMsg.value = ''
  ingestSuccessMsg.value = ''
  try {
    const payload = {
      title: ingestForm.value.title.trim(),
      school_of_thought: ingestForm.value.school_of_thought,
      category: ingestForm.value.category,
      sub_categories: ingestForm.value.sub_categories ? ingestForm.value.sub_categories.split(',').map((s) => s.trim()) : [],
      tags: ingestForm.value.tags ? ingestForm.value.tags.split(',').map((s) => s.trim()) : [],
      academic_reference: ingestForm.value.academic_reference.trim() || null,
      core_rule: ingestForm.value.core_rule.trim() || null,
      content: ingestForm.value.content.trim(),
      source_type: 'TRADER_PROVIDED',
    }
    const res = await agentStore.submitKnowledgeDoc(payload)
    ingestSuccessMsg.value = `Nạp tri thức thành công! ID #${res.knowledge_id} đã được lưu trữ và vector hóa 1536 chiều.`
    ingestForm.value = {
      title: '',
      school_of_thought: 'WYCKOFF',
      category: 'ACCUMULATION_SCHEMATIC',
      sub_categories: '',
      tags: '',
      academic_reference: '',
      core_rule: '',
      content: '',
    }
  } catch (err) {
    ingestErrorMsg.value = err.message || 'Lỗi khi nạp tài liệu tri thức'
  }
}
</script>

<template>
  <div v-if="show" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal-dialog">
      <!-- Modal Header -->
      <header class="modal-header">
        <div class="header-left">
          <span class="rag-badge"><Database :size="16" /></span>
          <div>
            <h3>Multi-School Strategic RAG Academy</h3>
            <small>pgvector (1536-dim) &middot; Wyckoff &middot; ICT &middot; CMT &middot; Inducement/Traps &middot; SMC</small>
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

      <!-- Navigation Sub-Tabs -->
      <div class="modal-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeSubTab === 'search' }"
          @click="activeSubTab = 'search'"
        >
          <Search :size="13" />
          <span>Tra Cứu Tri Thức Ngữ Nghĩa (Semantic Search)</span>
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeSubTab === 'ingest' }"
          @click="activeSubTab = 'ingest'"
        >
          <PlusCircle :size="13" />
          <span>Nạp Tri Thức Đa Trường Phái (Ingestion Pipeline)</span>
        </button>
      </div>

      <!-- TAB 1: SEARCH & EXPLORE -->
      <template v-if="activeSubTab === 'search'">
        <!-- Search & Filters Bar -->
        <div class="modal-search-bar">
          <div class="input-wrap">
            <Search :size="14" class="search-icon" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Tìm kiếm tri thức (VD: Wyckoff Spring, Judas Swing, CMT Dow, Quét IDM, Order Block...)"
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

          <!-- School and Category Pills -->
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
            <span class="quick-label">Gợi ý đa trường phái:</span>
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
                  <span v-if="item.school_of_thought" class="school-tag" :class="`school-${item.school_of_thought.toLowerCase()}`">
                    {{ item.school_of_thought }}
                  </span>
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
                <span v-if="item.metadata.academic_reference" class="academic-tag">
                  📚 {{ item.metadata.academic_reference }}
                </span>
                <span v-if="item.metadata.core_rule" class="core-rule-tag">
                  💡 Quy tắc cốt lõi: {{ item.metadata.core_rule }}
                </span>
                <span v-if="item.metadata.tags?.length" class="tags-tag">
                  🏷️ {{ item.metadata.tags.join(', ') }}
                </span>
              </footer>
            </article>
          </div>

          <!-- Default or Empty State -->
          <div v-else class="empty-docs-guide">
            <div class="guide-header">
              <BookOpen :size="24" class="guide-icon" />
              <h4>Viện Hàn Lâm Tri Thức Đa Trường Phái Cho Vàng (XAUUSD)</h4>
              <p>
                Hệ thống tích hợp toàn diện 5 bộ khung: <b>Wyckoff Method</b> (Spring / Accumulation), 
                <b>ICT Methodology</b> (IPDA, Judas Swing, OTE), <b>CMT Academic</b> (Dow Theory, Intermarket Analysis), 
                <b>Inducement/Traps</b> (Quét thanh khoản IDM) và <b>Smart Money Concepts</b> (OB, FVG).
              </p>
            </div>
            <div class="playbook-grid">
              <div class="playbook-item" @click="selectQuickQuery('Wyckoff Phase C Spring Volume Spread Absorption')">
                <strong>1. Wyckoff Method</strong>
                <small>Phase A-E, Spring, UTAD, VSA Effort vs Result</small>
              </div>
              <div class="playbook-item" @click="selectQuickQuery('ICT Judas Swing London Open OTE Fib 62%')">
                <strong>2. ICT Methodology</strong>
                <small>Power of 3 (AMD), Judas Swing, OTE 62-79%</small>
              </div>
              <div class="playbook-item" @click="selectQuickQuery('CMT Dow Theory Intermarket Analysis XAUUSD')">
                <strong>3. CMT Academic Framework</strong>
                <small>Dow Trend, Support Polarity, Vàng vs DXY</small>
              </div>
              <div class="playbook-item" @click="selectQuickQuery('Inducement IDM Engineered Liquidity Turtle Soup')">
                <strong>4. Inducement &amp; Traps</strong>
                <small>IDM, Bẫy thanh khoản, Turtle Soup Sweep</small>
              </div>
              <div class="playbook-item" @click="selectQuickQuery('Smart money concepts trading rules')">
                <strong>5. Smart Money Concepts</strong>
                <small>Order Block, FVG, Discount / Premium 50%</small>
              </div>
              <div class="playbook-item" @click="selectQuickQuery('Macro risk news circuit breaker CPI FOMC')">
                <strong>6. Macro Risk &amp; Reflexion</strong>
                <small>Tin tức 3 sao USD, Circuit Breaker &amp; Post-Mortem</small>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- TAB 2: INGESTION PIPELINE -->
      <template v-else>
        <div class="ingest-form-container">
          <div class="ingest-instructions">
            <p>
              Trader có thể chủ động nạp thêm tài liệu, ghi chú hoặc quy tắc giao dịch cá nhân.
              Hệ thống sẽ <b>tự động phân loại</b> (Auto-Classifier) trường phái học thuật, gắn thẻ ngữ nghĩa,
              và nhúng vector 1536 chiều vào CSDL PostgreSQL để Technical RAG Agent tham chiếu khi phân tích biểu đồ.
            </p>
          </div>

          <form class="ingest-form" @submit.prevent="handleSubmitIngestion">
            <div class="form-row">
              <div class="form-group flex-2">
                <label>Tiêu đề tri thức chiến lược *</label>
                <input
                  v-model="ingestForm.title"
                  type="text"
                  placeholder="VD: Wyckoff Phase C Spring & Quét Khối Lượng Hấp Thụ"
                  required
                />
              </div>

              <div class="form-group flex-1">
                <label>Trường phái học thuật *</label>
                <select v-model="ingestForm.school_of_thought">
                  <option v-for="sch in schoolOptions" :key="sch.value" :value="sch.value">
                    {{ sch.label }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group flex-1">
                <label>Danh mục (Category)</label>
                <input
                  v-model="ingestForm.category"
                  type="text"
                  placeholder="VD: ACCUMULATION_SCHEMATIC, POWER_OF_3..."
                />
              </div>

              <div class="form-group flex-1">
                <label>Thẻ gắn (Tags, cách nhau dấu phẩy)</label>
                <input
                  v-model="ingestForm.tags"
                  type="text"
                  placeholder="VD: VSA, SPRING, COMPOSITE_MAN..."
                />
              </div>

              <div class="form-group flex-1">
                <label>Tài liệu học thuật tham chiếu</label>
                <input
                  v-model="ingestForm.academic_reference"
                  type="text"
                  placeholder="VD: Richard D. Wyckoff (1931), CMT Level II..."
                />
              </div>
            </div>

            <div class="form-group">
              <label>Quy tắc cốt lõi (Core Rule tóm tắt)</label>
              <input
                v-model="ingestForm.core_rule"
                type="text"
                placeholder="VD: Spring Phase C kèm khối lượng lớn là điểm mua tối ưu nhất của chu kỳ tích lũy."
              />
            </div>

            <div class="form-group">
              <div class="label-with-action">
                <label>Nội dung chi tiết (Định dạng Markdown) *</label>
                <button
                  type="button"
                  class="auto-classify-btn"
                  :disabled="classifying"
                  @click="handleAutoClassify"
                >
                  <Wand2 :size="12" />
                  <span>{{ classifying ? 'Đang phân tích...' : 'AI Auto-Classify (Phân loại tự động)' }}</span>
                </button>
              </div>
              <textarea
                v-model="ingestForm.content"
                rows="6"
                placeholder="Nhập nội dung quy tắc kỹ thuật, điều kiện setup, tiêu chuẩn vào lệnh..."
                required
              ></textarea>
            </div>

            <div v-if="ingestSuccessMsg" class="form-alert alert-success">
              <CheckCircle2 :size="14" />
              <span>{{ ingestSuccessMsg }}</span>
            </div>

            <div v-if="ingestErrorMsg" class="form-alert alert-error">
              <span>{{ ingestErrorMsg }}</span>
            </div>

            <div class="form-actions">
              <button
                type="submit"
                class="submit-ingest-btn"
                :disabled="agentStore.submittingKnowledge"
              >
                <PlusCircle :size="14" />
                <span>{{ agentStore.submittingKnowledge ? 'Đang nạp...' : 'Nạp Tri Thức Vào Vector Database' }}</span>
              </button>
            </div>
          </form>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-dialog {
  background: #0d121c;
  border: 1px solid #1f2c3f;
  border-radius: 12px;
  width: 100%;
  max-width: 960px;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: #131b28;
  border-bottom: 1px solid #1f2c3f;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rag-badge {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0284c7, #0369a1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.modal-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #f1f5f9;
}

.modal-header small {
  color: #64748b;
  font-size: 11px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.reindex-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.reindex-btn:hover:not(:disabled) {
  color: #f1f5f9;
  border-color: #0284c7;
}

.close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 22px;
  cursor: pointer;
  line-height: 1;
}

.modal-tabs {
  display: flex;
  background: #0f1622;
  border-bottom: 1px solid #1f2c3f;
  padding: 0 16px;
}

.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 10px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #cbd5e1;
}

.tab-btn.active {
  color: #38bdf8;
  border-bottom-color: #38bdf8;
}

.modal-search-bar {
  padding: 14px 20px;
  background: #111827;
  border-bottom: 1px solid #1f2c3f;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #64748b;
}

.input-wrap input {
  width: 100%;
  padding: 9px 120px 9px 36px;
  background: #0a0d14;
  border: 1px solid #253347;
  border-radius: 6px;
  color: #f1f5f9;
  font-size: 13px;
  outline: none;
}

.input-wrap input:focus {
  border-color: #38bdf8;
}

.submit-search {
  position: absolute;
  right: 5px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  background: #0284c7;
  border: none;
  border-radius: 5px;
  color: white;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.category-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.cat-btn {
  padding: 3px 8px;
  background: #1a2332;
  border: 1px solid #28374d;
  color: #94a3b8;
  border-radius: 12px;
  font-size: 11px;
  cursor: pointer;
}

.cat-btn.active {
  background: #0369a1;
  color: white;
  border-color: #38bdf8;
}

.quick-queries {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.quick-label {
  font-size: 11px;
  color: #64748b;
}

.qq-btn {
  padding: 3px 8px;
  background: #0e1520;
  border: 1px dashed #29384e;
  border-radius: 4px;
  color: #cbd5e1;
  font-size: 10.5px;
  cursor: pointer;
}

.qq-btn:hover {
  border-color: #38bdf8;
  color: #38bdf8;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  background: #090c13;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
  color: #64748b;
  font-size: 13px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  background: #101724;
  border: 1px solid #1f2c3f;
  border-radius: 8px;
  padding: 12px 14px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.school-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.cat-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(56, 189, 248, 0.12);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.25);
}

.result-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #f1f5f9;
}

.similarity-score {
  font-size: 11px;
  color: #94a3b8;
}

.similarity-score b {
  color: #10b981;
}

.result-content pre {
  margin: 0;
  font-size: 12px;
  color: #cbd5e1;
  white-space: pre-wrap;
  font-family: inherit;
  line-height: 1.5;
}

.result-footer {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid #192435;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 11px;
  color: #64748b;
}

.empty-docs-guide {
  text-align: center;
  padding: 20px 0;
}

.guide-icon {
  margin: 0 auto 8px;
  color: #38bdf8;
}

.guide-header h4 {
  margin: 0 0 6px;
  font-size: 15px;
  color: #f1f5f9;
}

.guide-header p {
  color: #64748b;
  font-size: 12px;
  max-width: 600px;
  margin: 0 auto 16px;
  line-height: 1.5;
}

.playbook-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
  text-align: left;
}

.playbook-item {
  background: #111827;
  border: 1px solid #1f2c3f;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.playbook-item:hover {
  background: #172236;
  border-color: #38bdf8;
}

.playbook-item strong {
  font-size: 12px;
  color: #f1f5f9;
}

.playbook-item small {
  font-size: 11px;
  color: #64748b;
}

/* Ingest Form Styles */
.ingest-form-container {
  padding: 18px 24px;
  background: #090c13;
  overflow-y: auto;
}

.ingest-instructions {
  background: #101726;
  border: 1px solid #1e2c40;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 16px;
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
}

.ingest-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.flex-1 {
  flex: 1;
}

.flex-2 {
  flex: 2;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 11px;
  font-weight: 600;
  color: #cbd5e1;
}

.label-with-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.auto-classify-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  background: #2e1065;
  border: 1px solid #7c3aed;
  border-radius: 4px;
  color: #c084fc;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}

.auto-classify-btn:hover:not(:disabled) {
  background: #4c1d95;
}

.form-group input,
.form-group select,
.form-group textarea {
  background: #0d131f;
  border: 1px solid #1f2c3f;
  border-radius: 6px;
  padding: 8px 12px;
  color: #f1f5f9;
  font-size: 12px;
  outline: none;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: #38bdf8;
}

.form-alert {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-success {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid #10b981;
  color: #10b981;
}

.alert-error {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid #ef4444;
  color: #ef4444;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.submit-ingest-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: #0284c7;
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.submit-ingest-btn:hover:not(:disabled) {
  background: #0369a1;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}
</style>
