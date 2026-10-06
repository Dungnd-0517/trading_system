<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Database,
  DollarSign,
  HelpCircle,
  Radio,
  RefreshCw,
  Save,
  Server,
  Settings,
  Shield,
  Sliders,
  SlidersHorizontal,
  Volume2,
  Wifi,
  Zap,
} from 'lucide-vue-next'
import { fetchHealth } from '../../services/api'
import { marketStore } from '../../stores/marketStore'
import { orderStore } from '../../stores/orderStore'

const emit = defineEmits(['update-preferences'])

// Storage key
const SETTINGS_KEY = 'fieldnote_user_settings'

// Settings form state
const defaultLotSize = ref(0.1)
const defaultStopLossOffset = ref(5.0)
const defaultTakeProfitOffset = ref(10.0)
const maxSlippagePoints = ref(1.0)
const confirmBeforeOrder = ref(true)
const soundAlerts = ref(true)
const defaultTimeframe = ref('M1')
const displayTimezone = ref('ICT')
const showVolumeDefault = ref(true)

// Save notice
const saveNotice = ref(false)
const pingLoading = ref(false)
const pingResult = ref(null)

// Simulation Account info
const account = computed(() => orderStore.account || {})
const initialBal = computed(() => Number(account.value.initial_balance || 10000))
const currentBal = computed(() => Number(account.value.current_balance || 10000))
const equity = computed(() => Number(account.value.equity || 10000))
const marginUsed = computed(() => Number(account.value.margin_used || 0))
const freeMargin = computed(() => Number(account.value.free_margin || (equity.value - marginUsed.value)))
const totalGrowth = computed(() => {
  if (initialBal.value <= 0) return 0
  return ((currentBal.value - initialBal.value) / initialBal.value) * 100
})

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed.defaultLotSize !== undefined) defaultLotSize.value = parsed.defaultLotSize
      if (parsed.defaultStopLossOffset !== undefined) defaultStopLossOffset.value = parsed.defaultStopLossOffset
      if (parsed.defaultTakeProfitOffset !== undefined) defaultTakeProfitOffset.value = parsed.defaultTakeProfitOffset
      if (parsed.maxSlippagePoints !== undefined) maxSlippagePoints.value = parsed.maxSlippagePoints
      if (parsed.confirmBeforeOrder !== undefined) confirmBeforeOrder.value = parsed.confirmBeforeOrder
      if (parsed.soundAlerts !== undefined) soundAlerts.value = parsed.soundAlerts
      if (parsed.defaultTimeframe !== undefined) defaultTimeframe.value = parsed.defaultTimeframe
      if (parsed.displayTimezone !== undefined) displayTimezone.value = parsed.displayTimezone
      if (parsed.showVolumeDefault !== undefined) showVolumeDefault.value = parsed.showVolumeDefault
    }
  } catch (e) {
    console.warn('Failed to load settings from localStorage', e)
  }
}

function saveSettings() {
  const payload = {
    defaultLotSize: defaultLotSize.value,
    defaultStopLossOffset: defaultStopLossOffset.value,
    defaultTakeProfitOffset: defaultTakeProfitOffset.value,
    maxSlippagePoints: maxSlippagePoints.value,
    confirmBeforeOrder: confirmBeforeOrder.value,
    soundAlerts: soundAlerts.value,
    defaultTimeframe: defaultTimeframe.value,
    displayTimezone: displayTimezone.value,
    showVolumeDefault: showVolumeDefault.value,
  }
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(payload))
  saveNotice.value = true
  setTimeout(() => {
    saveNotice.value = false
  }, 2500)
}

async function testConnectionPing() {
  pingLoading.value = true
  const start = performance.now()
  try {
    const health = await fetchHealth()
    const ms = Math.round(performance.now() - start)
    pingResult.value = {
      status: health?.status || 'ok',
      latency: ms,
      time: new Date().toLocaleTimeString('vi-VN'),
      postgres: health?.services?.postgres === true,
      redis: health?.services?.redis === true,
    }
  } catch {
    pingResult.value = {
      status: 'error',
      latency: Math.round(performance.now() - start),
      time: new Date().toLocaleTimeString('vi-VN'),
      postgres: false,
      redis: false,
    }
  } finally {
    pingLoading.value = false
  }
}

