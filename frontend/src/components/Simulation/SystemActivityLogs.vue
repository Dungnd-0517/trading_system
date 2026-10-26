<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  Activity,
  ArrowDownCircle,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clock,
  Filter,
  Layers,
  MessageSquare,
  Newspaper,
  Pause,
  Play,
  RotateCcw,
  Search,
  Shield,
  Sliders,
  Terminal,
  Trash2,
  Zap,
} from 'lucide-vue-next'
import { systemLogStore } from '../../stores/systemLogStore'

const props = defineProps({
  symbol: { type: String, default: 'XAUUSD' },
  lastPrice: { type: Number, default: null },
})

const logContainerRef = ref(null)
const searchInput = ref('')

const filters = [
  { key: 'ALL', label: 'Tất cả' },
  { key: 'AGENTS', label: 'Giao tiếp Agents ⇄' },
  { key: 'ARBITER', label: 'Arbiter 🛡️' },
  { key: 'SENTINEL', label: 'Sentinel 📰' },
  { key: 'VECTOR', label: 'Vector 📐' },
  { key: 'SCRIBE', label: 'Scribe 🧠' },
  { key: 'SYSTEM', label: 'Hệ thống ⚙️' },
]

function onFilterChange(key) {
  systemLogStore.setFilter(key)
}

function onSearchInput(e) {
  systemLogStore.setSearch(e.target.value)
}

function clearSearch() {
  searchInput.value = ''
  systemLogStore.setSearch('')
}

function getSourceClass(source) {
  switch (source) {
    case 'ARBITER':
      return 'source-arbiter'
    case 'SENTINEL':
      return 'source-sentinel'
    case 'VECTOR':
      return 'source-vector'
    case 'SCRIBE':
      return 'source-scribe'
    case 'COUNCIL':
      return 'source-council'
    case 'SYSTEM':
    default:
      return 'source-system'
  }
}

function getLevelClass(level) {
  switch (level) {
    case 'success':
      return 'lvl-success'
    case 'warn':
      return 'lvl-warn'
    case 'critical':
      return 'lvl-critical'
    case 'info':
    default:
      return 'lvl-info'
  }
}

// Tự động cuộn mượt khi có log mới nếu autoScroll = true
watch(
  () => systemLogStore.logs.length,
  () => {
    if (systemLogStore.autoScroll && logContainerRef.value) {
      nextTick(() => {
        logContainerRef.value.scrollTop = 0
      })
    }
  }
)
</script>

