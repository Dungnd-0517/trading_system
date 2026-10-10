<script setup>
import { computed, ref } from 'vue'
import { CheckCircle2, ClipboardList, Scissors, ShieldAlert, XCircle } from 'lucide-vue-next'
import { marketStore } from '../../stores/marketStore'
import { orderStore } from '../../stores/orderStore'

const props = defineProps({ orders: { type: Array, default: () => [] } })
const activeOrders = computed(() => props.orders.filter((order) => ['PENDING', 'FILLED', 'OPEN'].includes(order.status)))
const closingMap = ref({})
const partialMap = ref({})

function calculateUnrealizedPnL(order) {
  const current = marketStore.lastPrice
  if (!current || !order.entry_price) return null
  const entry = Number(order.entry_price)
  const lots = Number(order.lot_size)
  const contractSize = 100.0 // 1 lot vàng = 100 oz
  const isBuy = order.order_type === 'BUY'
  const diff = isBuy ? current - entry : entry - current
  return Number((diff * lots * contractSize).toFixed(2))
}

async function handleClose(orderId) {
  closingMap.value[orderId] = true
  try {
    await orderStore.closeOrder(orderId, 'MANUAL_CLOSE')
  } catch (err) {
    alert(`Không thể đóng lệnh #${orderId}: ${err.message}`)
  } finally {
    closingMap.value[orderId] = false
  }
}

async function handlePartialClose(orderId) {
  partialMap.value[orderId] = true
  try {
    await orderStore.partialCloseOrder(orderId, 0.5, 'MANUAL_PARTIAL_TP')
  } catch (err) {
    alert(`Không thể chốt lời 50% lệnh #${orderId}: ${err.message}`)
  } finally {
    partialMap.value[orderId] = false
  }
}
</script>

