<script setup>
import { computed, ref, onMounted } from 'vue'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart2,
  Calendar,
  CheckCircle,
  Clock,
  Compass,
  Cpu,
  DollarSign,
  Filter,
  Layers,
  Lock,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  TrendingDown,
  TrendingUp,
  Unlock,
  XCircle,
  Zap,
} from 'lucide-vue-next'
import { runBacktest } from '../../services/api'

// Parameters
const symbol = ref('XAUUSD')
const timeframe = ref('M15')
const barsCount = ref(500)
const initialBalance = ref(10000)
const riskPct = ref(1.0)
const sizingMode = ref('FIXED') // 'FIXED' | 'COMPOUND'
const atrPeriod = ref(14)
const atrSlMultiplier = ref(1.5)
const riskRewardRatio = ref(2.0)
const enableBreakeven = ref(true)
const enablePartialTp = ref(false)
const sessionFilter = ref('ALL') // 'ALL' | 'KILL_ZONES_ONLY'

const showAdvanced = ref(false)
const tradeFilter = ref('ALL') // 'ALL' | 'WIN' | 'LOSS' | 'BREAKEVEN'

const loading = ref(false)
const errorMsg = ref('')
const backtestResult = ref(null)

const summary = computed(() => backtestResult.value?.summary || null)
const testSpecs = computed(() => backtestResult.value?.test_specs || null)
const allTrades = computed(() => backtestResult.value?.trades || [])
const equityCurve = computed(() => backtestResult.value?.equity_curve || [])

const filteredTrades = computed(() => {
  if (tradeFilter.value === 'ALL') return allTrades.value
  return allTrades.value.filter((t) => t.outcome === tradeFilter.value)
})

// Tính toán điểm vẽ biểu đồ SVG Equity Curve
const svgPoints = computed(() => {
  if (!equityCurve.value.length) return ''
  const balances = equityCurve.value.map((p) => p.balance)
  const minB = Math.min(...balances) * 0.99
  const maxB = Math.max(...balances) * 1.01
  const range = maxB - minB || 1

  const width = 800
  const height = 180
  const n = equityCurve.value.length

  return equityCurve.value
    .map((p, idx) => {
      const x = ((idx / (n - 1 || 1)) * (width - 40) + 20).toFixed(1)
      const y = (height - 20 - ((p.balance - minB) / range) * (height - 40)).toFixed(1)
      return `${x},${y}`
    })
    .join(' ')
})

function formatDateTime(isoStr) {
  if (!isoStr) return '--'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('vi-VN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return isoStr
  }
}

function formatFullDate(isoStr) {
  if (!isoStr) return '--'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return isoStr
  }
}

async function executeBacktest() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await runBacktest({
      symbol: symbol.value,
      timeframe: timeframe.value,
      bars_count: Number(barsCount.value),
      initial_balance: Number(initialBalance.value),
      risk_pct: Number(riskPct.value),
      sizing_mode: sizingMode.value,
      atr_period: Number(atrPeriod.value),
      atr_sl_multiplier: Number(atrSlMultiplier.value),
      risk_reward_ratio: Number(riskRewardRatio.value),
      enable_breakeven: Boolean(enableBreakeven.value),
      enable_partial_tp: Boolean(enablePartialTp.value),
      session_filter: sessionFilter.value,
    })
    backtestResult.value = res
  } catch (err) {
    errorMsg.value = `Lỗi thực hiện backtest: ${err.message}`
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  executeBacktest()
})
</script>

