<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  ExternalLink,
  FileCode,
  FileText,
  Layers,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from 'lucide-vue-next'
import { agentStore } from '../../stores/agentStore'

// State for Ingestion Hub
const ingestionMode = ref('file') // 'file' | 'url' | 'editor'
const selectedSchool = ref('')
const customDocTitle = ref('')

// File upload state
const fileInput = ref(null)
const selectedFile = ref(null)
const dragActive = ref(false)

// URL link state
const documentUrl = ref('')

// Direct Markdown Editor state
const editorContent = ref('')

// Filter for Standardized Strategies Library
const activeSchoolFilter = ref('ALL')

// Detail Modal / Drawer state
const showDetailModal = ref(false)
const modalTab = ref('formatted') // 'formatted' | 'json' | 'markdown'
const viewingStrategy = ref(null)
const copySuccess = ref(false)

// Sample templates for direct editor
const sampleTemplates = [
  {
    name: 'Wyckoff Spring',
    school: 'WYCKOFF',
    title: 'Wyckoff Phase C Spring Accumulation & VSA',
    content: `# Chiến lược Wyckoff Phase C Spring Accumulation

## 1. Cơ Chế Tích Lũy & Thanh Khoản
Mô hình tích lũy Pha C của Richard Wyckoff: Sau khi hình thành Trading Range (Pha A & B), giá tạo cú nhúng giả Spring xuyên thủng đáy hỗ trợ Preliminary Support để quét thanh khoản của các lệnh Stop Loss. Smart Money hấp thụ toàn bộ khối lượng bán tháo với hiện tượng nỗ lực không tương xứng kết quả (VSA Effort vs Result).

## 2. Checklist & Điều Kiện Vào Lệnh
- Xác định Trading Range có Phase A (Selling Climax & Automatic Rally) và Phase B rõ ràng.
- Cú Spring quét thủng biên dưới với khối lượng bán cạn kiệt.
- Nến kiểm tra (Test of Spring) giữ vững trên đáy cũ và hồi phục dứt khoát.
- Nến Sign of Strength (SOS) vượt ngưỡng kháng cự Creek kèm khối lượng tăng mạnh.

## 3. Điểm Vào Lệnh (Entry), Cắt Lỗ (SL) & Chốt Lời (TP)
- **Entry:** Vào lệnh BUY tại nhịp hồi kiểm tra LPS (Last Point of Support) sau nến SOS.
- **Stop Loss:** Đặt SL cách đáy Spring thấp nhất 1.5x ATR M15.
- **Take Profit:** TP1 tại 1:2.0R (chốt 50% khối lượng, dời SL về Entry); TP2 tại đỉnh biên trên Range (1:3.0R - 1:4.0R).
`,
  },
  {
    name: 'SMC Liquidity Sweep',
    school: 'SMC',
    title: 'SMC Liquidity Sweeps & FVG Mitigation',
    content: `# Chiến lược SMC Liquidity Sweeps & FVG Mitigation

## 1. Triết Lý Dòng Tiền Tổ Chức (Smart Money Concepts)
Thị trường di chuyển để tìm kiếm thanh khoản. Giá quét sạch thanh khoản Buyside hoặc Sellside Liquidity Pool tại các vùng đỉnh/đáy bằng nhau (EQH/EQL), sau đó dịch chuyển mạnh mẽ (Displacement) để tạo ra vùng mất cân bằng Fair Value Gap (FVG).

## 2. Quy Trình Phân Tích Đa Khung Thời Gian
- **HTF D1/H4:** Xác định thiên hướng xu hướng chính (Bullish / Bearish Bias).
- **ITF H1:** Xác định vùng POI (Order Block hoặc FVG) nằm tại vùng Discount (< 50% Dealing Range).
- **LTF M15:** Chờ giá nhúng vào POI H1 và xuất hiện Change of Character (CHoCH) kèm nến đóng cửa vượt qua đỉnh gần nhất.

## 3. Quản Trị Vị Thế
- Mở lệnh khi giá hồi quy về FVG nội phiên M15.
- Cắt lỗ ngoài biên POI 1.5x ATR.
- Tỷ lệ R:R mục tiêu ≥ 1:2.0.
`,
  },
  {
    name: 'ICT Silver Bullet',
    school: 'ICT',
    title: 'ICT Silver Bullet London Kill Zone',
    content: `# Chiến lược ICT Silver Bullet Kill Zone

## 1. Thuật Toán Phân Phối Giá IPDA
Mô hình Silver Bullet khai thác chu kỳ Power of 3 (AMD) trong các khung giờ thanh khoản cao (London Kill Zone 14:00-17:00 ICT hoặc New York AM 19:00-22:00 ICT). Cú Judas Swing quét thanh khoản phiên Á trước khi dịch chuyển theo xu hướng thực.

## 2. Tiêu Chí Vào Lệnh
- Nằm trong khung giờ Kill Zone chuẩn xác.
- Giá quét sạch đỉnh/đáy phiên Á.
- Xuất hiện sóng Displacement tạo khoảng trống giá FVG hợp lệ (biên độ ≥ 0.3x ATR).
- Giá thoái lui chạm mốc Consequent Encroachment (50% FVG) hoặc vùng OTE Fib 62-79%.

## 3. Quản Trị Rủi Ro
- Rủi ro tối đa 0.5% - 1.0% tài khoản.
- TP1 tại 1:2.0R và dời SL hòa vốn; TP2 tại cản đối diện.
`,
  },
]

function applyTemplate(tpl) {
  selectedSchool.value = tpl.school
  customDocTitle.value = tpl.title
  editorContent.value = tpl.content
}

// File Drag & Drop Handlers
function onFileChange(e) {
  const files = e.target.files
  if (files && files[0]) {
    selectedFile.value = files[0]
    if (!customDocTitle.value) {
      customDocTitle.value = files[0].name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ')
    }
  }
}

