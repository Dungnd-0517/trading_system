<script setup>
import { ref } from 'vue'
import { CandlestickChart, ChartNoAxesCombined } from 'lucide-vue-next'

const showVolume = ref(false)
const showOrders = ref(true)
</script>

<template>
  <div class="chart-controls">
    <div class="chart-legend"><CandlestickChart :size="15" /><span>PRICE ACTION</span><i></i><span class="legend-entry">ENTRY</span><i></i><span class="legend-stop">SL / TP</span></div>
    <div class="chart-toggles">
      <button :class="{ active: showVolume }" :aria-pressed="showVolume" @click="showVolume = !showVolume"><ChartNoAxesCombined :size="14" /> VOLUME</button>
      <button :class="{ active: showOrders }" :aria-pressed="showOrders" @click="showOrders = !showOrders">ORDERS</button>
    </div>
  </div>
</template>

<style scoped>
.chart-controls { min-height: 39px; display: flex; align-items: center; justify-content: space-between; padding: 0 12px; border-bottom: 1px solid #e8ece7; color: #65736a; font: 9px 'DM Mono', monospace; }
.chart-legend, .chart-toggles, .chart-toggles button { display: flex; align-items: center; gap: 7px; }
.chart-legend i { width: 6px; height: 6px; margin-left: 5px; border-radius: 50%; background: #52936d; }
.chart-legend i:last-of-type { background: #cc6a5c; }
.legend-entry { color: #4772a3; }
.legend-stop { color: #b35d52; }
.chart-toggles button { border: 0; border-radius: 4px; background: transparent; color: #8a958d; padding: 5px 6px; font: inherit; }
.chart-toggles button.active { color: #315c45; background: #eaf0e7; }
</style>