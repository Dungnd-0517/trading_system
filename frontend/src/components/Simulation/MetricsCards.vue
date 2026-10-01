<script setup>
import { computed } from 'vue'
import { Activity, CircleDollarSign, Target } from 'lucide-vue-next'

const props = defineProps({ orders: { type: Array, default: () => [] } })
const closed = computed(() => props.orders.filter((order) => order.status === 'CLOSED'))
const pnl = computed(() => closed.value.reduce((total, order) => total + (order.realized_pnl || 0), 0))
const wins = computed(() => closed.value.filter((order) => (order.realized_pnl || 0) > 0).length)
const winrate = computed(() => closed.value.length ? Math.round(wins.value / closed.value.length * 100) : null)
</script>

<template>
  <section class="metrics-row" aria-label="Simulation metrics">
    <div><span class="metric-icon"><CircleDollarSign :size="15" /></span><label>REALIZED P&amp;L</label><strong :class="pnl >= 0 ? 'positive' : 'negative'">{{ pnl >= 0 ? '+' : '' }}{{ pnl.toFixed(2) }}</strong></div>
    <div><span class="metric-icon"><Target :size="15" /></span><label>WIN RATE</label><strong>{{ winrate === null ? '—' : `${winrate}%` }}</strong></div>
    <div><span class="metric-icon"><Activity :size="15" /></span><label>CLOSED TRADES</label><strong>{{ closed.length }}</strong></div>
  </section>
</template>

<style scoped>
.metrics-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid #d5ded6; border-bottom: 1px solid #d5ded6; background: #f5f8f3; }
.metrics-row > div { min-height: 68px; display: grid; grid-template-columns: 24px 1fr; grid-template-rows: 1fr 1fr; align-items: center; padding: 10px 14px; border-right: 1px solid #e0e6df; }
.metrics-row > div:last-child { border: 0; }
.metric-icon { grid-row: 1 / 3; color: #6f8876; }
label { align-self: end; color: #89948c; font: 8px 'DM Mono', monospace; }
strong { align-self: start; color: #304238; font: 13px 'DM Mono', monospace; }
.positive { color: #2e7a52; }
.negative { color: #bb594c; }
@media (max-width: 460px) { .metrics-row > div { padding: 9px 7px; grid-template-columns: 20px 1fr; } label { font-size: 7px; } }
</style>