function onFileDrop(e) {
  dragActive.value = false
  const files = e.dataTransfer.files
  if (files && files[0]) {
    selectedFile.value = files[0]
    if (!customDocTitle.value) {
      customDocTitle.value = files[0].name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ')
    }
  }
}

// Ingestion Triggers
async function handleIngest() {
  if (ingestionMode.value === 'file') {
    if (!selectedFile.value) return
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    if (selectedSchool.value) formData.append('school_of_thought', selectedSchool.value)
    if (customDocTitle.value) formData.append('custom_title', customDocTitle.value)
    await agentStore.uploadFile(formData)
    selectedFile.value = null
    if (fileInput.value) fileInput.value.value = ''
  } else if (ingestionMode.value === 'url') {
    if (!documentUrl.value.trim()) return
    await agentStore.ingestUrl({
      url: documentUrl.value.trim(),
      custom_title: customDocTitle.value.trim() || null,
      school_of_thought: selectedSchool.value || null,
    })
    documentUrl.value = ''
  } else if (ingestionMode.value === 'editor') {
    if (!editorContent.value.trim()) return
    await agentStore.ingestMarkdown({
      title: customDocTitle.value.trim() || 'Tài liệu Chiến lược Mới',
      content: editorContent.value.trim(),
      school_of_thought: selectedSchool.value || null,
    })
  }
}

// Standardized Strategies Filtered List
const filteredStrategies = computed(() => {
  if (!agentStore.standardizedStrategies) return []
  if (activeSchoolFilter.value === 'ALL') return agentStore.standardizedStrategies
  return agentStore.standardizedStrategies.filter(
    (s) => s.school_of_thought === activeSchoolFilter.value
  )
})

const uniqueSchools = computed(() => {
  const schools = new Set(['ALL'])
  agentStore.standardizedStrategies?.forEach((s) => {
    if (s.school_of_thought) schools.add(s.school_of_thought)
  })
  return Array.from(schools)
})

// Modal Open Handler
async function openStrategyDetail(strategy) {
  viewingStrategy.value = strategy
  modalTab.value = 'formatted'
  showDetailModal.value = true
  // Tải thêm raw JSON và Markdown nếu chưa có
  const fullDetail = await agentStore.loadStrategyDetail(strategy.slug)
  if (fullDetail) {
    viewingStrategy.value = fullDetail
  }
}

function copyCurrentContent() {
  let text = ''
  if (modalTab.value === 'json') {
    text = JSON.stringify(viewingStrategy.value?.json_content || viewingStrategy.value, null, 2)
  } else if (modalTab.value === 'markdown') {
    text = viewingStrategy.value?.markdown_content || ''
  } else {
    text = viewingStrategy.value?.name + '\n\n' + viewingStrategy.value?.philosophy
  }
  navigator.clipboard.writeText(text)
  copySuccess.value = true
  setTimeout(() => {
    copySuccess.value = false
  }, 2000)
}

function downloadStrategyFile(format) {
  if (!viewingStrategy.value) return
  let content = ''
  let filename = ''
  let type = ''
  if (format === 'json') {
    content = JSON.stringify(viewingStrategy.value?.json_content || viewingStrategy.value, null, 2)
    filename = `${viewingStrategy.value.slug}.json`
    type = 'application/json'
  } else {
    content = viewingStrategy.value?.markdown_content || ''
    filename = `${viewingStrategy.value.slug}.md`
    type = 'text/markdown'
  }
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await Promise.all([
    agentStore.refreshStandardizedStrategies(),
    agentStore.refreshKnowledgeDocuments(),
    agentStore.refreshKnowledge(),
  ])
  // Nếu chưa có chiến lược chuẩn hóa nào, tự động seed 5 mẫu nền tảng
  if (agentStore.standardizedStrategies.length === 0) {
    await agentStore.seedBaselineStrategies()
  }
})
</script>

