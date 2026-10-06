<script setup>
import { computed, ref } from 'vue'
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  Clock,
  Copy,
  DollarSign,
  Filter,
  History,
  RotateCcw,
  Search,
  ShieldCheck,
  Target,
  TrendingDown,
  TrendingUp,
} from 'lucide-vue-next'

const props = defineProps({
  orders: {
    type: Array,
    default: () => [],
  },
})

const searchQuery = ref('')
const selectedStatus = ref('ALL')
const selectedSide = ref('ALL')
const selectedReason = ref('ALL')
const sortBy = ref('time_desc')
const copiedId = ref(null)

// Summary calculations
const closedOrders = computed(() => props.orders.filter((o) => o.status === 'CLOSED'))
const openOrders = computed(() => props.orders.filter((o) => ['OPEN', 'FILLED', 'PENDING'].includes(o.status)))

const totalRealizedPnl = computed(() =>
  closedOrders.value.reduce((acc, o) => acc + (Number(o.realized_pnl) || 0), 0)
)

const winningOrders = computed(() =>
  closedOrders.value.filter((o) => (Number(o.realized_pnl) || 0) > 0)
)
const losingOrders = computed(() =>
  closedOrders.value.filter((o) => (Number(o.realized_pnl) || 0) < 0)
)

const winRate = computed(() => {
  if (!closedOrders.value.length) return null
  return Math.round((winningOrders.value.length / closedOrders.value.length) * 1000) / 10
})

const totalGains = computed(() =>
  winningOrders.value.reduce((acc, o) => acc + (Number(o.realized_pnl) || 0), 0)
)
const totalLosses = computed(() =>
  Math.abs(losingOrders.value.reduce((acc, o) => acc + (Number(o.realized_pnl) || 0), 0))
)
const profitFactor = computed(() => {
  if (totalLosses.value === 0) return totalGains.value > 0 ? '∞' : '0.00'
  return (totalGains.value / totalLosses.value).toFixed(2)
})

const avgPnl = computed(() => {
  if (!closedOrders.value.length) return 0
  return totalRealizedPnl.value / closedOrders.value.length
})

// Filtering & sorting
const filteredOrders = computed(() => {
  return props.orders
    .filter((order) => {
      // Status filter
      if (selectedStatus.value !== 'ALL') {
        if (selectedStatus.value === 'OPEN' && !['OPEN', 'FILLED', 'PENDING'].includes(order.status)) return false
        if (selectedStatus.value === 'CLOSED' && order.status !== 'CLOSED') return false
      }

      // Side filter
      if (selectedSide.value !== 'ALL' && order.order_type !== selectedSide.value) return false

      // Reason filter
      if (selectedReason.value !== 'ALL' && order.close_reason !== selectedReason.value) return false

      // Search query (id, uuid, symbol, trigger)
      if (searchQuery.value.trim()) {
        const q = searchQuery.value.trim().toLowerCase()
        const matchId = String(order.id).includes(q)
        const matchUuid = (order.ticket_uuid || '').toLowerCase().includes(q)
        const matchSymbol = (order.symbol || '').toLowerCase().includes(q)
        const matchTrigger = (order.strategy_trigger || '').toLowerCase().includes(q)
        if (!matchId && !matchUuid && !matchSymbol && !matchTrigger) return false
      }

      return true
    })
    .sort((a, b) => {
      if (sortBy.value === 'time_desc') {
        return new Date(b.open_time || 0) - new Date(a.open_time || 0)
      }
      if (sortBy.value === 'time_asc') {
        return new Date(a.open_time || 0) - new Date(b.open_time || 0)
      }
      if (sortBy.value === 'pnl_desc') {
        return (b.realized_pnl || 0) - (a.realized_pnl || 0)
      }
      if (sortBy.value === 'pnl_asc') {
        return (a.realized_pnl || 0) - (b.realized_pnl || 0)
      }
      if (sortBy.value === 'size_desc') {
        return (b.lot_size || 0) - (a.lot_size || 0)
      }
      return 0
    })
})

