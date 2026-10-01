<script setup>
import { createChart, CrosshairMode } from 'lightweight-charts'
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  candles: { type: Array, default: () => [] },
  event: { type: Object, default: null },
  showVolume: { type: Boolean, default: true },
})
const host = ref(null)
let chart
let candleSeries
let volumeSeries
let livePriceLine
let resizeObserver

function renderCandles(candles) {
  if (!candleSeries) return
  candleSeries.setData(candles.map(({ time, open, high, low, close }) => candleData({ time, open, high, low, close })))
  volumeSeries?.setData(candles.map((candle) => volumeData(candle, candle.volume ?? 0)))
  if (candles.length) chart.timeScale().fitContent()
}

function candleData(candle) {
  return {
    time: candle.time,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
    ...(candle.close >= candle.open
      ? { color: '#2c7858', borderColor: '#2c7858', wickColor: '#2c7858' }
      : { color: '#cf6858', borderColor: '#cf6858', wickColor: '#cf6858' }),
  }
}

function volumeData(candle, value) {
  return {
    time: candle.time,
    value,
    color: candle.close >= candle.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)',
  }
}

function applyLiveEvent(event) {
  if (!candleSeries || !event?.candle || !event?.volume || !event?.price) return
  const candle = event.candle
  candleSeries.update(candleData(candle))
  volumeSeries.update(volumeData(candle, event.volume.value))
  if (livePriceLine) candleSeries.removePriceLine(livePriceLine)
  livePriceLine = candleSeries.createPriceLine({
    price: event.price.bid ?? event.price.value,
    color: '#4772a3',
    lineWidth: 1,
    lineStyle: 2,
    axisLabelVisible: true,
    title: 'LIVE',
  })
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
  candleSeries = chart.addCandlestickSeries({
    upColor: '#2c7858', downColor: '#cf6858', borderVisible: false,
    wickUpColor: '#2c7858', wickDownColor: '#cf6858',
    lastValueVisible: true,
  })
  candleSeries.priceScale().applyOptions({ scaleMargins: { top: 0.06, bottom: props.showVolume ? 0.28 : 0.08 } })
  volumeSeries = chart.addHistogramSeries({
    priceScaleId: '',
    priceFormat: { type: 'volume' },
    priceLineVisible: false,
    lastValueVisible: false,
  })
  chart.priceScale('').applyOptions({ scaleMargins: { top: 0.76, bottom: 0 }, visible: props.showVolume })
  renderCandles(props.candles)
  applyLiveEvent(props.event)
  volumeSeries.applyOptions({ visible: props.showVolume })
  resizeObserver = new ResizeObserver(([entry]) => chart?.applyOptions({ width: entry.contentRect.width }))
  resizeObserver.observe(host.value)
})

watch(() => props.candles, renderCandles)
watch(() => props.event, applyLiveEvent)
watch(() => props.showVolume, (visible) => {
  volumeSeries?.applyOptions({ visible })
  chart?.priceScale('').applyOptions({ visible })
  candleSeries?.priceScale().applyOptions({ scaleMargins: { top: 0.06, bottom: visible ? 0.28 : 0.08 } })
})
onUnmounted(() => {
  resizeObserver?.disconnect()
  if (livePriceLine && candleSeries) candleSeries.removePriceLine(livePriceLine)
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