<template>
  <section class="orders-panel">
    <header>
      <div><ClipboardList :size="15" /><h2>Paper positions</h2></div>
      <div class="header-tags">
        <span v-if="orderStore.circuitBreaker?.active" class="cb-alert-pill">
          <ShieldAlert :size="11" /> CIRCUIT BREAKER
        </span>
        <span class="count-pill">{{ activeOrders.length }} OPEN</span>
      </div>
    </header>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>TICKET</th>
            <th>ASSET</th>
            <th>SIDE</th>
            <th>SIZE</th>
            <th>ENTRY</th>
            <th>STOP</th>
            <th>TARGET</th>
            <th>PROTECTION</th>
            <th>LIVE P&amp;L</th>
            <th>STATUS</th>
            <th>ACTIONS</th>
          </tr>
        </thead>
        <tbody v-if="activeOrders.length">
          <tr v-for="order in activeOrders" :key="order.id">
            <td class="ticket-cell">#{{ order.id }}</td>
            <td class="font-bold">{{ order.symbol }}</td>
            <td :class="order.order_type.toLowerCase() + '-badge'">{{ order.order_type }}</td>
            <td>{{ order.lot_size }}L</td>
            <td>{{ Number(order.entry_price).toFixed(2) }}</td>
            <td>
              <span :class="{ 'be-highlight': order.is_breakeven_moved }">
                {{ Number(order.stop_loss).toFixed(2) }}
              </span>
            </td>
            <td>{{ Number(order.take_profit).toFixed(2) }}</td>
            <td>
              <div class="badges-wrap">
                <span v-if="order.is_breakeven_moved" class="tag-be" title="Stop Loss đã dời về hòa vốn">
                  <CheckCircle2 :size="10" /> BE
                </span>
                <span v-if="order.is_partial_closed" class="tag-partial" title="Đã chốt 50% khối lượng">
                  <Scissors :size="10" /> 50% Banked
                </span>
                <span v-if="!order.is_breakeven_moved && !order.is_partial_closed" class="text-muted">Standard</span>
              </div>
            </td>
            <td>
              <span v-if="calculateUnrealizedPnL(order) !== null" :class="calculateUnrealizedPnL(order) >= 0 ? 'pnl-up' : 'pnl-down'">
                {{ calculateUnrealizedPnL(order) >= 0 ? '+' : '' }}{{ calculateUnrealizedPnL(order) }} USD
              </span>
              <span v-else class="text-muted">--</span>
            </td>
            <td><span class="status-pill">{{ order.status }}</span></td>
            <td>
              <div class="actions-row">
                <button
                  class="partial-btn"
                  :disabled="partialMap[order.id] || order.is_partial_closed || Number(order.lot_size) <= 0.01"
                  @click="handlePartialClose(order.id)"
                  title="Chốt lời 50% vị thế và dời SL về hòa vốn"
                >
                  <Scissors :size="11" />
                  <span>{{ partialMap[order.id] ? 'Saving...' : '50% TP' }}</span>
                </button>
                <button
                  class="close-btn"
                  :disabled="closingMap[order.id]"
                  @click="handleClose(order.id)"
                  title="Đóng toàn bộ vị thế"
                >
                  <XCircle :size="11" />
                  <span>{{ closingMap[order.id] ? 'Closing...' : 'Close' }}</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr><td colspan="11" class="empty">No open paper positions</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.orders-panel { border: 1px solid #d5ded6; border-radius: 7px; background: #f8faf6; }
header { min-height: 43px; display: flex; align-items: center; justify-content: space-between; padding: 0 12px; border-bottom: 1px solid #e4e9e3; }
header div { display: flex; align-items: center; gap: 8px; color: #526359; }
h2 { margin: 0; color: #29382e; font-size: 11px; }
.header-tags { display: flex; align-items: center; gap: 6px; }
.count-pill { color: #849087; font: 9px 'DM Mono', monospace; }
.cb-alert-pill { display: inline-flex; align-items: center; gap: 4px; padding: 2px 7px; font-size: 9px; font-weight: 800; background: #fee2e2; color: #b91c1c; border-radius: 4px; border: 1px solid #fecaca; }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; white-space: nowrap; text-align: left; }
th { padding: 9px 12px; font-size: 9px; color: #849087; font-weight: 500; border-bottom: 1px solid #e4e9e3; }
td { padding: 8px 12px; border-bottom: 1px solid #edf2ec; font-size: 11px; color: #2b392f; }
.ticket-cell { font-family: 'DM Mono', monospace; color: #526359; }
.buy-badge { color: #16a34a; font-weight: 700; }
.sell-badge { color: #dc2626; font-weight: 700; }
.be-highlight { color: #0284c7; font-weight: 700; }
.badges-wrap { display: flex; align-items: center; gap: 4px; }
.tag-be { display: inline-flex; align-items: center; gap: 3px; font-size: 9px; font-weight: 700; color: #0284c7; background: #e0f2fe; padding: 1px 6px; border-radius: 4px; border: 1px solid #bae6fd; }
.tag-partial { display: inline-flex; align-items: center; gap: 3px; font-size: 9px; font-weight: 700; color: #7c3aed; background: #f3e8ff; padding: 1px 6px; border-radius: 4px; border: 1px solid #e9d5ff; }
.status-pill { font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: #e7ede6; color: #43544a; }
.pnl-up { color: #16a34a; font-weight: 700; }
.pnl-down { color: #dc2626; font-weight: 700; }
.text-muted { color: #9ca3af; font-size: 10px; }
.actions-row { display: flex; align-items: center; gap: 5px; }
.partial-btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #d8b4fe; background: #faf5ff; color: #7e22ce; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; cursor: pointer; transition: all 0.15s; }
.partial-btn:hover:not(:disabled) { background: #f3e8ff; border-color: #c084fc; }
.partial-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.close-btn { display: inline-flex; align-items: center; gap: 4px; border: 1px solid #fecaca; background: #fff5f5; color: #dc2626; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; cursor: pointer; transition: all 0.15s; }
.close-btn:hover:not(:disabled) { background: #fee2e2; border-color: #fca5a5; }
.close-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.empty { text-align: center; color: #849087; font-size: 11px; padding: 22px 0; }
</style>