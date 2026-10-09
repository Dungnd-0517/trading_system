<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Clock,
  Compass,
  Crosshair,
  RotateCw,
  ShieldAlert,
  Sliders,
  TrendingUp,
  XCircle,
  Zap,
} from 'lucide-vue-next'
import { fetchMarketAnalysis, evaluateSignals } from '../../services/api'
import { orderStore } from '../../stores/orderStore'

const props = defineProps({
  symbol: { type: String, default: 'XAUUSD' },
  lastPrice: { type: Number, default: null },
  account: {
    type: Object,
    default: () => ({ current_balance: 10000.0 }),
  },
})

const loading = ref(false)
const error = ref('')
const analysis = ref(null)
const lastUpdated = ref('')
const riskPercent = ref(1.0)
const scanning = ref(false)
const executing = ref(false)
const actionMessage = ref('')
const actionMessageType = ref('info')
let timer = null

const activePrice = computed(() => {
  return props.lastPrice || analysis.value?.current_price || 0
})

const dealingRange = computed(() => {
  return analysis.value?.intraday_trend?.dealing_range || { high: 0, low: 0, equilibrium: 0 }
})

const rangePercent = computed(() => {
  const { high, low } = dealingRange.value
  const price = activePrice.value
  if (!high || !low || high === low) return 50
  const pct = ((price - low) / (high - low)) * 100
  return Math.min(100, Math.max(0, Math.round(pct)))
})

const calculatedLots = computed(() => {
  const setup = analysis.value?.predicted_setup
  if (!setup) return 0.20
  const balance = Number(props.account?.current_balance) || 10000.0
  const riskAmount = balance * (riskPercent.value / 100)
  const entry = Number(setup.entry_price)
  const sl = Number(setup.stop_loss)
  const dist = Math.abs(entry - sl)
  if (!dist || dist <= 0) return 0.20
  // 1 standard lot vàng XAUUSD = 100 troy oz ($100 per 1.00 move)
  const lots = riskAmount / (dist * 100)
  return Math.max(0.01, Number(lots.toFixed(2)))
})

async function loadAnalysis() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchMarketAnalysis(props.symbol)
    analysis.value = data
    const now = new Date()
    lastUpdated.value = now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch (err) {
    error.value = err.message || 'Không thể tải phân tích thị trường'
  } finally {
    loading.value = false
  }
}

async function handleScanSignals() {
  scanning.value = true
  actionMessage.value = ''
  try {
    const res = await evaluateSignals(props.symbol)
    await orderStore.fetchSignals()
    if (res?.signal) {
      actionMessageType.value = 'success'
      const sig = res.signal
      actionMessage.value = `Đã phát hiện tín hiệu SMC: ${sig.side} tại $${Number(sig.entry_price).toFixed(2)} (SL: $${Number(sig.stop_loss).toFixed(2)}, TP: $${Number(sig.take_profit_1).toFixed(2)}, R:R 1:${sig.risk_reward})`
    } else {
      actionMessageType.value = 'info'
      actionMessage.value = res?.message || 'Đã quét nến M15: Không phát hiện setup SMC hợp lệ tại nến hiện tại hoặc ngoài phiên Kill Zone.'
    }
    await loadAnalysis()
    setTimeout(() => { actionMessage.value = '' }, 6000)
  } catch (err) {
    actionMessageType.value = 'error'
    actionMessage.value = err.message || 'Lỗi quét tín hiệu SMC'
  } finally {
    scanning.value = false
  }
}

async function handleExecuteSetup() {
  const setup = analysis.value?.predicted_setup
  if (!setup || !setup.entry_price) return

  if (orderStore.circuitBreaker.active) {
    actionMessageType.value = 'error'
    actionMessage.value = 'Circuit Breaker đang chặn vào lệnh do tin tức USD đỏ!'
    return
  }

  executing.value = true
  actionMessage.value = ''
  try {
    const side = setup.direction === 'BUY' ? 'BUY' : 'SELL'
    await orderStore.submitOrder({
      symbol: props.symbol,
      side,
      order_type: 'MARKET',
      volume: calculatedLots.value,
      stop_loss: Number(setup.stop_loss),
      take_profit: Number(setup.take_profit),
      comment: `SMC_SETUP_${props.symbol}`,
    })
    actionMessageType.value = 'success'
    actionMessage.value = `Đã kích hoạt lệnh ${side} ${calculatedLots.value} lot tại $${activePrice.value.toFixed(2)}!`
    await loadAnalysis()
    setTimeout(() => { actionMessage.value = '' }, 6000)
  } catch (err) {
    actionMessageType.value = 'error'
    actionMessage.value = err.message || 'Lỗi gửi lệnh theo Setup'
  } finally {
    executing.value = false
  }
}