async function refreshAccount() {
  await orderStore.refreshAccount()
}

onMounted(() => {
  loadSettings()
  testConnectionPing()
})
</script>

<template>
  <div class="settings-container">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <span class="icon-chip"><Sliders :size="18" /></span>
        <div>
          <h2>System Settings &amp; Execution Preferences</h2>
          <p>Cấu hình tham số giao dịch mô phỏng, tài khoản demo và giám sát kết nối hạ tầng</p>
        </div>
      </div>
      <div class="header-actions">
        <transition name="fade">
          <span v-if="saveNotice" class="save-toast">
            <CheckCircle2 :size="14" /> Đã lưu cài đặt!
          </span>
        </transition>
        <button class="save-btn" @click="saveSettings">
          <Save :size="14" /> Lưu cấu hình
        </button>
      </div>
    </div>

    <!-- Layout Grid -->
    <div class="settings-grid">
      <!-- Section 1: Simulated Account Portfolio -->
      <section class="card-panel">
        <div class="card-head">
          <div class="head-title">
            <DollarSign :size="16" />
            <h3>Tài khoản mô phỏng (Simulation Account #1)</h3>
          </div>
          <button class="refresh-pill-btn" @click="refreshAccount">
            <RefreshCw :size="12" /> Cập nhật
          </button>
        </div>

        <div class="account-overview-grid">
          <div class="acc-box">
            <span class="acc-lbl">INITIAL BALANCE</span>
            <strong class="acc-val">${{ initialBal.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
            <small class="acc-sub">Vốn nạp ban đầu</small>
          </div>

          <div class="acc-box">
            <span class="acc-lbl">CURRENT BALANCE</span>
            <strong class="acc-val text-green">${{ currentBal.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
            <small class="acc-sub">Số dư khả dụng</small>
          </div>

          <div class="acc-box">
            <span class="acc-lbl">TOTAL EQUITY</span>
            <strong class="acc-val text-green">${{ equity.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</strong>
            <small class="acc-sub">Tài sản ròng hiện tại</small>
          </div>

          <div class="acc-box">
            <span class="acc-lbl">TOTAL GROWTH</span>
            <strong :class="['acc-val', totalGrowth >= 0 ? 'text-green' : 'text-red']">
              {{ totalGrowth >= 0 ? '+' : '' }}{{ totalGrowth.toFixed(2) }}%
            </strong>
            <small class="acc-sub">Hiệu suất tổng thể</small>
          </div>
        </div>

        <div class="margin-specs-bar">
          <div class="spec-item">
            <span>Margin Used:</span>
            <b>${{ marginUsed.toFixed(2) }}</b>
          </div>
          <div class="spec-divider"></div>
          <div class="spec-item">
            <span>Free Margin:</span>
            <b>${{ freeMargin.toFixed(2) }}</b>
          </div>
          <div class="spec-divider"></div>
          <div class="spec-item">
            <span>Open Positions:</span>
            <b>{{ account.open_positions_count || 0 }} lệnh</b>
          </div>
          <div class="spec-divider"></div>
          <div class="spec-item">
            <span>Margin Call Level:</span>
            <b>100% ECN</b>
          </div>
        </div>
      </section>

      <!-- Section 2: Trading Parameters Configuration -->
      <section class="card-panel">
        <div class="card-head">
          <div class="head-title">
            <SlidersHorizontal :size="16" />
            <h3>Tham số khớp lệnh mặc định (Execution Defaults)</h3>
          </div>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label>
              Default Lot Size
              <small>Khối lượng lệnh mở mặc định (1 lot = 100 oz vàng)</small>
            </label>
            <div class="input-unit">
              <input v-model.number="defaultLotSize" type="number" step="0.01" min="0.01" max="10.0" />
              <span>LOTS</span>
            </div>
          </div>

          <div class="form-group">
            <label>
              Default Stop Loss Offset
              <small>Khoảng cách SL tự động từ giá Entry (USD)</small>
            </label>
            <div class="input-unit">
              <input v-model.number="defaultStopLossOffset" type="number" step="0.5" min="0.5" max="100.0" />
              <span>USD</span>
            </div>
          </div>

          <div class="form-group">
            <label>
              Default Take Profit Offset
              <small>Khoảng cách TP tự động từ giá Entry (USD)</small>
            </label>
            <div class="input-unit">
              <input v-model.number="defaultTakeProfitOffset" type="number" step="1.0" min="1.0" max="200.0" />
              <span>USD</span>
            </div>
          </div>

          <div class="form-group">
            <label>
              Max Slippage Tolerance
              <small>Dung sai trượt giá tối đa (points, 1 pt = $0.01)</small>
            </label>
            <div class="input-unit">
              <input v-model.number="maxSlippagePoints" type="number" step="0.5" min="0.0" max="10.0" />
              <span>POINTS</span>
            </div>
          </div>
        </div>

        <div class="toggle-list">
          <label class="toggle-item">
            <input v-model="confirmBeforeOrder" type="checkbox" />
            <div class="toggle-info">
              <strong>Xác nhận trước khi gửi lệnh</strong>
              <small>Hiển thị hộp thoại tóm tắt trước khi gửi lệnh mới lên hệ thống mô phỏng</small>
            </div>
          </label>

          <label class="toggle-item">
            <input v-model="soundAlerts" type="checkbox" />
            <div class="toggle-info">
              <strong>Âm thanh thông báo khi chạm TP/SL</strong>
              <small>Phát tín hiệu âm thanh khi lệnh chạm Take Profit, Stop Loss hoặc đóng vị thế</small>
            </div>
          </label>
        </div>
      </section>

      <!-- Section 3: Infrastructure Diagnostics -->
      <section class="card-panel">
        <div class="card-head">
          <div class="head-title">
            <Server :size="16" />
            <h3>Hạ tầng kỹ thuật &amp; Trạng thái dịch vụ (Diagnostics)</h3>
          </div>
          <button class="test-ping-btn" :disabled="pingLoading" @click="testConnectionPing">
            <Activity :size="12" /> {{ pingLoading ? 'Testing...' : 'Test Connection' }}
          </button>
        </div>

        <div class="infra-list">
          <!-- PostgreSQL -->
          <div class="infra-item">
            <div class="infra-icon-wrap"><Database :size="16" /></div>
            <div class="infra-details">
              <strong>PostgreSQL 16 Engine</strong>
              <span>Host: <code>postgres:5432</code> · DB: <code>trading_system</code></span>
            </div>
            <div class="infra-status">
              <span v-if="pingResult?.postgres !== false" class="badge-online">
                <span class="status-dot green"></span> CONNECTED
              </span>
              <span v-else class="badge-offline">
                <span class="status-dot red"></span> OFFLINE
              </span>
            </div>
          </div>

          <!-- Redis -->
          <div class="infra-item">
            <div class="infra-icon-wrap"><Zap :size="16" /></div>
            <div class="infra-details">
              <strong>Redis 7 In-Memory Pub/Sub</strong>
              <span>Channels: <code>market:ticks</code>, <code>paper:orders</code>, <code>news.upsert</code></span>
            </div>
            <div class="infra-status">
              <span v-if="pingResult?.redis !== false" class="badge-online">
                <span class="status-dot green"></span> CONNECTED
              </span>
              <span v-else class="badge-offline">
                <span class="status-dot red"></span> OFFLINE
              </span>
            </div>
          </div>

          <!-- Binance Feed -->
          <div class="infra-item">
            <div class="infra-icon-wrap"><Wifi :size="16" /></div>
            <div class="infra-details">
              <strong>Binance PAXGUSDT WebSocket Feed</strong>
              <span>Stream: <code>paxgusdt@kline_1m</code> · Alias: <code>XAUUSD</code> · Synthetic ECN Spread: 20 pts ($0.20)</span>
            </div>
            <div class="infra-status">
              <span class="badge-online">
                <span class="status-dot green"></span> ACTIVE STREAM
              </span>
            </div>
          </div>

          <!-- Paper Execution Worker -->
          <div class="infra-item">
            <div class="infra-icon-wrap"><Cpu :size="16" /></div>
            <div class="infra-details">
              <strong>Paper Execution Engine Worker</strong>
              <span>FastAPI Background Task · Quét SL/TP theo từng tick thị trường thực tế</span>
            </div>
            <div class="infra-status">
              <span class="badge-online">
                <span class="status-dot green"></span> RUNNING
              </span>
            </div>
          </div>
        </div>

        <!-- Latency / Ping info -->
        <div v-if="pingResult" class="ping-bar">
          <span>Latency API: <b>{{ pingResult.latency }}ms</b></span>
          <span>Last Check: {{ pingResult.time }}</span>
          <span>Overall Health: <b :class="pingResult.status === 'ok' ? 'text-green' : 'text-red'">{{ pingResult.status.toUpperCase() }}</b></span>
        </div>
      </section>

      <!-- Section 4: Display & Workspace Preferences -->
      <section class="card-panel">
        <div class="card-head">
          <div class="head-title">
            <Radio :size="16" />
            <h3>Tùy chọn hiển thị giao diện (Display Preferences)</h3>
          </div>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label>
              Default Chart Timeframe
              <small>Khung thời gian mặc định khi tải biểu đồ</small>
            </label>
            <div class="segmented-control">
              <button
                v-for="tf in ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']"
                :key="tf"
                :class="{ active: defaultTimeframe === tf }"
                @click="defaultTimeframe = tf"
              >
                {{ tf }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>
              Primary Clock &amp; Timezone
              <small>Múi giờ tham chiếu hiển thị trên các bảng dữ liệu</small>
            </label>
            <div class="segmented-control">
              <button :class="{ active: displayTimezone === 'ICT' }" @click="displayTimezone = 'ICT'">ICT (UTC+7, Vietnam)</button>
              <button :class="{ active: displayTimezone === 'UTC' }" @click="displayTimezone = 'UTC'">UTC (Universal)</button>
            </div>
          </div>
        </div>

        <div class="toggle-list">
          <label class="toggle-item">
            <input v-model="showVolumeDefault" type="checkbox" />
            <div class="toggle-info">
              <strong>Hiển thị cột Volume dưới biểu đồ nến theo mặc định</strong>
              <small>Tự động bật dải khối lượng giao dịch bên dưới biểu đồ kỹ thuật</small>
            </div>
          </label>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.settings-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px 0 24px;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 4px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-chip {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 9px;
  background: #225c43;
  color: #c9f06b;
  box-shadow: 0 2px 6px #225c432b;
}

.view-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #1b2a23;
  letter-spacing: -0.02em;
}

.view-header p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #6d7d74;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.save-toast {
  display: flex;
  align-items: center;
  gap: 6px;
  font: 11px 'DM Mono', monospace;
  color: #1e7043;
  background: #e3f4e6;
  border: 1px solid #c2e5c8;
  padding: 5px 10px;
  border-radius: 6px;
}

.save-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #225c43;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 2px 4px #225c4320;
  transition: background 0.15s ease;
}

.save-btn:hover {
  background: #1b4b36;
}

/* Settings Grid */
.settings-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.card-panel {
  background: #ffffff;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px #00000006;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebf0e9;
}

.head-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #225c43;
}

.head-title h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #1f3026;
}

.refresh-pill-btn, .test-ping-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  background: #f4f7f2;
  border: 1px solid #d0dbce;
  border-radius: 5px;
  padding: 4px 10px;
  font: 10px 'DM Mono', monospace;
  color: #3b4e43;
  cursor: pointer;
  transition: all 0.15s;
}

.refresh-pill-btn:hover, .test-ping-btn:hover {
  background: #e4ebe1;
  color: #225c43;
}

/* Account Overview */
.account-overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}

.acc-box {
  display: flex;
  flex-direction: column;
  padding: 12px 14px;
  background: #f8faf6;
  border: 1px solid #e0e7de;
  border-radius: 6px;
}

.acc-lbl {
  font: 9px 'DM Mono', monospace;
  color: #798b80;
  letter-spacing: 0.04em;
}

.acc-val {
  font: 18px 'DM Mono', monospace;
  font-weight: 700;
  color: #1b2a23;
  margin: 4px 0 2px;
}

.acc-sub {
  font-size: 10px;
  color: #8b9d92;
}

.text-green { color: #1e7043 !important; }
.text-red { color: #b83d30 !important; }

.margin-specs-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  padding: 8px 14px;
  background: #f3f6f1;
  border: 1px solid #e2e8df;
  border-radius: 6px;
  font: 10px 'DM Mono', monospace;
  color: #55675c;
}

.spec-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.spec-item b {
  color: #1f3026;
}

.spec-divider {
  width: 1px;
  height: 14px;
  background: #d4ded3;
}

/* Form Grid */
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  font-weight: 600;
  color: #2b3d32;
}

.form-group label small {
  font-size: 10px;
  font-weight: normal;
  color: #7a8b80;
  margin-top: 1px;
}

.input-unit {
  display: flex;
  align-items: center;
  background: #f8faf6;
  border: 1px solid #ccd8cd;
  border-radius: 5px;
  padding: 0 10px;
  max-width: 280px;
}

.input-unit input {
  border: none;
  background: transparent;
  padding: 8px 0;
  font: 13px 'DM Mono', monospace;
  font-weight: 700;
  color: #1b2a23;
  width: 100%;
  outline: none;
}

.input-unit span {
  font: 9px 'DM Mono', monospace;
  color: #7e8f84;
}

.segmented-control {
  display: flex;
  background: #e7ede5;
  border-radius: 6px;
  padding: 2px;
  width: fit-content;
}

.segmented-control button {
  border: none;
  background: transparent;
  padding: 6px 12px;
  font-size: 11px;
  color: #526359;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.segmented-control button.active {
  background: #ffffff;
  color: #225c43;
  font-weight: 700;
  box-shadow: 0 1px 3px #00000015;
}

/* Toggle List */
.toggle-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 6px;
}

