<script setup>
import { computed } from 'vue'
import { ClipboardList } from 'lucide-vue-next'

const props = defineProps({ orders: { type: Array, default: () => [] } })
const activeOrders = computed(() => props.orders.filter((order) => ['PENDING', 'FILLED', 'OPEN'].includes(order.status)))
</script>

<template>
  <section class="orders-panel">
    <header><div><ClipboardList :size="15" /><h2>Paper positions</h2></div><span>{{ activeOrders.length }} OPEN</span></header>
    <div class="table-scroll">
      <table>
        <thead><tr><th>TICKET</th><th>ASSET</th><th>SIDE</th><th>SIZE</th><th>ENTRY</th><th>STOP</th><th>TARGET</th><th>STATUS</th></tr></thead>
        <tbody v-if="activeOrders.length">
          <tr v-for="order in activeOrders" :key="order.id">
            <td>#{{ order.id }}</td><td>{{ order.symbol }}</td><td :class="order.order_type.toLowerCase()">{{ order.order_type }}</td><td>{{ order.lot_size }}</td><td>{{ Number(order.entry_price).toFixed(2) }}</td><td>{{ Number(order.stop_loss).toFixed(2) }}</td><td>{{ Number(order.take_profit).toFixed(2) }}</td><td><span class="status-pill">{{ order.status }}</span></td>
          </tr>
        </tbody>
        <tbody v-else><tr><td colspan="8" class="empty">No open paper positions</td></tr></tbody>
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
td { padding: 10px 11px; border-bottom: 1px solid #eff2ed; color: #58665d; font: 9px 'DM Mono', monospace; }
tbody tr:last-child td { border-bottom: 0; }
.buy { color: #34805a; }
.sell { color: #bf5c4e; }
.status-pill { color: #4b7559; }
.empty { height: 62px; text-align: center; color: #919c93; font: 10px 'Manrope', sans-serif; }
</style>