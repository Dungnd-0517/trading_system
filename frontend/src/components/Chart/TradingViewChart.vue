<script setup>
import { createChart, CrosshairMode } from 'lightweight-charts'
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({ candles: { type: Array, default: () => [] } })
const host = ref(null)
let chart
let candleSeries
let resizeObserver

function renderCandles(candles) {
  if (!candleSeries) return
  candleSeries.setData(candles.map(({ time, open, high, low, close }) => ({
    time, open, high, low, close,
    ...(close >= open ? { color: '#2c7858', borderColor: '#2c7858', wickColor: '#2c7858' } : { color: '#cf6858', borderColor: '#cf6858', wickColor: '#cf6858' }),
  })))
  if (candles.length) chart.timeScale().fitContent()
}

onMounted(() => {
  chart = createChart(host.value, {
    width: host.value.clientWidth,
    height: 390,
    layout: { background: { color: '#f8faf6' }, textColor: '#748178', fontFamily: "'DM Mono', monospace", fontSize: 10 },
    grid: { vertLines: { color: '#edf0eb' }, horzLines: { color: '#edf0eb' } },
    crosshair: { mode: CrosshairMode.Normal },
    rightPriceScale: { borderColor: '#e1e7e0' },
    timeScale: { borderColor: '#e1e7e0', timeVisible: true, secondsVisible: false },
  })
  candleSeries = chart.addCandlestickSeries({ upColor: '#2c7858', downColor: '#cf6858', borderVisible: false, wickUpColor: '#2c7858', wickDownColor: '#cf6858' })
  renderCandles(props.candles)
  resizeObserver = new ResizeObserver(([entry]) => chart?.applyOptions({ width: entry.contentRect.width }))
  resizeObserver.observe(host.value)
})

watch(() => props.candles, renderCandles)
onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.remove()
})
</script>

<template>
  <div class="chart-wrap">
    <div ref="host" class="chart-host"></div>
    <div v-if="!candles.length" class="empty-chart"><span>Waiting for candle feed</span><small>Historical data appears after ingestion is configured.</small></div>
  </div>
</template>

<style scoped>
.chart-wrap { position: relative; min-height: 390px; }
.chart-host { width: 100%; height: 390px; }
.empty-chart { position: absolute; inset: 0 0 22px; display: flex; flex-direction: column; gap: 5px; align-items: center; justify-content: center; pointer-events: none; color: #78857c; font-size: 12px; }
.empty-chart small { color: #a0aaa1; font-size: 10px; }
</style>