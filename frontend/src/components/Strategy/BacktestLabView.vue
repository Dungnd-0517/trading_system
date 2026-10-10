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
  DollarSign,
  Layers,
  Play,
  RotateCcw,
  ShieldAlert,
  Sliders,
  TrendingDown,
  TrendingUp,
  XCircle,
} from 'lucide-vue-next'
import { runBacktest } from '../../services/api'

const symbol = ref('XAUUSD')
const riskPct = ref(1.0)
const initialBalance = ref(10000)
const loading = ref(false)
const errorMsg = ref('')
const backtestResult = ref(null)

const summary = computed(() => backtestResult.value?.summary || null)
const trades = computed(() => backtestResult.value?.trades || [])
const equityCurve = computed(() => backtestResult.value?.equity_curve || [])

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

async function executeBacktest() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await runBacktest({
      symbol: symbol.value,
      risk_pct: Number(riskPct.value),
      initial_balance: Number(initialBalance.value),
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
        <div class="header-badge"><Activity :size="14" /> SMC QUANT LAB</div>
        <h1>Backtest & Chiến lược Định lượng SMC</h1>
        <p>Kiểm thử lại quy tắc giao dịch Smart Money Concepts trên tập dữ liệu nến M15/H1 đã nạp trong cơ sở dữ liệu.</p>
      </div>
      <div class="header-controls">
        <div class="control-group">
          <label>TÀI SẢN</label>
          <select v-model="symbol">
            <option value="XAUUSD">XAUUSD (Gold)</option>
          </select>
        </div>
        <div class="control-group">
          <label>RỦI RO / LỆNH</label>
          <select v-model="riskPct">
            <option :value="0.5">0.5% Vốn</option>
            <option :value="1.0">1.0% Vốn (Khuyên dùng)</option>
            <option :value="1.5">1.5% Vốn</option>
            <option :value="2.0">2.0% Vốn</option>
          </select>
        </div>
        <div class="control-group">
          <label>VỐN KHỞI TẠO</label>
          <input type="number" v-model="initialBalance" min="1000" step="1000" />
        </div>
        <button class="run-btn" :disabled="loading" @click="executeBacktest">
          <Play v-if="!loading" :size="14" />
          <RotateCcw v-else class="spin" :size="14" />
          <span>{{ loading ? 'Đang chạy...' : 'Chạy Backtest' }}</span>
        </button>
      </div>
    </header>

    <!-- Error Alert -->
    <div v-if="errorMsg" class="error-banner">
      <ShieldAlert :size="16" />
      <span>{{ errorMsg }}</span>
    </div>

    <!-- Summary Cards -->
    <div v-if="summary" class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">LỢI NHUẬN RÒNG (NET P&L)</div>
        <div class="kpi-val" :class="summary.net_pnl >= 0 ? 'text-green' : 'text-red'">
          {{ summary.net_pnl >= 0 ? '+' : '' }}${{ summary.net_pnl.toLocaleString() }}
        </div>
        <div class="kpi-sub" :class="summary.net_pnl >= 0 ? 'text-green' : 'text-red'">
          {{ summary.net_pnl_percent >= 0 ? '+' : '' }}{{ summary.net_pnl_percent }}% so với vốn ban đầu
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-label">TỶ LỆ THẮNG (WIN RATE)</div>
        <div class="kpi-val text-blue">{{ summary.winrate_percent }}%</div>
        <div class="kpi-sub text-muted">
          {{ summary.win_trades }} Thắng / {{ summary.loss_trades }} Thua (Tổng: {{ summary.total_trades }} lệnh)
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
        <div class="kpi-sub text-muted">-${{ summary.max_drawdown_dollars.toLocaleString() }} từ đỉnh vốn cao nhất</div>
      </div>
    </div>

    <!-- Equity Curve Chart -->
    <section v-if="equityCurve.length" class="chart-section">
      <div class="section-title">
        <BarChart2 :size="15" />
        <h2>Đường cong tăng trưởng vốn (Equity Curve)</h2>
        <span class="equity-final">Vốn cuối kỳ: ${{ summary?.final_balance?.toLocaleString() }}</span>
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
    <section v-if="trades.length" class="table-section">
      <div class="section-title">
        <Layers :size="15" />
        <h2>Nhật ký chi tiết các lệnh Backtest ({{ trades.length }} lệnh)</h2>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>#TRADE</th>
              <th>SIDE</th>
              <th>KHỐI LƯỢNG</th>
              <th>VÀO LỆNH (ENTRY)</th>
              <th>THOÁT (EXIT)</th>
              <th>STOP LOSS</th>
              <th>TAKE PROFIT</th>
              <th>KẾT QUẢ</th>
              <th>LÃI/LỖ (PNL)</th>
              <th>SỐ DƯ SAU LỆNH</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in trades" :key="t.trade_no">
              <td>#{{ t.trade_no }}</td>
              <td :class="t.side.toLowerCase() + '-tag'">{{ t.side }}</td>
              <td>{{ t.lots }}L</td>
              <td>${{ t.entry_price.toFixed(2) }}</td>
              <td>${{ t.exit_price.toFixed(2) }}</td>
              <td>${{ t.stop_loss.toFixed(2) }}</td>
              <td>${{ t.take_profit.toFixed(2) }}</td>
              <td>
                <span :class="t.outcome === 'WIN' ? 'outcome-win' : 'outcome-loss'">
                  {{ t.outcome }}
                </span>
              </td>
              <td :class="t.pnl >= 0 ? 'text-green' : 'text-red'">
                {{ t.pnl >= 0 ? '+' : '' }}${{ t.pnl.toFixed(2) }}
              </td>
              <td class="font-bold">${{ t.balance_after.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.backtest-view { padding: 18px 24px; max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 18px; }
.page-header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 16px; border-bottom: 1px solid #e5e7eb; padding-bottom: 16px; }
.header-badge { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 800; background: #e0f2fe; color: #0284c7; padding: 2px 8px; border-radius: 4px; margin-bottom: 6px; }
h1 { margin: 0; font-size: 20px; font-weight: 800; color: #111827; }
p { margin: 4px 0 0; font-size: 12px; color: #6b7280; }
.header-controls { display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap; }
.control-group { display: flex; flex-direction: column; gap: 4px; }
.control-group label { font-size: 9px; font-weight: 700; color: #6b7280; }
.control-group select, .control-group input { padding: 6px 10px; border-radius: 6px; border: 1px solid #d1d5db; background: #fff; font-size: 12px; color: #111827; outline: none; }
.run-btn { display: inline-flex; align-items: center; gap: 6px; background: #059669; color: #fff; padding: 7px 16px; border-radius: 6px; font-size: 12px; font-weight: 700; border: none; cursor: pointer; transition: all 0.15s; }
.run-btn:hover:not(:disabled) { background: #047857; }
.run-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.error-banner { display: flex; align-items: center; gap: 8px; background: #fee2e2; color: #b91c1c; padding: 10px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
.kpi-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
.kpi-label { font-size: 10px; font-weight: 700; color: #6b7280; letter-spacing: 0.5px; }
.kpi-val { font-size: 22px; font-weight: 900; margin: 4px 0 2px; }
.kpi-sub { font-size: 11px; }

.text-green { color: #10b981; }
.text-red { color: #ef4444; }
.text-blue { color: #2563eb; }
.text-yellow { color: #d97706; }
.text-muted { color: #6b7280; }
.font-bold { font-weight: 700; }

.chart-section, .table-section { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
.section-title { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; border-bottom: 1px solid #f3f4f6; padding-bottom: 8px; }
.section-title h2 { margin: 0; font-size: 13px; font-weight: 800; color: #1f2937; flex: 1; }
.equity-final { font-size: 11px; font-weight: 700; color: #059669; }
.svg-container { width: 100%; height: 180px; background: #fafafa; border-radius: 6px; overflow: hidden; }
.equity-svg { width: 100%; height: 100%; }

.table-scroll { overflow-x: auto; max-height: 400px; }
table { width: 100%; border-collapse: collapse; text-align: left; font-size: 11px; }
th { padding: 8px 10px; font-size: 9px; font-weight: 700; color: #6b7280; background: #f9fafb; border-bottom: 1px solid #e5e7eb; position: sticky; top: 0; }
td { padding: 8px 10px; border-bottom: 1px solid #f3f4f6; color: #1f2937; }
.buy-tag { color: #10b981; font-weight: 800; }
.sell-tag { color: #ef4444; font-weight: 800; }
.outcome-win { background: #d1fae5; color: #065f46; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px; }
.outcome-loss { background: #fee2e2; color: #991b1b; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 4px; }
</style>