<template>
  <section id="vector-knowledge-section" class="vector-knowledge-container">
    <!-- ========================================================= -->
    <!-- SECTION HERO HEADER WITH AGENT [VECTOR] PERSONA BADGE    -->
    <!-- ========================================================= -->
    <div class="vector-hero-header">
      <div class="agent-persona-chip">
        <span class="persona-avatar">📐</span>
        <div class="persona-text">
          <div class="persona-title-row">
            <span class="persona-codename">AGENT [VECTOR]</span>
            <span class="persona-tag">TECHNICAL RAG SPECIALIST</span>
            <span class="persona-status-dot"></span>
          </div>
          <span class="persona-sub">Viện Trưởng Viện Kỹ Thuật Đa Trường Phái &amp; Động Cơ Tri Thức Vector 1536 Chiều</span>
        </div>
      </div>

      <div class="hero-center-content">
        <h2 class="section-main-title">
          Hệ Thống Cập Nhật &amp; Lưu Trữ Tri Thức Giao Dịch Chuẩn Hóa
        </h2>
        <p class="section-main-desc">
          Tiếp nhận tài liệu <strong>PDF, Markdown, Link Web</strong> &middot; Agent [VECTOR] tự động đọc, phân loại trường phái và vector hóa vào PostgreSQL pgvector &middot; 
          Sau mỗi nguồn tri thức, hệ thống tự động sinh <strong>Cấu Trúc Giao Dịch Tiêu Chuẩn (Standardized Trading Framework)</strong> và lưu trữ thành file hệ thống (JSON &amp; Markdown) nhằm cải thiện hiệu suất giao dịch.
        </p>
      </div>

      <!-- Quick Metrics Counters -->
      <div class="vector-stats-strip">
        <div class="vstat-box">
          <small>CHUNKS TRI THỨC</small>
          <strong>{{ agentStore.knowledgeStats?.total_chunks || 18 }}</strong>
          <span>1536-dim vectors</span>
        </div>
        <div class="vstat-box">
          <small>CHIẾN LƯỢC CHUẨN</small>
          <strong class="text-gold">{{ agentStore.standardizedStrategies?.length || 0 }}</strong>
          <span>File JSON &amp; MD</span>
        </div>
        <div class="vstat-box">
          <small>NGUỒN TÀI LIỆU</small>
          <strong class="text-cyan">{{ agentStore.knowledgeDocuments?.length || 4 }}</strong>
          <span>PDF &middot; MD &middot; URL</span>
        </div>
        <div class="vstat-box">
          <small>TRƯỜNG PHÁI</small>
          <strong>5+</strong>
          <span>Wyckoff, SMC, ICT...</span>
        </div>
      </div>
    </div>

    <!-- ========================================================= -->
    <!-- INTERACTIVE KNOWLEDGE INGESTION CENTER                    -->
    <!-- ========================================================= -->
    <div class="ingestion-center-card">
      <div class="card-head-bar">
        <div class="head-left">
          <UploadCloud :size="18" class="text-gold" />
          <h3>Cửa Ngõ Nạp Dữ Liệu &amp; Huấn Luyện Tri Thức Mới</h3>
        </div>
        
        <!-- Mode Switcher Tabs -->
        <div class="mode-switcher" role="tablist">
          <button
            :class="['mode-btn', { active: ingestionMode === 'file' }]"
            @click="ingestionMode = 'file'"
          >
            <FileText :size="14" />
            <span>1. Upload File PDF / Markdown</span>
          </button>
          <button
            :class="['mode-btn', { active: ingestionMode === 'url' }]"
            @click="ingestionMode = 'url'"
          >
            <ExternalLink :size="14" />
            <span>2. Link Tài Liệu / Web URL</span>
          </button>
          <button
            :class="['mode-btn', { active: ingestionMode === 'editor' }]"
            @click="ingestionMode = 'editor'"
          >
            <Layers :size="14" />
            <span>3. Soạn Thảo Trực Tiếp</span>
          </button>
        </div>
      </div>

      <!-- Common Metadata Configuration Bar -->
      <div class="ingest-meta-row">
        <div class="meta-field">
          <label>Trường Phái Kỹ Thuật (School of Thought)</label>
          <select v-model="selectedSchool">
            <option value="">✨ Tự Động Nhận Diện Bởi Agent [VECTOR]</option>
            <option value="WYCKOFF">Wyckoff Method (VSA &amp; Schematics)</option>
            <option value="SMC">Smart Money Concepts (OB, BOS, CHoCH)</option>
            <option value="ICT">ICT / IPDA (Silver Bullet, Kill Zones)</option>
            <option value="CMT">CMT Academic (Polarity, Dow Theory, DXY)</option>
            <option value="PRICE_ACTION">Price Action (Wick Rejection, Engulfing)</option>
            <option value="RISK_MANAGEMENT">Risk Management &amp; Capital Guardrails</option>
          </select>
        </div>

        <div class="meta-field flex-2">
          <label>Tiêu Đề Phương Pháp / Tài Liệu (Tùy Chọn)</label>
          <input
            v-model="customDocTitle"
            type="text"
            placeholder="VD: Mô hình Wyckoff Spring M15 hoặc SMC Liquidity Sweeps..."
          />
        </div>
      </div>

      <!-- MODE 1: FILE UPLOAD -->
      <div v-if="ingestionMode === 'file'" class="mode-body">
        <div
          :class="['dropzone-container', { dragover: dragActive, 'has-file': !!selectedFile }]"
          @dragover.prevent="dragActive = true"
          @dragleave.prevent="dragActive = false"
          @drop.prevent="onFileDrop"
          @click="$refs.fileInput.click()"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".pdf,.md,.markdown,.txt"
            class="hidden-file-input"
            @change="onFileChange"
          />

          <div v-if="!selectedFile" class="dropzone-empty">
            <div class="drop-icon-glow">
              <UploadCloud :size="32" />
            </div>
            <h4>Kéo &amp; Thả File PDF hoặc Markdown vào đây, hoặc bấm để chọn file</h4>
            <p>Hỗ trợ định dạng tài liệu nghiên cứu: <strong>.pdf</strong>, <strong>.md</strong>, <strong>.txt</strong> (Tối đa 30MB)</p>
          </div>

          <div v-else class="dropzone-selected" @click.stop>
            <div class="file-badge">
              <FileText :size="24" class="text-gold" />
            </div>
            <div class="file-details">
              <strong>{{ selectedFile.name }}</strong>
              <small>{{ (selectedFile.size / 1024).toFixed(1) }} KB &middot; Sẵn sàng phân tích</small>
            </div>
            <button class="remove-file-btn" @click.stop="selectedFile = null">Thay đổi file</button>
          </div>
        </div>
      </div>

      <!-- MODE 2: URL INGESTION -->
      <div v-else-if="ingestionMode === 'url'" class="mode-body">
        <div class="url-input-container">
          <label>Nhập Đường Dẫn URL Bài Báo, Khảo Cứu Hoặc Tài Liệu Online</label>
          <div class="url-input-box">
            <ExternalLink :size="16" class="url-icon" />
            <input
              v-model="documentUrl"
              type="url"
              placeholder="https://example.com/trading-strategy-wyckoff-spring.html"
              @keyup.enter="handleIngest"
            />
          </div>
          <small class="field-hint">
            Agent [VECTOR] sẽ tự động tải trang, loại bỏ mã rác (HTML, Script, CSS), trích xuất văn bản cốt lõi và nạp vào pgvector.
          </small>
        </div>
      </div>

      <!-- MODE 3: DIRECT MARKDOWN EDITOR -->
      <div v-else class="mode-body">
        <div class="template-quick-strip">
          <span class="tpl-label">Mẫu chiến lược tham khảo nhanh:</span>
          <button
            v-for="tpl in sampleTemplates"
            :key="tpl.name"
            class="tpl-pill-btn"
            @click="applyTemplate(tpl)"
          >
            <Sparkles :size="12" />
            <span>{{ tpl.name }}</span>
          </button>
        </div>

        <div class="markdown-editor-box">
          <textarea
            v-model="editorContent"
            rows="10"
            placeholder="Nhập hoặc dán nội dung Markdown của chiến lược kỹ thuật vào đây..."
          ></textarea>
        </div>
      </div>

      <!-- Ingestion Action Bar -->
      <div class="ingest-action-bar">
        <div class="action-info">
          <ShieldCheck :size="15" class="text-green" />
          <span>Agent [VECTOR] sẽ tự động tổng hợp File Hệ Thống (JSON &amp; MD) &amp; Cập nhật CSDL.</span>
        </div>

        <button
          class="submit-ingest-btn"
          :disabled="agentStore.ingestingKnowledge || (ingestionMode === 'file' && !selectedFile) || (ingestionMode === 'url' && !documentUrl.trim()) || (ingestionMode === 'editor' && !editorContent.trim())"
          @click="handleIngest"
        >
          <RefreshCw v-if="agentStore.ingestingKnowledge" :size="16" class="spin" />
          <Sparkles v-else :size="16" />
          <span>{{ agentStore.ingestingKnowledge ? 'Agent [VECTOR] Đang Phân Tích & Chuẩn Hóa...' : 'Tiến Hành Phân Tích & Nạp Tri Thức' }}</span>
        </button>
      </div>

      <!-- INGESTION RESULT BANNER -->
      <div v-if="agentStore.ingestionResult" class="ingest-result-banner">
        <div class="result-header">
          <div class="res-tag">
            <CheckCircle2 :size="16" class="text-green" />
            <strong>Đã Hoàn Tất Phân Loại &amp; Chuẩn Hóa Tri Thức Thành Công!</strong>
          </div>
          <span class="res-score">Độ tin cậy: {{ Math.round((agentStore.ingestionResult.confidence || 0.95) * 100) }}%</span>
        </div>

        <div class="result-body-grid">
          <div class="res-item">
            <small>TRƯỜNG PHÁI PHÁT HIỆN</small>
            <span class="badge-school">{{ agentStore.ingestionResult.detected_school }}</span>
          </div>
          <div class="res-item">
            <small>SỐ CHUNKS VECTOR</small>
            <strong>+{{ agentStore.ingestionResult.chunks_created }} chunks (1536-dim)</strong>
          </div>
          <div class="res-item flex-2">
            <small>CẤU TRÚC TIÊU CHUẨN ĐÃ SINH</small>
            <strong class="text-gold">{{ agentStore.ingestionResult.standardized_strategy?.name }}</strong>
          </div>
        </div>

        <div class="result-footer-actions">
          <span class="reasoning-text">💡 <em>{{ agentStore.ingestionResult.reasoning }}</em></span>
          <button
            class="view-strat-btn"
            @click="openStrategyDetail(agentStore.ingestionResult.standardized_strategy)"
          >
            <span>Xem Cấu Trúc Tiêu Chuẩn Này</span>
            <ExternalLink :size="13" />
          </button>
        </div>
      </div>

      <!-- Ingestion Error Alert -->
      <div v-if="agentStore.ingestionError" class="ingest-error-banner">
        <AlertCircle :size="16" />
        <span>{{ agentStore.ingestionError }}</span>
      </div>
    </div>

    <!-- ========================================================= -->
    <!-- KHO CẤU TRÚC GIAO DỊCH TIÊU CHUẨN (STANDARDIZED STRATEGIES) -->
    <!-- ========================================================= -->
    <div class="standardized-strategies-hub">
      <div class="hub-header-row">
        <div>
          <div class="hub-title-strip">
            <Layers :size="18" class="text-gold" />
            <h3>Kho Cấu Trúc Giao Dịch Tiêu Chuẩn (Standardized Trading Frameworks)</h3>
          </div>
          <p class="hub-subtitle">
            Mỗi phương pháp kỹ thuật sau khi nạp được tự động mô hình hóa thành một cấu trúc giao dịch tiêu chuẩn khép kín: Checklist điều kiện, Vùng kích hoạt, ATR Stop Loss, R:R tối thiểu và Rào chắn bảo vệ vốn.
          </p>
        </div>

        <!-- School Filter Pills -->
        <div class="school-filter-strip">
          <button
            v-for="sc in uniqueSchools"
            :key="sc"
            :class="['filter-pill', { active: activeSchoolFilter === sc }]"
            @click="activeSchoolFilter = sc"
          >
            {{ sc }}
          </button>
        </div>
      </div>

      <!-- Strategy Cards Grid -->
      <div class="strategies-grid">
        <article
          v-for="strat in filteredStrategies"
          :key="strat.slug"
          class="strategy-card"
        >
          <div class="card-top-row">
            <span :class="['school-badge', strat.school_of_thought.toLowerCase()]">
              {{ strat.school_of_thought }}
            </span>
            <span class="rr-target-badge">
              R:R &ge; 1:{{ (strat.target_risk_reward || 2.0).toFixed(1) }}
            </span>
          </div>

          <h4 class="strat-title">{{ strat.name }}</h4>
          <p class="strat-philosophy">{{ strat.philosophy }}</p>

          <div class="strat-meta-specs">
            <div class="spec-row">
              <span class="spec-lbl">Khung Thời Gian:</span>
              <strong class="spec-val">{{ strat.timeframe_focus }}</strong>
            </div>
            <div class="spec-row">
              <span class="spec-lbl">Quy Tắc Vào Lệnh:</span>
              <span class="spec-val-trunc">{{ strat.entry_rules }}</span>
            </div>
            <div class="spec-row">
              <span class="spec-lbl">Cắt Lỗ (SL):</span>
              <span class="spec-val-trunc text-red">{{ strat.stop_loss_rules }}</span>
            </div>
          </div>

          <div class="system-file-pill">
            <FileCode :size="12" class="text-cyan" />
            <span>Lưu file: <code>{{ strat.slug }}.json</code> &amp; <code>.md</code></span>
          </div>

          <div class="card-btn-strip">
            <button class="action-card-btn primary" @click="openStrategyDetail(strat)">
              <BookOpen :size="13" />
              <span>Xem Chi Tiết &amp; Checklist</span>
            </button>
            <button class="action-card-btn secondary" @click="openStrategyDetail(strat); modalTab = 'json'">
              <FileCode :size="13" />
              <span>JSON</span>
            </button>
            <button class="action-card-btn secondary" @click="openStrategyDetail(strat); modalTab = 'markdown'">
              <FileText :size="13" />
              <span>Markdown</span>
            </button>
          </div>
        </article>
      </div>
    </div>

    <!-- ========================================================= -->
    <!-- KNOWLEDGE BASE DOCUMENTS & VECTOR CHUNKS EXPLORER         -->
    <!-- ========================================================= -->
    <div class="documents-explorer-card">
      <div class="doc-exp-head">
        <div class="doc-exp-title">
          <BookOpen :size="16" class="text-cyan" />
          <h4>Danh Mục Tài Liệu &amp; Tri Thức Đã Vector Hóa (pgvector 1536-dim)</h4>
        </div>
        <button
          class="reindex-btn"
          :disabled="agentStore.reindexing"
          @click="agentStore.triggerReindex()"
        >
          <RefreshCw :size="13" :class="{ spin: agentStore.reindexing }" />
          <span>{{ agentStore.reindexing ? 'Đang Tái Tạo Chỉ Mục...' : 'Tái Tạo Chỉ Mục Vector (Reindex)' }}</span>
        </button>
      </div>

      <div class="docs-table-wrapper">
        <table class="docs-table">
          <thead>
            <tr>
              <th>Nguồn Tài Liệu / File</th>
              <th>Trường Phái</th>
              <th>Danh Mục Cấp 2</th>
              <th>Định Dạng</th>
              <th>Số Chunks</th>
              <th>Thời Gian Cập Nhật</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(doc, idx) in agentStore.knowledgeDocuments" :key="idx">
              <td>
                <div class="doc-name-cell">
                  <FileText :size="14" class="text-gold" />
                  <span class="doc-filename">{{ doc.source_file }}</span>
                </div>
              </td>
              <td>
                <span :class="['mini-school-badge', (doc.school_of_thought || '').toLowerCase()]">
                  {{ doc.school_of_thought }}
                </span>
              </td>
              <td><code>{{ doc.category }}</code></td>
              <td><span class="type-pill">{{ doc.source_type }}</span></td>
              <td><strong>{{ doc.chunk_count }} chunks</strong></td>
              <td><small class="text-dim">{{ doc.last_updated ? new Date(doc.last_updated).toLocaleString('vi-VN') : 'Mặc định' }}</small></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ========================================================= -->
    <!-- MODAL / DRAWER: CHI TIẾT CẤU TRÚC GIAO DỊCH TIÊU CHUẨN     -->
    <!-- ========================================================= -->
    <div v-if="showDetailModal && viewingStrategy" class="modal-backdrop" @click="showDetailModal = false">
      <div class="strategy-modal-card" @click.stop>
        <header class="modal-header">
          <div class="modal-title-box">
            <span :class="['school-badge', viewingStrategy.school_of_thought.toLowerCase()]">
              {{ viewingStrategy.school_of_thought }}
            </span>
            <h3>{{ viewingStrategy.name }}</h3>
          </div>
          <button class="modal-close-btn" @click="showDetailModal = false">&times;</button>
        </header>

        <!-- Modal View Tabs -->
        <div class="modal-tabs-strip">
          <button
            :class="['mtab-btn', { active: modalTab === 'formatted' }]"
            @click="modalTab = 'formatted'"
          >
            <Layers :size="14" />
            <span>1. Quy Trình &amp; Checklist</span>
          </button>
          <button
            :class="['mtab-btn', { active: modalTab === 'json' }]"
            @click="modalTab = 'json'"
          >
            <FileCode :size="14" />
            <span>2. File JSON Hệ Thống</span>
          </button>
          <button
            :class="['mtab-btn', { active: modalTab === 'markdown' }]"
            @click="modalTab = 'markdown'"
          >
            <FileText :size="14" />
            <span>3. File Markdown Hệ Thống</span>
          </button>

          <div class="modal-toolbar-actions">
            <button class="tool-btn" @click="copyCurrentContent">
              <CheckCircle2 v-if="copySuccess" :size="13" class="text-green" />
              <Copy v-else :size="13" />
              <span>{{ copySuccess ? 'Đã Sao Chép!' : 'Sao Chép' }}</span>
            </button>
            <button class="tool-btn" @click="downloadStrategyFile(modalTab === 'json' ? 'json' : 'markdown')">
              <Download :size="13" />
              <span>Tải File</span>
            </button>
          </div>
        </div>

        <!-- TAB CONTENT 1: FORMATTED STRATEGY -->
        <div v-if="modalTab === 'formatted'" class="modal-tab-content">
          <div class="spec-section">
            <h4>1. Triết Lý &amp; Nguyên Lý Dòng Tiền Tổ Chức</h4>
            <p class="section-p">{{ viewingStrategy.philosophy }}</p>
          </div>

          <div class="spec-section">
            <h4>2. Checklist Điều Kiện Tiên Quyết (Standardized Setup Checklist)</h4>
            <div class="checklist-interactive-box">
              <div
                v-for="(item, idx) in viewingStrategy.setup_checklist"
                :key="idx"
                class="modal-check-item"
              >
                <CheckCircle2 :size="16" class="text-gold" />
                <span><strong>Bước {{ idx + 1 }}:</strong> {{ item.label }}</span>
              </div>
            </div>
          </div>

          <div class="spec-grid-2">
            <div class="spec-box">
              <h4>3. Vùng &amp; Tín Hiệu Vào Lệnh (Entry)</h4>
              <p>{{ viewingStrategy.entry_rules }}</p>
            </div>
            <div class="spec-box">
              <h4>4. Cắt Lỗ (Stop Loss)</h4>
              <p class="text-red">{{ viewingStrategy.stop_loss_rules }}</p>
            </div>
            <div class="spec-box">
              <h4>5. Chốt Lời (Take Profit)</h4>
              <p class="text-green">{{ viewingStrategy.take_profit_rules }}</p>
            </div>
            <div class="spec-box">
              <h4>6. Điều Kiện Hủy Bỏ (Invalidation)</h4>
              <p>{{ viewingStrategy.invalidation_conditions }}</p>
            </div>
          </div>

          <div class="spec-section">
            <h4>7. Rào Chắn Quản Trị Rủi Ro Cứng (Hard Guardrails)</h4>
            <div class="guardrails-mini-strip">
              <div class="g-mini-item">
                <small>RỦI RO / LỆNH</small>
                <strong>{{ viewingStrategy.risk_guardrails?.min_risk_per_trade_pct || 0.25 }}% - {{ viewingStrategy.risk_guardrails?.max_risk_per_trade_pct || 1.0 }}%</strong>
              </div>
              <div class="g-mini-item">
                <small>MỤC TIÊU R:R</small>
                <strong class="text-green">&ge; 1:{{ (viewingStrategy.target_risk_reward || 2.0).toFixed(1) }}</strong>
              </div>
              <div class="g-mini-item">
                <small>CIRCUIT BREAKER</small>
                <strong class="text-gold">{{ viewingStrategy.risk_guardrails?.circuit_breaker_buffer_mins || 30 }} Phút</strong>
              </div>
              <div class="g-mini-item">
                <small>MAX DAILY DRAWDOWN</small>
                <strong class="text-red">{{ viewingStrategy.risk_guardrails?.max_daily_drawdown_limit_pct || 3.0 }}%</strong>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB CONTENT 2: RAW JSON CODE VIEWER -->
        <div v-else-if="modalTab === 'json'" class="modal-tab-content">
          <pre class="code-viewer">{{ JSON.stringify(viewingStrategy.json_content || viewingStrategy, null, 2) }}</pre>
        </div>

        <!-- TAB CONTENT 3: RAW MARKDOWN VIEWER -->
        <div v-else class="modal-tab-content">
          <pre class="code-viewer">{{ viewingStrategy.markdown_content || '# Đang cập nhật Markdown...' }}</pre>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* ==================================================== */