<template>
  <section class="activity-logs-panel" aria-label="Bảng Hệ thống Log & Giao tiếp Agents">
    <!-- PANEL HEADER -->
    <header class="logs-header">
      <div class="header-left">
        <div class="terminal-badge">
          <Terminal :size="16" />
        </div>
        <div>
          <div class="title-row">
            <h2 class="title">Bảng Hoạt động Hệ thống &amp; Giao tiếp Agents</h2>
            <span
              class="stream-status"
              :class="systemLogStore.isPaused ? 'status-paused' : 'status-live'"
              :title="systemLogStore.isPaused ? 'Luồng log đang tạm dừng' : 'Luồng log đang truyền trực tiếp theo thời gian thực'"
            >
              <span class="pulse-dot"></span>
              {{ systemLogStore.isPaused ? 'TẠM DỪNG' : 'LIVE STREAM' }}
            </span>
          </div>
          <span class="subtitle">Real-time Inter-Agent Deliberations · Risk Audits · Technical Inferences &amp; Telemetry</span>
        </div>
      </div>

      <div class="header-right">
        <!-- Live Counter Stats -->
        <div class="event-counter" title="Tổng số bản ghi hoạt động hiện có">
          <Activity :size="12" />
          <span>{{ systemLogStore.logs.length }} sự kiện</span>
        </div>

        <!-- Auto-scroll Button -->
        <button
          type="button"
          class="ctrl-btn"
          :class="{ active: systemLogStore.autoScroll }"
          @click="systemLogStore.toggleAutoScroll"
          :title="systemLogStore.autoScroll ? 'Đang tự động bám theo log mới nhất' : 'Tắt tự động cuộn'"
        >
          <ArrowDownCircle :size="13" />
          <span>{{ systemLogStore.autoScroll ? 'Auto-scroll BẬT' : 'Auto-scroll TẮT' }}</span>
        </button>

        <!-- Pause / Resume Button -->
        <button
          type="button"
          class="ctrl-btn pause-resume-btn"
          :class="systemLogStore.isPaused ? 'btn-resume' : 'btn-pause'"
          @click="systemLogStore.togglePause"
          :title="systemLogStore.isPaused ? 'Tiếp tục nhận luồng log' : 'Tạm dừng luồng log để quan sát'"
        >
          <Play v-if="systemLogStore.isPaused" :size="13" />
          <Pause v-else :size="13" />
          <span>{{ systemLogStore.isPaused ? 'Tiếp tục' : 'Tạm dừng' }}</span>
        </button>

        <!-- Clear Logs Button -->
        <button
          type="button"
          class="ctrl-btn btn-clear"
          @click="systemLogStore.clearLogs"
          title="Xóa danh sách log hiện tại"
        >
          <Trash2 :size="13" />
          <span>Xóa log</span>
        </button>
      </div>
    </header>

    <!-- FILTER BAR & SEARCH -->
    <div class="logs-toolbar">
      <div class="filters-pills" role="tablist" aria-label="Bộ lọc nguồn tác tử">
        <button
          v-for="f in filters"
          :key="f.key"
          type="button"
          class="filter-pill"
          :class="{ active: systemLogStore.activeFilter === f.key }"
          @click="onFilterChange(f.key)"
        >
          {{ f.label }}
          <span v-if="f.key !== 'ALL' && systemLogStore.logStats[f.key]" class="pill-count">
            {{ systemLogStore.logStats[f.key] }}
          </span>
        </button>
      </div>

      <div class="search-box">
        <Search :size="13" class="search-icon" />
        <input
          type="text"
          v-model="searchInput"
          @input="onSearchInput"
          placeholder="Lọc nội dung log (ví dụ: BUY, Drawdown, FVG, pgvector)..."
          aria-label="Lọc nội dung log"
        />
        <button
          v-if="searchInput"
          type="button"
          class="clear-search-btn"
          @click="clearSearch"
          title="Xóa tìm kiếm"
        >
          &times;
        </button>
      </div>
    </div>

    <!-- LOG TABLE & STREAM VIEW -->
    <div class="logs-table-wrapper" ref="logContainerRef">
      <table class="logs-table">
        <thead>
          <tr>
            <th class="col-time">THỜI GIAN</th>
            <th class="col-source">NGUỒN / TÁC TỬ</th>
            <th class="col-category">LOẠI SỰ KIỆN</th>
            <th class="col-message">CHI TIẾT HOẠT ĐỘNG &amp; GIAO TIẾP TÁC TỬ</th>
            <th class="col-level">MỨC ĐỘ</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="log in systemLogStore.filteredLogs"
            :key="log.id"
            class="log-row"
            :class="getLevelClass(log.level)"
          >
            <!-- THỜI GIAN -->
            <td class="col-time">
              <span class="mono-time">{{ log.time }}</span>
            </td>

            <!-- NGUỒN / TÁC TỬ -->
            <td class="col-source">
              <span class="source-tag" :class="getSourceClass(log.source)">
                <span v-if="log.source === 'ARBITER'">🛡️ ARBITER</span>
                <span v-else-if="log.source === 'SENTINEL'">📰 SENTINEL</span>
                <span v-else-if="log.source === 'VECTOR'">📐 VECTOR</span>
                <span v-else-if="log.source === 'SCRIBE'">🧠 SCRIBE</span>
                <span v-else-if="log.source === 'COUNCIL'">⇄ COUNCIL</span>
                <span v-else>⚙️ SYSTEM</span>
              </span>
            </td>

            <!-- LOẠI SỰ KIỆN -->
            <td class="col-category">
              <span class="category-badge">{{ log.category }}</span>
            </td>

            <!-- THÔNG ĐIỆP CHI TIẾT -->
            <td class="col-message">
              <div class="message-content">
                {{ log.message }}
              </div>
            </td>

            <!-- MỨC ĐỘ / LEVEL -->
            <td class="col-level">
              <span class="level-badge" :class="getLevelClass(log.level)">
                {{ log.level.toUpperCase() }}
              </span>
            </td>
          </tr>

          <!-- EMPTY STATE -->
          <tr v-if="systemLogStore.filteredLogs.length === 0">
            <td colspan="5" class="empty-state-cell">
              <div class="empty-state">
                <Terminal :size="24" class="empty-icon" />
                <p>Không tìm thấy hoạt động nào phù hợp với bộ lọc hiện tại.</p>
                <button
                  type="button"
                  class="btn-reset-filter"
                  @click="systemLogStore.setFilter('ALL'); clearSearch()"
                >
                  Xóa bộ lọc để xem toàn bộ log
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- LOGS FOOTER STATUS -->
    <footer class="logs-footer">
      <div class="footer-stats">
        <span>Kênh lắng nghe: <code>market:ticks</code>, <code>paper:orders</code>, <code>agent:state</code>, <code>governor:consensus</code></span>
        <span>•</span>
        <span>Độ trễ trung bình: <strong>~12ms</strong></span>
        <span>•</span>
        <span>Tần số cập nhật: <strong>Liên tục (Streaming ~3s/chu kỳ)</strong></span>
      </div>
      <div class="footer-symbol">
        <span>Cặp tài sản: <strong>{{ props.symbol }}</strong></span>
      </div>
    </footer>
  </section>
