<script setup>
import { ref } from 'vue'
import { Activity, CandlestickChart, ChartNoAxesCombined } from 'lucide-vue-next'
import { settingsStore } from '../../stores/settingsStore'

const props = defineProps({ showVolume: { type: Boolean, default: true } })
const emit = defineEmits(['update:showVolume'])
const showOrders = ref(true)
</script>

<template>
  <div class="chart-controls">
    <div class="chart-legend">
      <CandlestickChart :size="15" />
      <span>PRICE ACTION</span>
      <i></i><span class="legend-entry">ENTRY</span>
      <i></i><span class="legend-stop">SL / TP</span>
      <span v-if="settingsStore.showEma" class="legend-ema" :style="{ color: settingsStore.emaColor }">
        <i :style="{ background: settingsStore.emaColor }"></i>EMA {{ settingsStore.emaPeriod }}
      </span>
    </div>
    <div class="chart-toggles">
      <button
        :class="{ active: settingsStore.showEma }"
        :aria-pressed="settingsStore.showEma"
        @click="settingsStore.showEma = !settingsStore.showEma"
        title="Bật/Tắt đường EMA trên biểu đồ (Tùy chỉnh chu kỳ trong mục Cài đặt)"
      >
        <Activity :size="13" /> EMA ({{ settingsStore.emaPeriod }})
      </button>
      <button :class="{ active: props.showVolume }" :aria-pressed="props.showVolume" @click="emit('update:showVolume', !props.showVolume)">
        <ChartNoAxesCombined :size="14" /> VOLUME
      </button>
      <button :class="{ active: showOrders }" :aria-pressed="showOrders" @click="showOrders = !showOrders">
        ORDERS
      </button>
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
.legend-ema { font-weight: 700; display: inline-flex; align-items: center; gap: 4px; }
.legend-ema i { width: 6px; height: 6px; border-radius: 50%; margin-left: 6px; }
.chart-toggles button { border: 0; border-radius: 4px; background: transparent; color: #8a958d; padding: 5px 6px; font: inherit; cursor: pointer; transition: all 0.15s ease; }
.chart-toggles button:hover { color: #315c45; background: #f0f4ef; }
.chart-toggles button.active { color: #315c45; background: #eaf0e7; font-weight: 600; }
</style>