/* VECTOR KNOWLEDGE CONTAINER                           */
/* ==================================================== */
.vector-knowledge-container {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--line, #d9e0d9);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ==================================================== */
/* HERO HEADER WITH AGENT [VECTOR] PERSONA BADGE        */
/* ==================================================== */
.vector-hero-header {
  background: var(--paper, #f8faf6);
  border: 1px solid #d5ded6;
  border-radius: 8px;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.04);
}

.agent-persona-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: #eaf1e9;
  border: 1px solid #c8d9c5;
  border-radius: 20px;
  padding: 4px 14px 4px 6px;
  width: fit-content;
}

.persona-avatar {
  font-size: 1.1rem;
  background: #225c43;
  color: #c9f06b;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.persona-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.persona-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.persona-codename {
  font-weight: 800;
  color: #225c43;
  font-size: 0.8rem;
  letter-spacing: 0.03em;
}

.persona-tag {
  background: #d8e5d6;
  color: #276949;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
}

.persona-status-dot {
  width: 6px;
  height: 6px;
  background: #54a267;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(84, 162, 103, 0.5);
  animation: pulse-green 2s infinite;
}

.persona-sub {
  font-size: 0.72rem;
  color: #637569;
}

.section-main-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 800;
  color: #1b2a23;
  letter-spacing: -0.01em;
}