</template>

<style scoped>
.activity-logs-panel {
  border: 1px solid #d5ded6;
  border-radius: 7px;
  background: #f8faf6;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.05);
  margin-top: 10px;
}

/* HEADER */
.logs-header {
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #e4e9e3;
  background: #f4f7f2;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.terminal-badge {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: #225c43;
  color: #c9f06b;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #1b2a23;
  letter-spacing: 0.2px;
}

.subtitle {
  display: block;
  font-size: 9.5px;
  color: #77847c;
  font-family: 'DM Mono', monospace;
  margin-top: 2px;
}

/* LIVE STATUS BADGE */
.stream-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  font-weight: 700;
  font-family: 'DM Mono', monospace;
  padding: 2px 7px;
  border-radius: 10px;
  letter-spacing: 0.5px;
}

.status-live {
  background: #e2f4e8;
  color: #15803d;
  border: 1px solid #bbf0cb;
}

.status-paused {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #16a34a;
  box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.3);
  animation: pulse 1.6s infinite ease-in-out;
}

.status-paused .pulse-dot {
  background: #d97706;
  box-shadow: none;
  animation: none;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.7; }
  50% { transform: scale(1.3); opacity: 1; box-shadow: 0 0 6px rgba(22, 163, 74, 0.6); }
  100% { transform: scale(0.9); opacity: 0.7; }
}

/* HEADER CONTROLS */
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.event-counter {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-family: 'DM Mono', monospace;
  color: #55645a;
  background: #e8eee6;
  padding: 4px 8px;
  border-radius: 5px;
  border: 1px solid #d4ded4;
}

.ctrl-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 600;
  padding: 5px 9px;
  border-radius: 5px;
  border: 1px solid #d4ded4;
  background: #ffffff;
  color: #425247;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ctrl-btn:hover {
  background: #eef3ec;
  color: #1b2a23;
  border-color: #c2cfc1;
}

.ctrl-btn.active {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}

.pause-resume-btn.btn-resume {
  background: #fef3c7;
  color: #92400e;
  border-color: #fcd34d;
}

.pause-resume-btn.btn-pause:hover {
  color: #92400e;
}

.btn-clear:hover {
  color: #b91c1c;
  border-color: #fca5a5;
  background: #fef2f2;
}

/* TOOLBAR & FILTERS */
.logs-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #eef3ec;
  border-bottom: 1px solid #e1e7df;
  gap: 12px;
  flex-wrap: wrap;
}

.filters-pills {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.filter-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid transparent;
  background: transparent;
  color: #55645a;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
}

.filter-pill:hover {
  background: #e1eae0;
  color: #1b2a23;
}

.filter-pill.active {
  background: #ffffff;
  color: #225c43;
  border-color: #c8d7c7;
  box-shadow: 0 1px 2px rgba(27, 42, 35, 0.08);
  font-weight: 700;
}

.pill-count {
  font-size: 8.5px;
  font-family: 'DM Mono', monospace;
  padding: 1px 4px;
  border-radius: 6px;
  background: #e3ede1;
  color: #2a3a31;
}

.filter-pill.active .pill-count {
  background: #225c43;
  color: #c9f06b;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 250px;
}

.search-icon {
  position: absolute;
  left: 9px;
  color: #77847c;
  pointer-events: none;
}

.search-box input {
  width: 100%;
  height: 28px;
  padding: 0 24px 0 28px;
  font-size: 10px;
  font-family: inherit;
  border: 1px solid #cfd9ce;
  border-radius: 5px;
  background: #ffffff;
  color: #1b2a23;
  outline: none;
  transition: border-color 0.15s ease;
}