onMounted(() => {
  loadAnalysis()
  // Tự động làm mới phân tích thị trường mỗi 30 giây
  timer = setInterval(() => {
    loadAnalysis()
  }, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <section class="analysis-panel" aria-label="Phân tích thị trường & Kịch bản giao dịch">
    <!-- PANEL HEADER -->
    <header class="panel-header">
      <div class="header-left">
        <Compass :size="16" class="header-icon" />
        <div>
          <h2 class="title">Phân tích Thị trường &amp; Trạng thái Kịch bản</h2>
          <span class="subtitle">SMC Framework · Multi-timeframe Bias · Setup &amp; Invalidation Rules</span>
        </div>
      </div>
      <div class="header-right">
        <span class="price-badge" title="Giá thị trường hiện tại">
          <small>{{ props.symbol }}</small>
          <strong>${{ activePrice ? activePrice.toFixed(2) : '—' }}</strong>
        </span>
        <button
          class="refresh-btn"
          :class="{ rotating: loading }"
          title="Làm mới phân tích"
          @click="loadAnalysis"
        >
          <RotateCw :size="12" />
          <span>{{ loading ? 'Đang tải...' : (lastUpdated || 'Cập nhật') }}</span>
        </button>
      </div>
    </header>

    <div v-if="error" class="error-banner">
      <AlertTriangle :size="14" />
      <span>{{ error }}</span>
    </div>

    <div v-else-if="analysis" class="analysis-content">
      <!-- SUMMARY RIBBON -->
      <div class="summary-ribbon">
        <div class="ribbon-item">
          <span class="ribbon-label">HTF D1/H4 BIAS</span>
          <strong :class="analysis.htf_trend.bias === 'BULLISH' ? 'bias-bull' : 'bias-bear'">
            {{ analysis.htf_trend.bias }}
          </strong>
        </div>
        <div class="ribbon-item">
          <span class="ribbon-label">INTRADAY ZONE</span>
          <strong :class="analysis.intraday_trend.current_zone === 'DISCOUNT' ? 'zone-discount' : 'zone-premium'">
            {{ analysis.intraday_trend.current_zone }} ({{ rangePercent }}%)
          </strong>
        </div>
        <div class="ribbon-item">
          <span class="ribbon-label">KILL ZONE STATUS</span>
          <strong :class="analysis.intraday_trend.is_kill_zone ? 'session-active' : 'session-off'">
            {{ analysis.intraday_trend.is_kill_zone ? 'ACTIVE KZ' : 'OFF-KZ WINDOW' }}
          </strong>
        </div>
        <div class="ribbon-item">
          <span class="ribbon-label">SETUP ENGINE</span>
          <strong class="setup-waiting">
            {{ analysis.predicted_setup.status }}
          </strong>
        </div>
      </div>

      <!-- MAIN 5 SECTIONS GRID -->
      <div class="cards-grid">
        <!-- 1. XU HƯỚNG DÀI HẠN (HTF CONFIRMATION) -->
        <article class="analysis-card htf-card">
          <div class="card-head">
            <div class="card-title-group">
              <TrendingUp :size="15" class="card-icon text-bull" />
              <h3>1. Xu hướng Dài hạn (HTF Confirmation)</h3>
            </div>
            <span class="badge badge-bull">XÁC NHẬN D1 &amp; H4</span>
          </div>

          <div class="card-body">
            <div class="metric-row">
              <span class="m-label">Cấu trúc khung lớn:</span>
              <strong class="m-val bias-bull">
                {{ analysis.htf_trend.bias }} (TĂNG GIÁ BỀN VỮNG)
              </strong>
            </div>
            <div class="metric-row">
              <span class="m-label">Đồng thuận xu hướng:</span>
              <span class="align-tag" :class="{ 'tag-ok': analysis.htf_trend.alignment }">
                <CheckCircle2 :size="12" /> Đồng thuận đa khung D1 / H4
              </span>
            </div>
            <div class="metric-row">
              <span class="m-label">Mốc Swing High:</span>
              <span class="m-num">${{ analysis.htf_trend.swing_high?.toFixed(2) }}</span>
            </div>
            <div class="metric-row">
              <span class="m-label">Mốc Swing Low:</span>
              <span class="m-num">${{ analysis.htf_trend.swing_low?.toFixed(2) }}</span>
            </div>
            <p class="card-desc">
              {{ analysis.htf_trend.description }}
            </p>
          </div>
        </article>

        <!-- 2. XU HƯỚNG HIỆN TẠI TRONG NGÀY (INTRADAY BIAS) -->
        <article class="analysis-card intraday-card">
          <div class="card-head">
            <div class="card-title-group">
              <Clock :size="15" class="card-icon text-zone" />
              <h3>2. Xu hướng Trong ngày (Intraday Trend)</h3>
            </div>
            <span class="badge" :class="analysis.intraday_trend.current_zone === 'DISCOUNT' ? 'badge-discount' : 'badge-premium'">
              {{ analysis.intraday_trend.current_zone }} ZONE
            </span>
          </div>

          <div class="card-body">
            <div class="metric-row">
              <span class="m-label">Xu hướng phiên:</span>
              <strong class="m-val">{{ analysis.intraday_trend.bias }}</strong>
            </div>
            <div class="metric-row">
              <span class="m-label">Phiên giao dịch:</span>
              <span class="session-tag">
                {{ analysis.intraday_trend.session_name }}
              </span>
            </div>

            <!-- Dealing Range Visual Bar -->
            <div class="range-box">
              <div class="range-labels">
                <span>Low: ${{ dealingRange.low?.toFixed(2) }}</span>
                <span class="range-eq">EQ (50%): ${{ dealingRange.equilibrium?.toFixed(2) }}</span>
                <span>High: ${{ dealingRange.high?.toFixed(2) }}</span>
              </div>
              <div class="range-track">
                <div class="track-discount" style="width: 50%" title="Vùng Discount (< 50%)"></div>
                <div class="track-premium" style="width: 50%" title="Vùng Premium (> 50%)"></div>
                <div
                  class="needle-indicator"
                  :style="{ left: `${rangePercent}%` }"
                  :title="`Giá hiện tại: $${activePrice.toFixed(2)} (${rangePercent}%)`"
                >
                  <span class="needle-tip">▲</span>
                </div>
              </div>
              <div class="range-subtext">
                <span v-if="analysis.intraday_trend.current_zone === 'DISCOUNT'" class="subtext-discount">
                  ★ Giá ở vùng Chiết khấu (Discount) &mdash; Ưu tiên tìm lệnh Mua theo dòng tiền
                </span>
                <span v-else class="subtext-premium">
                  ★ Giá ở vùng Giá cao (Premium) &mdash; Cẩn trọng rủi ro mua đuổi đỉnh
                </span>
              </div>
            </div>
          </div>
        </article>
      </div>

      <!-- 3. CÁC KỊCH BẢN ĐỀ XUẤT (THEO DÕI) -->
      <article class="analysis-card scenarios-card">
        <div class="card-head">
          <div class="card-title-group">
            <Activity :size="15" class="card-icon text-accent" />
            <h3>3. Các Kịch bản Đề xuất (Theo dõi thị trường)</h3>
          </div>
          <span class="badge badge-neutral">2 SCENARIOS IN MONITOR</span>
        </div>

        <div class="scenarios-wrapper">
          <!-- Scenario 1: Primary -->
          <div class="scenario-box primary-box">
            <div class="scenario-top">
              <div class="sc-badge-row">
                <span class="sc-tag tag-primary">KỊCH BẢN ƯU TIÊN</span>
                <span class="sc-prob prob-high">Xác suất: {{ analysis.scenarios.primary.probability }}</span>
              </div>
              <h4 class="sc-name">{{ analysis.scenarios.primary.name }}</h4>
            </div>
            <div class="sc-details">
              <div class="sc-row">
                <span class="sc-label">Điều kiện kích hoạt:</span>
                <p class="sc-text">{{ analysis.scenarios.primary.condition }}</p>
              </div>
              <div class="sc-row">
                <span class="sc-label">Mục tiêu giá (Target):</span>
                <p class="sc-text target-text">{{ analysis.scenarios.primary.target }}</p>
              </div>
            </div>
            <div class="sc-foot">
              <span class="status-pill pill-active">
                ● {{ analysis.scenarios.primary.status }}
              </span>
            </div>
          </div>

          <!-- Scenario 2: Alternative -->
          <div class="scenario-box alt-box">
            <div class="scenario-top">
              <div class="sc-badge-row">
                <span class="sc-tag tag-alt">KỊCH BẢN DỰ PHÒNG</span>
                <span class="sc-prob prob-low">Xác suất: {{ analysis.scenarios.alternative.probability }}</span>
              </div>
              <h4 class="sc-name">{{ analysis.scenarios.alternative.name }}</h4>
            </div>
            <div class="sc-details">
              <div class="sc-row">
                <span class="sc-label">Điều kiện kích hoạt:</span>
                <p class="sc-text">{{ analysis.scenarios.alternative.condition }}</p>
              </div>
              <div class="sc-row">
                <span class="sc-label">Mục tiêu giá (Target):</span>
                <p class="sc-text target-text">{{ analysis.scenarios.alternative.target }}</p>
              </div>
            </div>
            <div class="sc-foot">
              <span class="status-pill pill-secondary">
                ○ {{ analysis.scenarios.alternative.status }}
              </span>
            </div>
          </div>
        </div>
      </article>

      <!-- 4. DỰ ĐOÁN ĐIỂM VÀO LỆNH KHI ĐỦ ĐIỀU KIỆN -->
      <article class="analysis-card setup-card">
        <div class="card-head">
          <div class="card-title-group">
            <Crosshair :size="15" class="card-icon text-bull" />
            <h3>4. Dự đoán Điểm vào lệnh khi đủ điều kiện</h3>
          </div>
          <span class="badge badge-waiting">
            {{ analysis.predicted_setup.status_label }}
          </span>
        </div>

        <div class="card-body">
          <div class="setup-grid">
            <!-- DIRECTION & ENTRY ZONE -->
            <div class="setup-tile">
              <span class="tile-label">HƯỚNG LỆNH DỰ KIẾN</span>
              <strong class="tile-val val-buy">
                <ArrowUp :size="14" /> {{ analysis.predicted_setup.direction }}
              </strong>
              <small class="tile-sub">Chỉ mở lệnh khi xuất hiện nến xác nhận M15</small>
            </div>

            <div class="setup-tile">
              <span class="tile-label">VÙNG VÀO LỆNH (ENTRY ZONE)</span>
              <strong class="tile-val val-entry">{{ analysis.predicted_setup.entry_zone }}</strong>
              <small class="tile-sub">Điểm kích hoạt chuẩn: <b>${{ analysis.predicted_setup.entry_price?.toFixed(2) }}</b></small>
            </div>

            <div class="setup-tile">
              <span class="tile-label">ĐIỂM CẮT LỖ (SL)</span>
              <strong class="tile-val val-sl">${{ analysis.predicted_setup.stop_loss?.toFixed(2) }}</strong>
              <small class="tile-sub">
                Khoảng cách: -{{ (analysis.predicted_setup.entry_price - analysis.predicted_setup.stop_loss).toFixed(2) }} giá
              </small>
            </div>

            <div class="setup-tile">
              <span class="tile-label">ĐIỂM CHỐT LỜI (TP)</span>
              <strong class="tile-val val-tp">${{ analysis.predicted_setup.take_profit?.toFixed(2) }}</strong>
              <small class="tile-sub">
                Khoảng cách: +{{ (analysis.predicted_setup.take_profit - analysis.predicted_setup.entry_price).toFixed(2) }} giá
              </small>
            </div>

            <div class="setup-tile">
              <span class="tile-label">TỶ LỆ LỜI / LỖ (R:R)</span>
              <strong class="tile-val val-rr">{{ analysis.predicted_setup.risk_reward }}</strong>
              <small class="tile-sub text-ok">Đạt chuẩn tối ưu (&gt; 1:2.0)</small>
            </div>

            <!-- DYNAMIC LOT SIZE WITH RISK CALCULATOR -->
            <div class="setup-tile lot-tile">
              <div class="lot-header">
                <span class="tile-label">TỔNG LOT SIZE ĐỀ XUẤT</span>
                <div class="risk-pills">
                  <span class="risk-note">Risk:</span>
                  <button
                    v-for="r in [0.5, 1.0, 1.5, 2.0]"
                    :key="r"
                    class="risk-btn"
                    :class="{ active: riskPercent === r }"
                    @click="riskPercent = r"
                  >
                    {{ r }}%
                  </button>
                </div>
              </div>
              <strong class="tile-val val-lot">{{ calculatedLots }} Lots</strong>
              <small class="tile-sub lot-calc-info">
                Số dư: ${{ (props.account?.current_balance || 10000).toLocaleString() }} &middot;
                Rủi ro: ${{ ((props.account?.current_balance || 10000) * (riskPercent / 100)).toFixed(0) }}
              </small>
            </div>
          </div>

          <!-- ACTION CONTROLS & CIRCUIT BREAKER WARNING -->
          <div class="setup-actions-bar">
            <div v-if="orderStore.circuitBreaker.active" class="circuit-inline-alert">
              <ShieldAlert :size="14" />
              <span><b>Cảnh báo Ngắt mạch:</b> Khóa mở lệnh do tin tức USD đỏ ({{ orderStore.circuitBreaker.reason || 'High Impact USD Event' }})</span>
            </div>

            <div class="actions-buttons-row">
              <button
                class="btn-action-primary"
                :disabled="executing || orderStore.circuitBreaker.active || !analysis.predicted_setup?.entry_price"
                @click="handleExecuteSetup"
                title="Tự động mở vị thế theo kịch bản và lot tính toán"
              >
                <Zap :size="14" />
                <span>{{ executing ? 'Đang gửi lệnh...' : 'Kích hoạt theo Setup ⚡' }}</span>
              </button>

              <button
                class="btn-action-secondary"
                :disabled="scanning"
                @click="handleScanSignals"
                title="Quét lại tín hiệu SMC trên nến M15"
              >
                <RotateCw :size="13" :class="{ 'spin-icon': scanning }" />
                <span>{{ scanning ? 'Đang quét...' : 'Quét Tín hiệu M15' }}</span>
              </button>
            </div>

            <div v-if="actionMessage" class="setup-action-feedback" :class="actionMessageType">
              {{ actionMessage }}
            </div>
          </div>
        </div>
      </article>

      <!-- 5. XÁC NHẬN BỎ QUA CHỈ BÁO & HỦY KỊCH BẢN -->
      <article class="analysis-card invalidation-card">
        <div class="card-head">
          <div class="card-title-group">
            <ShieldAlert :size="15" class="card-icon text-warn" />
            <h3>5. Xác nhận Bỏ qua Chỉ báo &amp; Điều kiện Hủy kịch bản</h3>
          </div>
          <span class="badge badge-warn">QUY TẮC BẢO VỆ VỐN</span>
        </div>

        <div class="card-body">
          <div class="invalidation-notice">
            <AlertTriangle :size="14" class="notice-icon" />
            <span>
              <b>Nguyên tắc kỷ luật SMC:</b> Nếu thị trường vi phạm bất kỳ tiêu chí nào dưới đây, tín hiệu sẽ bị
              <b>hủy bỏ ngay lập tức</b> và hệ thống chuyển về trạng thái đứng ngoài an toàn để bảo vệ vốn.
            </span>
          </div>

          <div class="invalidation-list">
            <div
              v-for="(rule, idx) in analysis.invalidation_criteria"
              :key="rule.id || idx"
              class="inv-item"
            >
              <div class="inv-index">
                <XCircle :size="14" class="inv-icon" />
                <span>#{{ idx + 1 }}</span>
              </div>
              <div class="inv-details">
                <strong class="inv-cond">{{ rule.condition }}</strong>
                <p class="inv-action">&rarr; {{ rule.action }}</p>
              </div>
              <div class="inv-status">
                <span
                  class="inv-badge"
                  :class="{
                    'badge-safe': rule.status === 'AN TOÀN' || rule.status === 'ĐẠT CHUẨN',
                    'badge-wait': rule.status === 'THEO DÕI' || rule.status === 'CHỜ PHIÊN',
                  }"
                >
                  {{ rule.status }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.analysis-panel {
  border: 1px solid #d5ded6;
  border-radius: 7px;
  background: #f8faf6;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* HEADER */
.panel-header {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-bottom: 1px solid #e4e9e3;
  background: #f4f7f2;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  color: #3b7454;
}

.title {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: #24352a;
  letter-spacing: 0.2px;
}

.subtitle {
  display: block;
  font-size: 9px;
  color: #7b887e;
  font-family: 'DM Mono', monospace;
  margin-top: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.price-badge {
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #e9f0e8;
  border: 1px solid #d0dcd0;
}

.price-badge small {
  font: 8px 'DM Mono', monospace;
  color: #6d7d71;
}

.price-badge strong {
  font: 11px 'DM Mono', monospace;
  color: #24352a;
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #fff;
  border: 1px solid #cfd8d0;
  color: #55665b;
  font: 9px 'DM Mono', monospace;
  cursor: pointer;
  transition: all 0.15s ease;
}

.refresh-btn:hover {
  background: #f0f4ee;
  border-color: #bccbc0;
  color: #2b3b30;
}

.refresh-btn.rotating svg {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  background: #fdf3f2;
  color: #b54a3e;
  font-size: 11px;
}

/* RIBBON */
.summary-ribbon {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-bottom: 1px solid #e0e6df;
  background: #f0f4ee;
}

.ribbon-item {
  padding: 8px 12px;
  border-right: 1px solid #e0e6df;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ribbon-item:last-child {
  border-right: none;
}

.ribbon-label {
  font: 8px 'DM Mono', monospace;
  color: #839185;
}

.ribbon-item strong {
  font: 10px 'DM Mono', monospace;
  letter-spacing: 0.3px;
}

.bias-bull { color: #2e7a52; font-weight: 700; }
.bias-bear { color: #bb594c; font-weight: 700; }
.zone-discount { color: #2e7a52; }
.zone-premium { color: #b54a3e; }
.session-active { color: #2e7a52; }
.session-off { color: #839185; }
.setup-waiting { color: #9c6c19; }

/* CONTENT & CARDS GRID */
.analysis-content {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cards-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.analysis-card {
  border: 1px solid #e1e7e0;
  border-radius: 6px;
  background: #fff;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(30, 45, 35, 0.02);
}

.card-head {
  padding: 8px 12px;
  background: #f9fbf8;
  border-bottom: 1px solid #e8ede7;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title-group {
  display: flex;
  align-items: center;
  gap: 7px;
}

.card-icon {
  flex-shrink: 0;
}

.card-head h3 {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  color: #2b3a30;
}

.card-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* BADGES */
.badge {
  font: 8px 'DM Mono', monospace;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
}

.badge-bull { background: #eaf3ed; color: #2b704c; border: 1px solid #c9e2d3; }
.badge-discount { background: #eaf3ed; color: #2b704c; border: 1px solid #c9e2d3; }
.badge-premium { background: #fdf2f1; color: #ba4f43; border: 1px solid #f2c7c2; }
.badge-waiting { background: #fef8eb; color: #9a6b18; border: 1px solid #f6e3b5; }
.badge-warn { background: #fdf3f0; color: #b84b3e; border: 1px solid #f5cfc9; }
.badge-neutral { background: #eef2ec; color: #6a796e; }

/* METRICS */
.metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
}

.m-label {
  color: #79877d;
  font-family: 'DM Mono', monospace;
  font-size: 9px;
}

.m-val {
  color: #2e3e33;
}

.m-num {
  font: 10px 'DM Mono', monospace;
  color: #2b3930;
  font-weight: 600;
}

.align-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  color: #6a796e;
}

.align-tag.tag-ok {
  color: #2b704c;
  font-weight: 600;
}

.session-tag {
  font: 9px 'DM Mono', monospace;
  background: #edf2eb;
  padding: 2px 5px;
  border-radius: 3px;
  color: #4b5d51;
}

.card-desc {
  margin: 4px 0 0;
  font-size: 10px;
  line-height: 1.45;
  color: #5e6f64;
  background: #f6f8f5;
  padding: 6px 8px;
  border-radius: 4px;
  border-left: 3px solid #367d58;
}

/* DEALING RANGE VISUAL */
.range-box {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font: 8px 'DM Mono', monospace;
  color: #7e8d82;
}

.range-eq {
  color: #3b5c46;
  font-weight: 600;
}

.range-track {
  position: relative;
  height: 10px;
  background: #e2e8e0;
  border-radius: 5px;
  display: flex;
  overflow: visible;
}

.track-discount {
  background: linear-gradient(90deg, #b8dbc5, #88c49e);
  border-top-left-radius: 5px;
  border-bottom-left-radius: 5px;
}

.track-premium {
  background: linear-gradient(90deg, #f3cfca, #e99e95);
  border-top-right-radius: 5px;
  border-bottom-right-radius: 5px;
}

.needle-indicator {
  position: absolute;
  top: -6px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 2;
  cursor: pointer;
}

.needle-tip {
  color: #1f2e24;
  font-size: 12px;
  line-height: 1;
}

.range-subtext {
  font-size: 9px;
  line-height: 1.35;
  margin-top: 2px;
}

.subtext-discount {
  color: #2b704c;
  font-weight: 600;
}

.subtext-premium {
  color: #ba4f43;
  font-weight: 600;
}

/* SCENARIOS */
.scenarios-wrapper {
  padding: 10px 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.scenario-box {
  border: 1px solid #e1e7e0;
  border-radius: 5px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fbfdfa;
}

.primary-box {
  border-color: #c9ded0;
  background: #f7fbf8;
}

.alt-box {
  border-color: #eeddd8;
  background: #fdfaf9;
}

.sc-badge-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.sc-tag {
  font: 8px 'DM Mono', monospace;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
}

.tag-primary { background: #e3f2e7; color: #286c47; }
.tag-alt { background: #faeae7; color: #b0493d; }

.sc-prob {
  font: 8px 'DM Mono', monospace;
}

.prob-high { color: #286c47; font-weight: 700; }
.prob-low { color: #88978c; }

.sc-name {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  color: #28372d;
}

.sc-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 10px;
}

.sc-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sc-label {
  font: 8px 'DM Mono', monospace;
  color: #829085;
}

.sc-text {
  margin: 0;
  font-size: 10px;
  line-height: 1.4;
  color: #445449;
}

.target-text {
  color: #2b704c;
  font-weight: 600;
}

.sc-foot {
  margin-top: auto;
  padding-top: 4px;
}

.status-pill {
  display: inline-block;
  font: 8px 'DM Mono', monospace;
  padding: 2px 6px;
  border-radius: 3px;
}

.pill-active { background: #e6f3ea; color: #2b704c; }
.pill-secondary { background: #f0f3ef; color: #6e7e72; }

/* PREDICTED SETUP */
.setup-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.setup-tile {
  background: #f9fbf8;
  border: 1px solid #e4eae2;
  border-radius: 5px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.tile-label {
  font: 8px 'DM Mono', monospace;
  color: #849387;
}

.tile-val {
  font: 12px 'DM Mono', monospace;
  color: #24352a;
}

.val-buy {
  color: #2b704c;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.val-entry { color: #28382d; }
.val-sl { color: #bb5447; }
.val-tp { color: #2b704c; }
.val-rr { color: #2b704c; font-weight: 700; }
.val-lot { color: #28382d; font-size: 14px; font-weight: 700; }

.tile-sub {
  font-size: 9px;
  color: #79877d;
  font-family: 'DM Mono', monospace;
}

.text-ok { color: #2b704c; }

.lot-tile {
  grid-column: span 3;
  background: #f4f8f3;
  border-color: #cfe0d3;
}

.lot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.risk-pills {
  display: flex;
  align-items: center;
  gap: 4px;
}

.risk-note {
  font: 8px 'DM Mono', monospace;
  color: #718175;
}

.risk-btn {
  border: 1px solid #cfd8cf;
  background: #fff;
  color: #55665b;
  font: 8px 'DM Mono', monospace;
  padding: 2px 6px;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.risk-btn.active {
  background: #2b704c;
  border-color: #2b704c;
  color: #fff;
  font-weight: 700;
}

.lot-calc-info {
  color: #526357;
}

.setup-actions-bar {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #dbe5dc;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.circuit-inline-alert {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fbf0ee;
  border: 1px solid #f2c7c2;
  border-radius: 4px;
  padding: 6px 10px;
  color: #b84a3c;
  font-size: 10px;
}

.actions-buttons-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-action-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #2b704c;
  color: #fff;
  border: 1px solid #235c3e;
  border-radius: 5px;
  padding: 6px 14px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action-primary:hover:not(:disabled) {
  background: #235c3e;
  box-shadow: 0 2px 6px rgba(43, 112, 76, 0.25);
}

.btn-action-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  filter: grayscale(0.5);
}

.btn-action-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f4f7f4;
  color: #3b4e41;
  border: 1px solid #ccd8cf;
  border-radius: 5px;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-action-secondary:hover:not(:disabled) {
  background: #eaf1eb;
  border-color: #b7c8bc;
}

.btn-action-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.setup-action-feedback {
  font-size: 10px;
  padding: 5px 8px;
  border-radius: 4px;
  font-family: 'DM Mono', monospace;
}

.setup-action-feedback.success {
  background: #e9f5ed;
  color: #236841;
  border: 1px solid #c2e2cc;
}

.setup-action-feedback.error {
  background: #fdf0ee;
  color: #ba4739;
  border: 1px solid #f4c9c3;
}

.setup-action-feedback.info {
  background: #eef3f8;
  color: #2b5579;
  border: 1px solid #cde0f1;
}

/* INVALIDATION */
.invalidation-notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  background: #fcf6ee;
  border: 1px solid #f2dfc5;
  border-radius: 5px;
  font-size: 10px;
  line-height: 1.45;
  color: #835c1e;
}

.notice-icon {
  flex-shrink: 0;
  margin-top: 1px;
}

.invalidation-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.inv-item {
  display: grid;
  grid-template-columns: 36px 1fr 100px;
  align-items: center;
  padding: 7px 10px;
  background: #fafcf9;
  border: 1px solid #e6ece4;
  border-radius: 4px;
  gap: 10px;
}

.inv-index {
  display: flex;
  align-items: center;
  gap: 4px;
  font: 9px 'DM Mono', monospace;
  color: #8c4338;
}

.inv-icon {
  color: #c75647;
}

.inv-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.inv-cond {
  font-size: 10px;
  color: #2a382e;
}

.inv-action {
  margin: 0;
  font-size: 9px;
  color: #6d7d71;
}

.inv-status {
  text-align: right;
}

.inv-badge {
  font: 8px 'DM Mono', monospace;
  padding: 2px 6px;
  border-radius: 3px;
  display: inline-block;
}

.badge-safe {
  background: #e9f3ec;
  color: #2b704c;
  border: 1px solid #cce2d4;
}

.badge-wait {
  background: #fbf5ea;
  color: #9c6c19;
  border: 1px solid #f3e0bf;
}

/* RESPONSIVE */
@media (max-width: 900px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
  .scenarios-wrapper {
    grid-template-columns: 1fr;
  }
  .summary-ribbon {
    grid-template-columns: 1fr 1fr;
  }
  .setup-grid {
    grid-template-columns: 1fr 1fr;
  }
  .lot-tile {
    grid-column: span 2;
  }
  .inv-item {
    grid-template-columns: 30px 1fr;
  }
  .inv-status {
    grid-column: span 2;
    text-align: left;
  }
}
</style>