function resetFilters() {
  searchQuery.value = ''
  selectedStatus.value = 'ALL'
  selectedSide.value = 'ALL'
  selectedReason.value = 'ALL'
  sortBy.value = 'time_desc'
}

function copyTicket(ticket) {
  if (!navigator?.clipboard) return
  navigator.clipboard.writeText(ticket)
  copiedId.value = ticket
  setTimeout(() => {
    if (copiedId.value === ticket) copiedId.value = null
  }, 2000)
}

function formatDuration(open, close) {
  if (!open || !close) return '--'
  const diffSec = Math.max(0, Math.floor((new Date(close) - new Date(open)) / 1000))
  if (diffSec < 60) return `${diffSec}s`
  const min = Math.floor(diffSec / 60)
  const sec = diffSec % 60
  if (min < 60) return `${min}m ${sec}s`
  const hours = Math.floor(min / 60)
  return `${hours}h ${min % 60}m`
}

function formatDateTime(iso) {
  if (!iso) return '--'
  const d = new Date(iso)
  return d.toLocaleString('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour12: false,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function calculatePnlPct(order) {
  if (order.pnl_percentage !== null && order.pnl_percentage !== undefined) {
    return Number(order.pnl_percentage)
  }
  if (order.exit_price && order.entry_price) {
    const mult = order.order_type === 'BUY' ? 1 : -1
    return Number((((order.exit_price - order.entry_price) / order.entry_price) * 100 * mult).toFixed(2))
  }
  return null
}
</script>

<template>
  <div class="orders-history-container">
    <!-- Header title -->
    <div class="view-header">
      <div class="header-left">
        <span class="icon-chip"><History :size="18" /></span>
        <div>
          <h2>Orders History &amp; Trade Analytics</h2>
          <p>Lịch sử khớp lệnh và phân tích hiệu suất thực tế từ cơ sở dữ liệu mô phỏng</p>
        </div>
      </div>
      <div class="header-badge">
        <span>TOTAL RECORDED: <b>{{ orders.length }} ORDERS</b></span>
      </div>
    </div>

    <!-- Metrics Cards Overview -->
    <section class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon winrate"><Target :size="18" /></div>
        <div class="kpi-info">
          <span class="kpi-label">WIN RATE</span>
          <span class="kpi-value highlight">{{ winRate !== null ? `${winRate}%` : '—' }}</span>
          <small class="kpi-sub">{{ winningOrders.length }} Wins / {{ losingOrders.length }} Losses</small>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon pnl"><DollarSign :size="18" /></div>
        <div class="kpi-info">
          <span class="kpi-label">TOTAL REALIZED P&amp;L</span>
          <span :class="['kpi-value', totalRealizedPnl >= 0 ? 'text-profit' : 'text-loss']">
            {{ totalRealizedPnl >= 0 ? '+' : '' }}${{ totalRealizedPnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </span>
          <small class="kpi-sub">Avg ${{ avgPnl.toFixed(2) }} / trade</small>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon factor"><TrendingUp :size="18" /></div>
        <div class="kpi-info">
          <span class="kpi-label">PROFIT FACTOR</span>
          <span class="kpi-value">{{ profitFactor }}</span>
          <small class="kpi-sub">${{ totalGains.toFixed(0) }} gains vs ${{ totalLosses.toFixed(0) }} losses</small>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon trades"><ShieldCheck :size="18" /></div>
        <div class="kpi-info">
          <span class="kpi-label">CLOSED TRADES</span>
          <span class="kpi-value">{{ closedOrders.length }}</span>
          <small class="kpi-sub">{{ openOrders.length }} Open Position(s)</small>
        </div>
      </div>
    </section>

    <!-- Filter and Control Bar -->
    <section class="filter-toolbar">
      <div class="search-box">
        <Search :size="15" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Tìm theo Ticket #, UUID, Symbol..."
        />
        <button v-if="searchQuery" class="clear-search" @click="searchQuery = ''">×</button>
      </div>

      <div class="filter-group">
        <span class="filter-label"><Filter :size="13" /> Status:</span>
        <div class="segmented-control">
          <button :class="{ active: selectedStatus === 'ALL' }" @click="selectedStatus = 'ALL'">Tất cả</button>
          <button :class="{ active: selectedStatus === 'CLOSED' }" @click="selectedStatus = 'CLOSED'">Đã đóng ({{ closedOrders.length }})</button>
          <button :class="{ active: selectedStatus === 'OPEN' }" @click="selectedStatus = 'OPEN'">Mở ({{ openOrders.length }})</button>
        </div>
      </div>

      <div class="filter-group">
        <span class="filter-label">Side:</span>
        <div class="segmented-control">
          <button :class="{ active: selectedSide === 'ALL' }" @click="selectedSide = 'ALL'">All</button>
          <button :class="{ active: selectedSide === 'BUY' }" @click="selectedSide = 'BUY'">BUY</button>
          <button :class="{ active: selectedSide === 'SELL' }" @click="selectedSide = 'SELL'">SELL</button>
        </div>
      </div>

      <div class="filter-group">
        <span class="filter-label">Lý do đóng:</span>
        <select v-model="selectedReason" class="select-dropdown">
          <option value="ALL">Tất cả lý do</option>
          <option value="TP_HIT">TP Hit (Take Profit)</option>
          <option value="SL_HIT">SL Hit (Stop Loss)</option>
          <option value="MANUAL_CLOSE">Manual Close</option>
        </select>
      </div>

      <div class="filter-group sort-group">
        <span class="filter-label">Sắp xếp:</span>
        <select v-model="sortBy" class="select-dropdown">
          <option value="time_desc">Mới nhất trước</option>
          <option value="time_asc">Cũ nhất trước</option>
          <option value="pnl_desc">PnL cao nhất</option>
          <option value="pnl_asc">PnL thấp nhất</option>
          <option value="size_desc">Khối lượng lớn nhất</option>
        </select>
      </div>

      <button
        v-if="searchQuery || selectedStatus !== 'ALL' || selectedSide !== 'ALL' || selectedReason !== 'ALL' || sortBy !== 'time_desc'"
        class="reset-btn"
        @click="resetFilters"
        title="Đặt lại bộ lọc"
      >
        <RotateCcw :size="13" /> Reset
      </button>
    </section>

    <!-- Orders Table -->
    <div class="table-wrapper">
      <table class="orders-table">
        <thead>
          <tr>
            <th>TICKET</th>
            <th>THỜI GIAN (ICT)</th>
            <th>ASSET</th>
            <th>SIDE</th>
            <th>LOT SIZE</th>
            <th>ENTRY</th>
            <th>EXIT</th>
            <th>SL / TP</th>
            <th>REALIZED P&amp;L</th>
            <th>LỜI/LỖ (%)</th>
            <th>LÝ DO ĐÓNG</th>
            <th>THỜI LƯỢNG</th>
            <th>STATUS</th>
          </tr>
        </thead>
        <tbody v-if="filteredOrders.length">
          <tr v-for="order in filteredOrders" :key="order.id" :class="`row-${order.status.toLowerCase()}`">
            <!-- Ticket -->
            <td class="col-ticket">
              <div class="ticket-cell">
                <span class="ticket-id">#{{ order.id }}</span>
                <button
                  v-if="order.ticket_uuid"
                  class="copy-btn"
                  :title="order.ticket_uuid"
                  @click="copyTicket(order.ticket_uuid)"
                >
                  <Check v-if="copiedId === order.ticket_uuid" :size="12" class="text-green" />
                  <Copy v-else :size="12" />
                </button>
              </div>
            </td>

            <!-- Time -->
            <td class="col-time">
              <div class="time-cell">
                <span class="open-time">{{ formatDateTime(order.open_time) }}</span>
                <small v-if="order.close_time" class="close-time">Đóng: {{ formatDateTime(order.close_time) }}</small>
              </div>
            </td>

            <!-- Symbol -->
            <td class="col-symbol">
              <span class="symbol-pill">{{ order.symbol }}</span>
            </td>

            <!-- Side -->
            <td class="col-side">
              <span :class="['side-badge', order.order_type.toLowerCase()]">
                <ArrowUpRight v-if="order.order_type === 'BUY'" :size="12" />
                <ArrowDownRight v-else :size="12" />
                {{ order.order_type }}
              </span>
            </td>

            <!-- Lot Size -->
            <td class="col-size">
              <span class="mono-value">{{ Number(order.lot_size).toFixed(2) }} lots</span>
            </td>

            <!-- Entry Price -->
            <td class="col-price">
              <span class="mono-value">${{ Number(order.entry_price).toFixed(2) }}</span>
            </td>

            <!-- Exit Price -->
            <td class="col-price">
              <span v-if="order.exit_price" class="mono-value">${{ Number(order.exit_price).toFixed(2) }}</span>
              <span v-else class="text-muted">—</span>
            </td>

            <!-- SL / TP -->
            <td class="col-sltp">
              <div class="sltp-cell">
                <span class="sl-val">SL: {{ Number(order.stop_loss).toFixed(2) }}</span>
                <span class="tp-val">TP: {{ Number(order.take_profit).toFixed(2) }}</span>
              </div>
            </td>

            <!-- Realized PnL -->
            <td class="col-pnl">
              <div v-if="order.realized_pnl !== null" :class="['pnl-pill', Number(order.realized_pnl) >= 0 ? 'pnl-pos' : 'pnl-neg']">
                {{ Number(order.realized_pnl) >= 0 ? '+' : '' }}${{ Number(order.realized_pnl).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </div>
              <span v-else class="text-muted">—</span>
            </td>

            <!-- PnL % -->
            <td class="col-pct">
              <div v-if="calculatePnlPct(order) !== null" :class="['pct-pill', calculatePnlPct(order) >= 0 ? 'pct-pos' : 'pct-neg']">
                {{ calculatePnlPct(order) >= 0 ? '+' : '' }}{{ calculatePnlPct(order) }}%
              </div>
              <span v-else class="text-muted">—</span>
            </td>

            <!-- Close reason -->
            <td class="col-reason">
              <span v-if="order.close_reason" :class="['reason-tag', `reason-${order.close_reason.toLowerCase().replace('_', '-')}`]">
                {{ order.close_reason === 'TP_HIT' ? 'Take Profit' : order.close_reason === 'SL_HIT' ? 'Stop Loss' : order.close_reason === 'MANUAL_CLOSE' ? 'Manual Close' : order.close_reason }}
              </span>
              <span v-else class="text-muted">—</span>
            </td>

            <!-- Duration -->
            <td class="col-duration">
              <span class="duration-text">
                <Clock :size="11" />
                {{ formatDuration(order.open_time, order.close_time) }}
              </span>
            </td>

            <!-- Status -->
            <td class="col-status">
              <span :class="['status-badge', `status-${order.status.toLowerCase()}`]">
                {{ order.status }}
              </span>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr>
            <td colspan="13" class="empty-state">
              <div class="empty-content">
                <History :size="34" class="empty-icon" />
                <h4>Không tìm thấy lệnh nào khớp</h4>
                <p>Thử xóa bộ lọc hoặc tìm kiếm theo từ khóa khác</p>
                <button class="reset-btn empty-reset" @click="resetFilters">Xóa bộ lọc</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Table Footer / Count Info -->
    <div class="table-foot">
      <span>Đang hiển thị {{ filteredOrders.length }} / {{ orders.length }} lệnh từ hệ thống</span>
      <span class="foot-note">Hợp đồng chuẩn: 1 Lot XAUUSD = 100 oz troy · Dữ liệu mô phỏng chính xác</span>
    </div>
  </div>
</template>

<style scoped>
.orders-history-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px 0 24px;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 6px;
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

.header-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #e4ebe2;
  border: 1px solid #d0dbce;
  border-radius: 6px;
  font: 10px 'DM Mono', monospace;
  color: #225c43;
}

/* KPI Cards */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  background: #f8faf6;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  box-shadow: 0 1px 2px #00000008;
}

.kpi-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: #e8efe6;
  color: #225c43;
}

.kpi-icon.winrate { background: #e2f2e5; color: #2e7a52; }
.kpi-icon.pnl { background: #dff0e6; color: #1e6c46; }
.kpi-icon.factor { background: #f5eedb; color: #9c7324; }
.kpi-icon.trades { background: #e5eceb; color: #3b6b66; }

.kpi-info {
  display: flex;
  flex-direction: column;
}

.kpi-label {
  font: 9px 'DM Mono', monospace;
  color: #798a80;
  letter-spacing: 0.04em;
}

.kpi-value {
  font: 18px 'DM Mono', monospace;
  font-weight: 700;
  color: #1b2a23;
  line-height: 1.25;
}

.kpi-value.text-profit { color: #237b4b; }
.kpi-value.text-loss { color: #bb4739; }

.kpi-sub {
  font-size: 10px;
  color: #84948a;
  margin-top: 2px;
}

/* Filter Toolbar */
.filter-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #f4f7f2;
  border: 1px solid #d9e2da;
  border-radius: 7px;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 1px solid #ccd8cd;
  border-radius: 5px;
  padding: 0 9px;
  min-width: 230px;
}

.search-box svg {
  color: #7d8f84;
}

.search-box input {
  border: none;
  background: transparent;
  padding: 7px 6px;
  font-size: 12px;
  color: #1b2a23;
  width: 100%;
  outline: none;
}

.clear-search {
  border: none;
  background: transparent;
  font-size: 14px;
  color: #809087;
  cursor: pointer;
  padding: 0 4px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font: 10px 'DM Mono', monospace;
  color: #67786f;
  display: flex;
  align-items: center;
  gap: 4px;
}

.segmented-control {
  display: flex;
  background: #e2e8e0;
  border-radius: 5px;
  padding: 2px;
}

.segmented-control button {
  border: none;
  background: transparent;
  padding: 4px 9px;
  font-size: 11px;
  color: #55665d;
  border-radius: 4px;
  font-weight: 500;
  transition: all 0.15s ease;
}

.segmented-control button.active {
  background: #ffffff;
  color: #225c43;
  font-weight: 700;
  box-shadow: 0 1px 3px #00000015;
}

.select-dropdown {
  background: #ffffff;
  border: 1px solid #ccd8cd;
  border-radius: 5px;
  padding: 5px 8px;
  font-size: 11px;
  color: #2b3b32;
  outline: none;
  cursor: pointer;
}

.reset-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-left: auto;
  border: 1px solid #d2ded0;
  background: #ffffff;
  color: #63776c;
  padding: 5px 10px;
  border-radius: 5px;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s;
}

.reset-btn:hover {
  background: #e5ece3;
  color: #225c43;
}

/* Table */
.table-wrapper {
  overflow-x: auto;
  background: #ffffff;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  box-shadow: 0 1px 3px #00000008;
}

.orders-table {
  width: 100%;
  border-collapse: collapse;
  white-space: nowrap;
  font-size: 12px;
  text-align: left;
}

.orders-table thead {
  background: #eef3ec;
  border-bottom: 1px solid #d0dbce;
}

.orders-table th {
  padding: 9px 12px;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  color: #617368;
  letter-spacing: 0.03em;
}

.orders-table tbody tr {
  border-bottom: 1px solid #edf1eb;
  transition: background 0.15s ease;
}

.orders-table tbody tr:hover {
  background: #f7faf5;
}

.orders-table tbody tr:last-child {
  border-bottom: none;
}

.orders-table td {
  padding: 10px 12px;
  color: #25362d;
}

.ticket-cell {
  display: flex;
  align-items: center;
  gap: 5px;
}

.ticket-id {
  font: 11px 'DM Mono', monospace;
  font-weight: 700;
  color: #1b2a23;
}

.copy-btn {
  border: none;
  background: transparent;
  color: #8c9c92;
  cursor: pointer;
  padding: 2px;
  border-radius: 3px;
  display: grid;
  place-items: center;
}

.copy-btn:hover {
  color: #225c43;
  background: #e3ebe1;
}

.text-green {
  color: #2e7a52;
}

.time-cell {
  display: flex;
  flex-direction: column;
}

.open-time {
  font: 11px 'DM Mono', monospace;
  color: #2a3c31;
}

.close-time {
  font: 9px 'DM Mono', monospace;
  color: #839389;
}

.symbol-pill {
  display: inline-block;
  padding: 2px 6px;
  background: #fcf4dd;
  border: 1px solid #ebd8a0;
  color: #8f6f1c;
  border-radius: 4px;
  font: 10px 'DM Mono', monospace;
  font-weight: 700;
}

.side-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  border-radius: 4px;
  font: 10px 'DM Mono', monospace;
  font-weight: 700;
}

.side-badge.buy {
  background: #e4f4e7;
  color: #1e7043;
  border: 1px solid #c2e5c8;
}

.side-badge.sell {
  background: #fde8e5;
  color: #b83d30;
  border: 1px solid #f6c0ba;
}

.mono-value {
  font: 11px 'DM Mono', monospace;
  color: #25362d;
}

.sltp-cell {
  display: flex;
  flex-direction: column;
  gap: 1px;
  font: 10px 'DM Mono', monospace;
}

.sl-val { color: #b84337; }
.tp-val { color: #237b4b; }

.pnl-pill {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  font: 11px 'DM Mono', monospace;
  font-weight: 700;
}

.pnl-pos {
  background: #e4f4e7;
  color: #1e7043;
}

.pnl-neg {
  background: #fde8e5;
  color: #b83d30;
}

.pct-pill {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  font: 10px 'DM Mono', monospace;
  font-weight: 600;
}

.pct-pos {
  background: #ebf6ec;
  color: #27794b;
}

.pct-neg {
  background: #faeceb;
  color: #bd4538;
}

.reason-tag {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font: 10px 'DM Mono', monospace;
  font-weight: 600;
}

.reason-tp-hit {
  background: #daf0df;
  color: #1a6d3f;
  border: 1px solid #b7e3bf;
}

.reason-sl-hit {
  background: #fce1de;
  color: #b5382b;
  border: 1px solid #f5bdb6;
}

.reason-manual-close {
  background: #e8ecf1;
  color: #3b5874;
  border: 1px solid #cbd6e2;
}

.duration-text {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: 10px 'DM Mono', monospace;
  color: #6b7c71;
}

.status-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
}

.status-closed {
  background: #e5ece6;
  color: #4b5d52;
}

.status-filled, .status-open {
  background: #d4ebd7;
  color: #1e6d42;
}

.empty-state {
  padding: 48px 16px !important;
  text-align: center;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.empty-icon {
  color: #a4b4a9;
}

.empty-content h4 {
  margin: 0;
  font-size: 14px;
  color: #314238;
}

.empty-content p {
  margin: 0;
  font-size: 12px;
  color: #798b80;
}

.empty-reset {
  margin-top: 6px;
}

.table-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 6px;
  font: 10px 'DM Mono', monospace;
  color: #7d8e83;
}

.foot-note {
  color: #9aa89f;
}

@media (max-width: 1050px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 760px) {
  .view-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .kpi-grid {
    grid-template-columns: 1fr;
  }
  .table-foot {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>