.search-box input:focus {
  border-color: #225c43;
  box-shadow: 0 0 0 2px rgba(34, 92, 67, 0.12);
}

.clear-search-btn {
  position: absolute;
  right: 6px;
  background: transparent;
  border: none;
  font-size: 13px;
  color: #88968e;
  cursor: pointer;
}

/* LOGS TABLE */
.logs-table-wrapper {
  max-height: 310px;
  overflow-y: auto;
  background: #ffffff;
}

.logs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10.5px;
  text-align: left;
}

.logs-table thead {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #f7faf6;
}

.logs-table th {
  padding: 7px 10px;
  font-size: 9px;
  font-weight: 700;
  font-family: 'DM Mono', monospace;
  color: #637367;
  border-bottom: 1px solid #e1e7df;
  letter-spacing: 0.5px;
}

.logs-table td {
  padding: 7px 10px;
  border-bottom: 1px solid #f0f4ef;
  vertical-align: middle;
}

.log-row {
  transition: background-color 0.12s ease;
}

.log-row:hover {
  background-color: #f7faf6;
}

/* ROW HIGHLIGHTS BY LEVEL */
.log-row.lvl-success {
  border-left: 3px solid #22c55e;
}

.log-row.lvl-warn {
  border-left: 3px solid #f59e0b;
  background-color: #fffbeb15;
}

.log-row.lvl-critical {
  border-left: 3px solid #ef4444;
  background-color: #fef2f225;
}

.log-row.lvl-info {
  border-left: 3px solid #60a5fa;
}

/* COLUMNS */
.col-time {
  width: 95px;
  white-space: nowrap;
}

.mono-time {
  font-family: 'DM Mono', monospace;
  font-size: 9.5px;
  color: #6a796e;
}

.col-source {
  width: 120px;
  white-space: nowrap;
}

.source-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
  font-family: 'DM Mono', monospace;
  letter-spacing: 0.3px;
}

/* SOURCE BADGE COLORS */
.source-arbiter {
  background: #fbf3d5;
  color: #8b6b23;
  border: 1px solid #eddca8;
}

.source-sentinel {
  background: #f3e8ff;
  color: #7e22ce;
  border: 1px solid #e9d5ff;
}

.source-vector {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.source-scribe {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.source-council {
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fed7aa;
}

.source-system {
  background: #f0fdfa;
  color: #0f766e;
  border: 1px solid #99f6e4;
}

.col-category {
  width: 130px;
  white-space: nowrap;
}

.category-badge {
  font-family: 'DM Mono', monospace;
  font-size: 8.5px;
  padding: 2px 5px;
  background: #edf2eb;
  color: #4b5a50;
  border-radius: 4px;
}

.col-message {
  color: #1b2a23;
}

.message-content {
  line-height: 1.45;
  font-size: 10px;
  color: #24352a;
  word-break: break-word;
}

.col-level {
  width: 70px;
  text-align: right;
  white-space: nowrap;
}

.level-badge {
  display: inline-block;
  padding: 2px 5px;
  border-radius: 3px;
  font-family: 'DM Mono', monospace;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.4px;
}

.lvl-info .level-badge {
  background: #e0f2fe;
  color: #0369a1;
}

.lvl-success .level-badge {
  background: #dcfce7;
  color: #15803d;
}

.lvl-warn .level-badge {
  background: #fef3c7;
  color: #b45309;
}

.lvl-critical .level-badge {
  background: #fee2e2;
  color: #b91c1c;
}

/* EMPTY STATE */
.empty-state-cell {
  padding: 40px 10px !important;
  text-align: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #77847c;
}

.empty-icon {
  color: #a4b3a7;
}

.empty-state p {
  margin: 0;
  font-size: 11px;
}

.btn-reset-filter {
  font-size: 10px;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid #c8d5c6;
  background: #f0f5ee;
  color: #225c43;
  cursor: pointer;
}

.btn-reset-filter:hover {
  background: #e2ece0;
}

/* FOOTER */
.logs-footer {
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 14px;
  background: #f4f7f2;
  border-top: 1px solid #e4e9e3;
  font-size: 9px;
  font-family: 'DM Mono', monospace;
  color: #77847c;
}

.footer-stats {
  display: flex;
  align-items: center;
  gap: 8px;
}

.footer-stats code {
  color: #225c43;
}

.footer-stats strong {
  color: #3b4e42;
}

.footer-symbol strong {
  color: #225c43;
}
</style>