.toggle-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
}

.toggle-item input[type='checkbox'] {
  margin-top: 3px;
  width: 15px;
  height: 15px;
  accent-color: #225c43;
  cursor: pointer;
}

.toggle-info {
  display: flex;
  flex-direction: column;
}

.toggle-info strong {
  font-size: 12px;
  color: #24352b;
}

.toggle-info small {
  font-size: 10px;
  color: #74857b;
}

/* Infrastructure */
.infra-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.infra-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  background: #f8faf6;
  border: 1px solid #e0e7de;
  border-radius: 6px;
}

.infra-icon-wrap {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #e7eee5;
  color: #225c43;
}

.infra-details {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.infra-details strong {
  font-size: 12px;
  color: #1f3026;
}

.infra-details span {
  font-size: 10px;
  color: #74857b;
  margin-top: 1px;
}

.infra-details code {
  font: 10px 'DM Mono', monospace;
  background: #eef2ec;
  padding: 1px 4px;
  border-radius: 3px;
  color: #2c4234;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.green { background: #2e7a52; box-shadow: 0 0 0 2px #2e7a5220; }
.status-dot.red { background: #c25243; }

.badge-online {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  color: #1e7043;
  background: #e3f4e6;
  border: 1px solid #c2e5c8;
  padding: 2px 7px;
  border-radius: 4px;
}

.badge-offline {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  color: #b83d30;
  background: #fde8e5;
  border: 1px solid #f6c0ba;
  padding: 2px 7px;
  border-radius: 4px;
}

.ping-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding: 6px 12px;
  background: #f0f4ee;
  border: 1px solid #dde5db;
  border-radius: 5px;
  font: 10px 'DM Mono', monospace;
  color: #63766a;
}

.ping-bar b {
  color: #1b2a23;
}

@media (max-width: 900px) {
  .account-overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .view-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .account-overview-grid {
    grid-template-columns: 1fr;
  }
  .margin-specs-bar {
    flex-direction: column;
    align-items: flex-start;
  }
  .spec-divider {
    display: none;
  }
}
</style>