.section-main-desc {
  margin: 6px 0 0;
  color: #55675c;
  font-size: 0.84rem;
  line-height: 1.55;
  max-width: 1000px;
}

.section-main-desc strong {
  color: #1b2a23;
}

.vector-stats-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid #e1e8df;
}

.vstat-box {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.vstat-box small {
  font-size: 0.65rem;
  color: #77847c;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.vstat-box strong {
  font-size: 1.2rem;
  font-weight: 800;
  color: #1b2a23;
}

.vstat-box span {
  font-size: 0.7rem;
  color: #77847c;
}

/* ==================================================== */
/* INGESTION CENTER CARD                                */
/* ==================================================== */
.ingestion-center-card {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 8px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-head-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e8ede7;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.head-left h3 {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 800;
  color: #1b2a23;
}

.mode-switcher {
  display: flex;
  gap: 5px;
  background: #edf1ec;
  padding: 3px;
  border-radius: 6px;
}

.mode-btn {
  background: transparent;
  border: none;
  color: #58695f;
  padding: 5px 11px;
  border-radius: 5px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}

.mode-btn:hover {
  color: #225c43;
  background: #e1e9e0;
}

.mode-btn.active {
  background: #225c43;
  color: #c9f06b;
  box-shadow: 0 1px 3px rgba(34, 92, 67, 0.2);
}

.ingest-meta-row {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.meta-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 240px;
}

.meta-field.flex-2 {
  flex: 2;
  min-width: 300px;
}

.meta-field label {
  font-size: 0.72rem;
  font-weight: 700;
  color: #4a5c50;
  letter-spacing: 0.02em;
}

.meta-field select,
.meta-field input {
  background: #f8faf6;
  border: 1px solid #cfd9ce;
  color: #1b2a23;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.82rem;
  outline: none;
  transition: border-color 0.2s;
}

.meta-field select:focus,
.meta-field input:focus {
  border-color: #225c43;
  background: #ffffff;
}

/* DROPZONE */
.dropzone-container {
  border: 2px dashed #cfd9ce;
  background: #fbfdfa;
  border-radius: 8px;
  padding: 30px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dropzone-container:hover,
.dropzone-container.dragover {
  border-color: #225c43;
  background: #f0f6ee;
}

.dropzone-container.has-file {
  border-color: #c68133;
  background: #fef9ee;
  padding: 16px;
}

.hidden-file-input {
  display: none;
}

.drop-icon-glow {
  color: #225c43;
  margin-bottom: 8px;
}

.dropzone-empty h4 {
  margin: 0 0 4px;
  font-size: 0.92rem;
  font-weight: 700;
  color: #1b2a23;
}

.dropzone-empty p {
  margin: 0;
  font-size: 0.76rem;
  color: #77847c;
}

.dropzone-selected {
  display: flex;
  align-items: center;
  gap: 12px;
  text-align: left;
}

.file-details {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.file-details strong {
  font-size: 0.85rem;
  color: #1b2a23;
}

.file-details small {
  font-size: 0.72rem;
  color: #77847c;
}

.remove-file-btn {
  background: #e9efe7;
  border: 1px solid #cfd9ce;
  color: #3b4e41;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 0.72rem;
  cursor: pointer;
}

/* URL INPUT */
.url-input-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.url-input-container label {
  font-size: 0.75rem;
  font-weight: 700;
  color: #4a5c50;
}

.url-input-box {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f8faf6;
  border: 1px solid #cfd9ce;
  border-radius: 6px;
  padding: 9px 12px;
}

.url-icon {
  color: #225c43;
}

.url-input-box input {
  background: transparent;
  border: none;
  outline: none;
  color: #1b2a23;
  font-size: 0.84rem;
  width: 100%;
}

.field-hint {
  font-size: 0.72rem;
  color: #77847c;
}

/* MARKDOWN EDITOR */
.template-quick-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.tpl-label {
  font-size: 0.72rem;
  color: #77847c;
  font-weight: 600;
}

.tpl-pill-btn {
  background: #eef3ec;
  border: 1px solid #d4ded3;
  color: #3f5546;
  padding: 3px 9px;
  border-radius: 5px;
  font-size: 0.72rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: all 0.15s ease;
}

.tpl-pill-btn:hover {
  background: #fef5e6;
  color: #9c6014;
  border-color: #e4c28f;
}

.markdown-editor-box textarea {
  width: 100%;
  background: #f8faf6;
  border: 1px solid #cfd9ce;
  border-radius: 6px;
  color: #1b2a23;
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.8rem;
  padding: 10px;
  outline: none;
  resize: vertical;
}

.markdown-editor-box textarea:focus {
  border-color: #225c43;
  background: #ffffff;
}

/* ACTION BAR */
.ingest-action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #e8ede7;
}

.action-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  color: #637569;
}

.submit-ingest-btn {
  background: #225c43;
  border: 1px solid #174230;
  color: #c9f06b;
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.15s ease;
}

.submit-ingest-btn:hover:not(:disabled) {
  background: #174230;
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(34, 92, 67, 0.25);
}

.submit-ingest-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* RESULT BANNER */
.ingest-result-banner {
  background: #eef8ec;
  border: 1px solid #b3d9ad;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.res-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #225c43;
  font-size: 0.85rem;
  font-weight: 700;
}

.res-score {
  font-size: 0.72rem;
  font-weight: 700;
  background: #d5ecd0;
  color: #174230;
  padding: 2px 7px;
  border-radius: 4px;
}

.result-body-grid {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.res-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.res-item.flex-2 {
  flex: 2;
}

.res-item small {
  font-size: 0.65rem;
  color: #77847c;
  font-weight: 700;
}

.result-footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid #d5ecd0;
}

.reasoning-text {
  font-size: 0.76rem;
  color: #4a5c50;
}

.view-strat-btn {
  background: #fdf5ea;
  border: 1px solid #ecc68a;
  color: #9c6014;
  padding: 4px 10px;
  border-radius: 5px;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ingest-error-banner {
  background: #fcf1ef;
  border: 1px solid #f2b9b1;
  color: #c65345;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ==================================================== */
/* STANDARDIZED STRATEGIES HUB                          */
/* ==================================================== */
.standardized-strategies-hub {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hub-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
}

.hub-title-strip {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hub-title-strip h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: #1b2a23;
}

.hub-subtitle {
  margin: 4px 0 0;
  font-size: 0.82rem;
  color: #637569;
  max-width: 800px;
}

.school-filter-strip {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.filter-pill {
  background: #eef3ec;
  border: 1px solid #d4ded3;
  color: #58695f;
  padding: 4px 11px;
  border-radius: 16px;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-pill:hover {
  color: #225c43;
  border-color: #bad3bc;
}

.filter-pill.active {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}

/* STRATEGIES GRID */
.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.strategy-card {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.03);
  transition: transform 0.15s, border-color 0.15s;
}

.strategy-card:hover {
  transform: translateY(-2px);
  border-color: #9fc9a4;
  box-shadow: 0 4px 12px rgba(34, 92, 67, 0.08);
}

.card-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.school-badge {
  font-size: 0.68rem;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.03em;
}

.school-badge.wyckoff { background: #f3eef8; color: #723b9c; border: 1px solid #d9c7ea; }
.school-badge.smc { background: #eaf1e9; color: #225c43; border: 1px solid #c8d9c5; }
.school-badge.ict { background: #e6f3f8; color: #156d94; border: 1px solid #badfe9; }
.school-badge.cmt { background: #fef5e6; color: #9c6014; border: 1px solid #edd4ad; }
.school-badge.price_action { background: #ebf5ee; color: #2b7044; border: 1px solid #c2e2cc; }

.rr-target-badge {
  font-size: 0.72rem;
  font-weight: 800;
  color: #225c43;
  background: #e3ede1;
  padding: 2px 7px;
  border-radius: 4px;
}

.strat-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 800;
  color: #1b2a23;
  line-height: 1.35;
}

.strat-philosophy {
  margin: 0;
  font-size: 0.75rem;
  color: #55675c;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.strat-meta-specs {
  background: #f8faf6;
  border: 1px solid #e5ebe4;
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.spec-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.72rem;
}

.spec-lbl {
  color: #77847c;
  font-weight: 600;
  white-space: nowrap;
}

.spec-val {
  color: #1b2a23;
  font-weight: 700;
}

.spec-val-trunc {
  color: #3b4e41;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

.system-file-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.68rem;
  color: #637569;
  min-width: 0;
  overflow: hidden;
}

.system-file-pill span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.system-file-pill code {
  color: #225c43;
  background: #e8efe7;
  padding: 1px 4px;
  border-radius: 3px;
  word-break: break-all;
}

.card-btn-strip {
  display: flex;
  gap: 6px;
  margin-top: auto;
  padding-top: 6px;
}

.action-card-btn {
  border: 1px solid transparent;
  border-radius: 5px;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 6px 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  transition: all 0.15s;
}

.action-card-btn.primary {
  background: #225c43;
  border-color: #174230;
  color: #c9f06b;
  flex: 1;
}

.action-card-btn.primary:hover {
  background: #174230;
  color: #ffffff;
}

.action-card-btn.secondary {
  background: #f0f4ef;
  border-color: #d6e0d5;
  color: #4a5c50;
}

.action-card-btn.secondary:hover {
  background: #e2ebe0;
  color: #1b2a23;
}

/* ==================================================== */
/* DOCUMENTS & CHUNKS EXPLORER                          */
/* ==================================================== */
.documents-explorer-card {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 8px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.doc-exp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

.doc-exp-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-exp-title h4 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 800;
  color: #1b2a23;
}

.reindex-btn {
  background: #eef3ec;
  border: 1px solid #d4ded3;
  color: #4a5c50;
  padding: 5px 11px;
  border-radius: 5px;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.docs-table-wrapper {
  overflow-x: auto;
}

.docs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}

.docs-table th {
  text-align: left;
  padding: 8px 12px;
  color: #77847c;
  font-weight: 700;
  border-bottom: 1px solid #dce4da;
  background: #f8faf6;
}

.docs-table td {
  padding: 9px 12px;
  color: #3b4e41;
  border-bottom: 1px solid #edf1ec;
}

.doc-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-filename {
  font-weight: 700;
  color: #1b2a23;
}

.mini-school-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  background: #eaf1e9;
  color: #225c43;
}

.type-pill {
  background: #edf1ec;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.65rem;
  color: #77847c;
}

/* ==================================================== */
/* MODAL / DRAWER                                       */
/* ==================================================== */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(27, 42, 35, 0.6);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.strategy-modal-card {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 10px;
  width: 100%;
  max-width: 900px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 16px 40px rgba(27, 42, 35, 0.2);
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5ebe4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8faf6;
}

.modal-title-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-title-box h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: #1b2a23;
}

.modal-close-btn {
  background: transparent;
  border: none;
  color: #77847c;
  font-size: 1.6rem;
  cursor: pointer;
  line-height: 1;
}

.modal-close-btn:hover {
  color: #1b2a23;
}

.modal-tabs-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: #edf1ec;
  border-bottom: 1px solid #dce4da;
}

.mtab-btn {
  background: transparent;
  border: none;
  color: #58695f;
  padding: 5px 12px;
  border-radius: 5px;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}

.mtab-btn.active {
  background: #ffffff;
  color: #225c43;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.1);
}

.modal-toolbar-actions {
  margin-left: auto;
  display: flex;
  gap: 6px;
}

.tool-btn {
  background: #ffffff;
  border: 1px solid #d4ded3;
  color: #4a5c50;
  padding: 4px 9px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}

.tool-btn:hover {
  background: #eaf1e9;
  color: #1b2a23;
}

.modal-tab-content {
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.spec-section h4 {
  margin: 0 0 6px;
  font-size: 0.88rem;
  font-weight: 800;
  color: #1b2a23;
}

.section-p {
  margin: 0;
  font-size: 0.8rem;
  color: #55675c;
  line-height: 1.55;
}

.checklist-interactive-box {
  background: #f8faf6;
  border: 1px solid #dce4da;
  border-radius: 6px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.78rem;
  color: #23362a;
}

.spec-grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}

.spec-box {
  background: #f8faf6;
  border: 1px solid #dce4da;
  border-radius: 6px;
  padding: 10px 12px;
}

.spec-box h4 {
  margin: 0 0 4px;
  font-size: 0.8rem;
  font-weight: 800;
  color: #1b2a23;
}

.spec-box p {
  margin: 0;
  font-size: 0.76rem;
  color: #4a5c50;
  line-height: 1.45;
}

.guardrails-mini-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.g-mini-item {
  background: #f8faf6;
  border: 1px solid #dce4da;
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.g-mini-item small {
  font-size: 0.65rem;
  color: #77847c;
  font-weight: 700;
}

.g-mini-item strong {
  font-size: 0.92rem;
  color: #1b2a23;
}

.code-viewer {
  margin: 0;
  background: #17241e;
  border: 1px solid #225c43;
  border-radius: 6px;
  padding: 14px;
  color: #c9f06b;
  font-family: var(--mono, ui-monospace, monospace);
  font-size: 0.78rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 500px;
  overflow-y: auto;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse-green {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

.text-gold { color: #c68133; }
.text-cyan { color: #156d94; }
.text-green { color: #225c43; }
.text-red { color: #c65345; }
.text-dim { color: #77847c; }
</style>