<template>
  <div class="backtest-view">
    <!-- Header -->
    <header class="page-header">
      <div class="header-left">
        <div class="header-badge"><Activity :size="14" /> SMC QUANT LAB &middot; PHASE 03</div>
        <h1>Backtest &amp; Kiểm Thử Chiến Lược Định Lượng</h1>
        <p>Thực thi mô phỏng chiến lược SMC trên chuỗi nến lịch sử đa khung thời gian với cơ chế quản trị rủi ro và lot size chuẩn xác 100%.</p>
      </div>

      <!-- Quick Action Controls -->
      <div class="header-actions">
        <button class="adv-toggle-btn" :class="{ active: showAdvanced }" @click="showAdvanced = !showAdvanced">
          <Sliders :size="13" />
          <span>{{ showAdvanced ? 'Thu gọn tham số' : 'Mở rộng tham số nâng cao' }}</span>
        </button>

        <button class="run-btn" :disabled="loading" @click="executeBacktest">
          <Play v-if="!loading" :size="14" />
          <RotateCcw v-else class="spin" :size="14" />
          <span>{{ loading ? 'Đang chạy mô phỏng...' : 'Chạy Backtest ⚡' }}</span>
        </button>
      </div>
    </header>

    <!-- Parameter Config Console -->
    <section class="config-console">
      <!-- Row 1: Primary Parameters -->
      <div class="config-row primary-row">
        <div class="control-item">
          <label>TÀI SẢN</label>
          <select v-model="symbol">
            <option value="XAUUSD">XAUUSD (Gold / USD)</option>
          </select>
        </div>

        <div class="control-item">
          <label>KHUNG THỜI GIAN</label>
          <select v-model="timeframe">
            <option value="M1">M1 (1 Phút)</option>
            <option value="M5">M5 (5 Phút)</option>
            <option value="M15">M15 (15 Phút - Tiêu chuẩn)</option>
            <option value="H1">H1 (1 Giờ)</option>
            <option value="H4">H4 (4 Giờ)</option>
            <option value="D1">D1 (1 Ngày)</option>
          </select>
        </div>

        <div class="control-item">
          <label>SỐ LƯỢNG NẾN TEST</label>
          <select v-model.number="barsCount">
            <option :value="100">100 nến gần nhất</option>
            <option :value="300">300 nến</option>
            <option :value="500">500 nến (Khuyên dùng)</option>
            <option :value="1000">1,000 nến</option>
            <option :value="2000">2,000 nến</option>
          </select>
        </div>

        <div class="control-item">
          <label>VỐN KHỞI TẠO ($)</label>
          <input type="number" v-model.number="initialBalance" min="500" step="1000" />
        </div>

        <div class="control-item">
          <label>RỦI RO / LỆNH</label>
          <select v-model.number="riskPct">
            <option :value="0.25">0.25% Vốn (Bảo thủ)</option>
            <option :value="0.5">0.5% Vốn</option>
            <option :value="1.0">1.0% Vốn (Chuẩn mực)</option>
            <option :value="1.5">1.5% Vốn (Giới hạn tối đa)</option>
            <option :value="2.0">2.0% Vốn (Cao)</option>
          </select>
        </div>
      </div>

      <!-- Row 2: Advanced Parameters (Collapsible) -->
      <div v-if="showAdvanced" class="config-row advanced-row">
        <div class="control-item">
          <label>CƠ CHẾ TÍNH LOT SIZE</label>
          <select v-model="sizingMode">
            <option value="FIXED">Cố định (% vốn ban đầu: ${{ ((initialBalance * riskPct) / 100).toFixed(0) }}/lệnh)</option>
            <option value="COMPOUND">Lũy kế (% vốn hiện tại - Compound)</option>
          </select>
        </div>

        <div class="control-item">
          <label>ATR SL MULTIPLIER</label>
          <select v-model.number="atrSlMultiplier">
            <option :value="1.0">1.0x ATR (Chặt)</option>
            <option :value="1.2">1.2x ATR</option>
            <option :value="1.5">1.5x ATR (Mặc định)</option>
            <option :value="1.8">1.8x ATR (Reflexion nới rộng)</option>
            <option :value="2.0">2.0x ATR (Tin tức / Biến động cao)</option>
          </select>
        </div>

        <div class="control-item">
          <label>MỤC TIÊU RISK : REWARD</label>
          <select v-model.number="riskRewardRatio">
            <option :value="1.5">1 : 1.5</option>
            <option :value="2.0">1 : 2.0 (Khuyên dùng)</option>
            <option :value="2.5">1 : 2.5</option>
            <option :value="3.0">1 : 3.0</option>
          </select>
        </div>

        <div class="control-item">
          <label>BỘ LỌC PHIÊN GIAO DỊCH</label>
          <select v-model="sessionFilter">
            <option value="ALL">Tất cả các phiên (24/7)</option>
            <option value="KILL_ZONES_ONLY">Chỉ Kill Zones (London &amp; NY AM)</option>
          </select>
        </div>

        <div class="control-item checkbox-item">
          <label>DỜI SL HÒA VỐN (BE)</label>
          <button
            type="button"
            class="toggle-switch-btn"
            :class="{ active: enableBreakeven }"
            @click="enableBreakeven = !enableBreakeven"
          >
            <component :is="enableBreakeven ? Unlock : Lock" :size="12" />
            <span>{{ enableBreakeven ? 'BẬT (Khi đạt 1.5R)' : 'TẮT' }}</span>
          </button>
        </div>

        <div class="control-item checkbox-item">
          <label>CHỐT LỜI TỪNG PHẦN (TP1)</label>
          <button
            type="button"
            class="toggle-switch-btn"
            :class="{ active: enablePartialTp }"
            @click="enablePartialTp = !enablePartialTp"
          >
            <component :is="enablePartialTp ? Unlock : Lock" :size="12" />
            <span>{{ enablePartialTp ? 'BẬT (Chốt 50% tại 1.5R)' : 'TẮT' }}</span>
          </button>
        </div>
      </div>
    </section>

    <!-- Error Alert -->
    <div v-if="errorMsg" class="error-banner">
      <ShieldAlert :size="16" />
      <span>{{ errorMsg }}</span>
    </div>

    <!-- Test Specs Banner (Hiển thị chi tiết tham số test) -->
    <section v-if="testSpecs" class="specs-banner">
      <div class="specs-col">
        <div class="specs-title"><Calendar :size="12" /> THỜI GIAN DỮ LIỆU TEST</div>
        <div class="specs-value">
          <strong>{{ formatFullDate(testSpecs.start_candle_time) }}</strong>
          <span class="specs-arrow">&rarr;</span>
          <strong>{{ formatFullDate(testSpecs.end_candle_time) }}</strong>
        </div>
        <small class="specs-sub">Thời lượng chuỗi nến: {{ testSpecs.duration_str }}</small>
      </div>

      <div class="specs-col">
        <div class="specs-title"><Clock :size="12" /> KHUNG THỜI GIAN &amp; SỐ NẾN</div>
        <div class="specs-value">
          <span class="tf-badge">{{ testSpecs.timeframe }}</span>
          <strong>{{ testSpecs.bars_tested }} nến</strong>
          <small v-if="testSpecs.bars_requested !== testSpecs.bars_tested" class="text-muted">
            (yêu cầu {{ testSpecs.bars_requested }})
          </small>
        </div>
        <small class="specs-sub">ATR chu kỳ {{ testSpecs.atr_period }} nến</small>
      </div>

      <div class="specs-col">
        <div class="specs-title"><DollarSign :size="12" /> QUẢN TRỊ RỦI RO &amp; VỐN</div>
        <div class="specs-value">
          <strong>{{ testSpecs.risk_pct }}% vốn / lệnh</strong>
          <span class="sizing-chip">{{ testSpecs.sizing_mode === 'FIXED' ? 'Cố định' : 'Lũy kế' }}</span>
        </div>
        <small class="specs-sub">
          Rủi ro ban đầu: ${{ ((testSpecs.initial_balance * testSpecs.risk_pct) / 100).toFixed(2) }} / lệnh
        </small>
      </div>

      <div class="specs-col">
        <div class="specs-title"><Sliders :size="12" /> CẤU HÌNH SMC CHIẾN LƯỢC</div>
        <div class="specs-value">
          <strong>SL: {{ testSpecs.atr_sl_multiplier }}x ATR &middot; TP: 1:{{ testSpecs.risk_reward_ratio }}</strong>
        </div>
        <small class="specs-sub">
          BE: {{ testSpecs.enable_breakeven ? 'Bật (1.5R)' : 'Tắt' }} &middot;
          TP1: {{ testSpecs.enable_partial_tp ? 'Bật (50%)' : 'Tắt' }}
        </small>
      </div>
    </section>

    <!-- KPI Summary Cards -->
    <div v-if="summary" class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">LỢI NHUẬN RÒNG (NET P&amp;L)</div>
        <div class="kpi-val" :class="summary.net_pnl >= 0 ? 'text-green' : 'text-red'">
          {{ summary.net_pnl >= 0 ? '+' : '' }}${{ summary.net_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
        </div>
        <div class="kpi-sub" :class="summary.net_pnl >= 0 ? 'text-green' : 'text-red'">
          {{ summary.net_pnl_percent >= 0 ? '+' : '' }}{{ summary.net_pnl_percent }}% so với vốn ban đầu
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">TỶ LỆ THẮNG (WIN RATE)</div>
        <div class="kpi-val text-blue">{{ summary.winrate_percent }}%</div>
        <div class="kpi-sub text-muted">
          {{ summary.win_trades }} Thắng / {{ summary.loss_trades }} Thua / {{ summary.be_trades || 0 }} Hòa
          (Tổng: {{ summary.total_trades }} lệnh)
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">PROFIT FACTOR</div>
        <div class="kpi-val" :class="summary.profit_factor >= 1.5 ? 'text-green' : 'text-yellow'">
          {{ summary.profit_factor }}
        </div>
        <div class="kpi-sub text-muted">Hệ số lãi/lỗ kỳ vọng (Target &ge; 1.5)</div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">MAX DRAWDOWN (SỤT GIẢM TỐI ĐA)</div>
        <div class="kpi-val text-red">-{{ summary.max_drawdown_percent }}%</div>
        <div class="kpi-sub text-muted">-${{ summary.max_drawdown_dollars.toLocaleString('en-US', { minimumFractionDigits: 2 }) }} từ đỉnh vốn</div>
      </div>
    </div>

    <!-- Equity Curve Chart -->
    <section v-if="equityCurve.length" class="chart-section">
      <div class="section-title">
        <BarChart2 :size="15" />
        <h2>Đường cong tăng trưởng vốn (Equity Curve)</h2>
        <span class="equity-final">Vốn cuối kỳ: ${{ summary?.final_balance?.toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</span>
      </div>
      <div class="svg-container">
        <svg viewBox="0 0 800 180" class="equity-svg" preserveAspectRatio="none">
          <defs>
            <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#10b981" stop-opacity="0.3" />
              <stop offset="100%" stop-color="#10b981" stop-opacity="0.0" />
            </linearGradient>
          </defs>
          <!-- Grid lines -->
          <line x1="20" y1="20" x2="780" y2="20" stroke="#e5e7eb" stroke-dasharray="3,3" />
          <line x1="20" y1="90" x2="780" y2="90" stroke="#e5e7eb" stroke-dasharray="3,3" />
          <line x1="20" y1="160" x2="780" y2="160" stroke="#e5e7eb" stroke-dasharray="3,3" />
          <!-- Curve -->
          <polyline :points="svgPoints" fill="none" stroke="#10b981" stroke-width="2.5" />
        </svg>
      </div>
    </section>

    <!-- Trades Table -->
    <section v-if="allTrades.length" class="table-section">
      <div class="section-title">
        <div class="table-title-left">
          <Layers :size="15" />
          <h2>Nhật Ký Chi Tiết Các Lệnh Backtest ({{ filteredTrades.length }} / {{ allTrades.length }} lệnh)</h2>
        </div>

        <!-- Filter tabs for trades -->
        <div class="table-filter-tabs">
          <button
            class="filter-tab-btn"
            :class="{ active: tradeFilter === 'ALL' }"
            @click="tradeFilter = 'ALL'"
          >
            Tất cả ({{ allTrades.length }})
          </button>
          <button
            class="filter-tab-btn"
            :class="{ active: tradeFilter === 'WIN' }"
            @click="tradeFilter = 'WIN'"
          >
            Thắng ({{ summary?.win_trades || 0 }})
          </button>
          <button
            class="filter-tab-btn"
            :class="{ active: tradeFilter === 'LOSS' }"
            @click="tradeFilter = 'LOSS'"
          >
            Thua ({{ summary?.loss_trades || 0 }})
          </button>
          <button
            class="filter-tab-btn"
            :class="{ active: tradeFilter === 'BREAKEVEN' }"
            @click="tradeFilter = 'BREAKEVEN'"
          >
            Hòa vốn ({{ summary?.be_trades || 0 }})
          </button>
        </div>
      </div>

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>#LỆNH</th>
              <th>SIDE</th>
              <th>VÀO LỆNH (ENTRY)</th>
              <th>THOÁT (EXIT)</th>
              <th>THỜI LƯỢNG</th>
              <th>KHỐI LƯỢNG</th>
              <th>RỦI RO DỰ KIẾN</th>
              <th>GIÁ VÀO</th>
              <th>GIÁ THOÁT</th>
              <th>STOP LOSS</th>
              <th>TAKE PROFIT</th>
              <th>R:R</th>
              <th>KẾT QUẢ</th>
              <th>LÃI/LỖ (PNL)</th>
              <th>SỐ DƯ SAU LỆNH</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in filteredTrades" :key="t.trade_no">
              <td><strong>#{{ t.trade_no }}</strong></td>
              <td>
                <span :class="t.side === 'BUY' ? 'side-buy' : 'side-sell'">{{ t.side }}</span>
              </td>
              <td class="font-mono text-muted">{{ formatDateTime(t.entry_time) }}</td>
              <td class="font-mono text-muted">{{ formatDateTime(t.exit_time) }}</td>
              <td class="font-mono text-muted">{{ t.duration_str || `${t.bars_held} bars` }}</td>
              <td class="font-mono font-bold">{{ t.lots }}L</td>
              <td class="font-mono text-muted">${{ Number(t.expected_risk || 100).toFixed(2) }}</td>
              <td class="font-mono">${{ Number(t.entry_price).toFixed(2) }}</td>
              <td class="font-mono">${{ Number(t.exit_price).toFixed(2) }}</td>
              <td class="font-mono text-muted">${{ Number(t.stop_loss).toFixed(2) }}</td>
              <td class="font-mono text-muted">${{ Number(t.take_profit).toFixed(2) }}</td>
              <td>
                <span class="r-badge" :class="t.r_multiple?.startsWith('+') ? 'r-win' : t.r_multiple === '0.0R' ? 'r-be' : 'r-loss'">
                  {{ t.r_multiple }}
                </span>
              </td>
              <td>
                <span
                  class="outcome-badge"
                  :class="t.outcome === 'WIN' ? 'outcome-win' : t.outcome === 'BREAKEVEN' ? 'outcome-be' : 'outcome-loss'"
                >
                  {{ t.outcome }}
                </span>
              </td>
              <td class="font-mono font-bold" :class="t.pnl > 0 ? 'text-green' : t.pnl === 0 ? 'text-muted' : 'text-red'">
                {{ t.pnl > 0 ? '+' : '' }}${{ Number(t.pnl).toFixed(2) }}
              </td>
              <td class="font-mono font-bold">${{ Number(t.balance_after).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.backtest-view {
  padding: 18px 24px;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  border-bottom: 1px solid #d9e0d9;
  padding-bottom: 16px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 800;
  background: #e2ede0;
  color: #225c43;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 6px;
  font-family: 'DM Mono', monospace;
}

h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #1b2a23;
}

p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #637168;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.adv-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f0f4ef;
  color: #3b4e42;
  border: 1px solid #cedcce;
  padding: 7px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}

.adv-toggle-btn:hover {
  background: #e2ece0;
  color: #1b2a23;
}

.adv-toggle-btn.active {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}

.run-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #225c43;
  color: #c9f06b;
  padding: 7px 18px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 800;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}

.run-btn:hover:not(:disabled) {
  background: #184632;
}

.run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Config Console */
.config-console {
  background: #ffffff;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.04);
}

.config-row {
  display: grid;
  gap: 12px;
}

.primary-row {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.advanced-row {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  padding-top: 12px;
  border-top: 1px dashed #e1e7df;
}

.control-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.control-item label {
  font-size: 9px;
  font-weight: 800;
  color: #6d7f73;
  font-family: 'DM Mono', monospace;
  letter-spacing: 0.03em;
}

.control-item select,
.control-item input {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #d0ded0;
  background: #f8faf6;
  font-size: 11px;
  color: #1b2a23;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s;
}

.control-item select:focus,
.control-item input:focus {
  border-color: #225c43;
  background: #ffffff;
}

.toggle-switch-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 31px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid #d0ded0;
  background: #f2f6f1;
  color: #55665b;
  font-size: 10px;
  font-family: 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}

.toggle-switch-btn.active {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}

/* Specs Banner */
.specs-banner {
  background: #f3f7f2;
  border: 1px solid #c8d8c6;
  border-radius: 8px;
  padding: 12px 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.specs-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.specs-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font: 9px 'DM Mono', monospace;
  font-weight: 800;
  color: #4a6352;
}

.specs-value {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #1b2a23;
  flex-wrap: wrap;
}

.specs-arrow {
  color: #8fa093;
  font-weight: bold;
}

.specs-sub {
  font-size: 10px;
  color: #6a7c6f;
  font-family: 'DM Mono', monospace;
}

.tf-badge {
  font: 10px 'DM Mono', monospace;
  font-weight: 800;
  background: #225c43;
  color: #c9f06b;
  padding: 1px 6px;
  border-radius: 3px;
}

.sizing-chip {
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  background: #e2ede0;
  color: #225c43;
  padding: 1px 5px;
  border-radius: 3px;
}

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.04);
}

.kpi-label {
  font-size: 9px;
  font-weight: 800;
  color: #6d7f73;
  font-family: 'DM Mono', monospace;
  letter-spacing: 0.5px;
}

.kpi-val {
  font-size: 22px;
  font-weight: 900;
  font-family: 'DM Mono', monospace;
  margin: 4px 0 2px;
}

.kpi-sub {
  font-size: 10px;
}

.text-green { color: #16a34a; }
.text-red { color: #dc2626; }
.text-blue { color: #2563eb; }
.text-yellow { color: #d97706; }
.text-muted { color: #6b7280; }
.font-bold { font-weight: 800; }
.font-mono { font-family: 'DM Mono', monospace; }

/* Charts & Tables */
.chart-section,
.table-section {
  background: #ffffff;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.04);
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
  border-bottom: 1px solid #eef2ed;
  padding-bottom: 8px;
  flex-wrap: wrap;
}

.table-title-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title h2 {
  margin: 0;
  font-size: 12px;
  font-weight: 800;
  color: #1b2a23;
}

.equity-final {
  font: 11px 'DM Mono', monospace;
  font-weight: 800;
  color: #16a34a;
}

.svg-container {
  width: 100%;
  height: 180px;
  background: #f8faf6;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e6ece5;
}

.equity-svg {
  width: 100%;
  height: 100%;
}

/* Table Filter Tabs */
.table-filter-tabs {
  display: flex;
  gap: 4px;
}

.filter-tab-btn {
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #d5ded6;
  background: #f8faf6;
  color: #55665b;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-tab-btn:hover {
  background: #e2ede0;
}

.filter-tab-btn.active {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}

.table-scroll {
  overflow-x: auto;
  max-height: 480px;
}

table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 11px;
}

th {
  padding: 8px 10px;
  font-size: 9px;
  font-weight: 800;
  color: #617367;
  font-family: 'DM Mono', monospace;
  background: #f4f8f3;
  border-bottom: 1px solid #d9e0d9;
  position: sticky;
  top: 0;
  white-space: nowrap;
}

td {
  padding: 8px 10px;
  border-bottom: 1px solid #edf2ec;
  color: #1b2a23;
  white-space: nowrap;
}

.side-buy {
  color: #16a34a;
  font-weight: 800;
  font-family: 'DM Mono', monospace;
}

.side-sell {
  color: #dc2626;
  font-weight: 800;
  font-family: 'DM Mono', monospace;
}

.r-badge {
  font: 9px 'DM Mono', monospace;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 3px;
}

.r-win { background: #dcfce7; color: #15803d; }
.r-loss { background: #fee2e2; color: #b91c1c; }
.r-be { background: #f3f4f6; color: #4b5563; }

.outcome-badge {
  font: 9px 'DM Mono', monospace;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}

.outcome-win { background: #dcfce7; color: #15803d; }
.outcome-loss { background: #fee2e2; color: #b91c1c; }
.outcome-be { background: #f3f4f6; color: #4b5563; }

.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fee2e2;
  color: #b91c1c;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}
</style>
