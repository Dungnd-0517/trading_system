<script setup>
import { computed, ref } from 'vue'
import { ClipboardList, XCircle } from 'lucide-vue-next'
import { marketStore } from '../../stores/marketStore'
import { orderStore } from '../../stores/orderStore'

const props = defineProps({ orders: { type: Array, default: () => [] } })
const activeOrders = computed(() => props.orders.filter((order) => ['PENDING', 'FILLED', 'OPEN'].includes(order.status)))
const closingMap = ref({})

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
</script>

<template>
  <section class="orders-panel">
    <header>
      <div><ClipboardList :size="15" /><h2>Paper positions</h2></div>
      <span>{{ activeOrders.length }} OPEN</span>
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
            <th>LIVE P&amp;L</th>
            <th>STATUS</th>
            <th>ACTION</th>
          </tr>
        </thead>
        <tbody v-if="activeOrders.length">
          <tr v-for="order in activeOrders" :key="order.id">
            <td>#{{ order.id }}</td>
            <td>{{ order.symbol }}</td>
            <td :class="order.order_type.toLowerCase()">{{ order.order_type }}</td>
            <td>{{ order.lot_size }}</td>
            <td>{{ Number(order.entry_price).toFixed(2) }}</td>
            <td>{{ Number(order.stop_loss).toFixed(2) }}</td>
            <td>{{ Number(order.take_profit).toFixed(2) }}</td>
            <td>
              <span v-if="calculateUnrealizedPnL(order) !== null" :class="calculateUnrealizedPnL(order) >= 0 ? 'pnl-up' : 'pnl-down'">
                {{ calculateUnrealizedPnL(order) >= 0 ? '+' : '' }}{{ calculateUnrealizedPnL(order) }} USD
              </span>
              <span v-else class="text-muted">--</span>
            </td>
            <td><span class="status-pill">{{ order.status }}</span></td>
            <td>
              <button
                class="close-btn"
                :disabled="closingMap[order.id]"
                @click="handleClose(order.id)"
                title="Đóng lệnh này với giá hiện tại"
              >
                <XCircle :size="12" />
                <span>{{ closingMap[order.id] ? 'Closing...' : 'Close' }}</span>
              </button>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr><td colspan="10" class="empty">No open paper positions</td></tr>
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
header > span { color: #849087; font: 9px 'DM Mono', monospace; }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; white-space: nowrap; text-align: left; }
th { padding: 9px 11px; border-bottom: 1px solid #e8ece7; color: #98a198; font: 8px 'DM Mono', monospace; }
td { padding: 8px 11px; border-bottom: 1px solid #eff2ed; color: #58665d; font: 9px 'DM Mono', monospace; vertical-align: middle; }
tbody tr:last-child td { border-bottom: 0; }
.buy { color: #34805a; font-weight: 600; }
.sell { color: #bf5c4e; font-weight: 600; }
.status-pill { color: #4b7559; background: #eaf1eb; padding: 2px 5px; border-radius: 3px; }
.pnl-up { color: #2e7a52; font-weight: 600; }
.pnl-down { color: #bb594c; font-weight: 600; }
.text-muted { color: #9aa59d; }
.empty { height: 62px; text-align: center; color: #919c93; font: 10px 'Manrope', sans-serif; }
.close-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 7px;
  background: #fff;
  border: 1px solid #cfd8d0;
  border-radius: 4px;
  font: 8px 'DM Mono', monospace;
  color: #a8473a;
  cursor: pointer;
  transition: all 0.15s ease;
}
.close-btn:hover:not(:disabled) {
  background: #fdf2f1;
  border-color: #e59d94;
  color: #8c2e22;
}
.close-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>