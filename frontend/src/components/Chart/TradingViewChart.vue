<script setup>
import { createChart, CrosshairMode } from 'lightweight-charts'
import { onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  candles: { type: Array, default: () => [] },
  event: { type: Object, default: null },
  orders: { type: Array, default: () => [] },
  showVolume: { type: Boolean, default: true },
  lastPrice: { type: Number, default: null },
})

const host = ref(null)
let chart
let candleSeries
let volumeSeries
let livePriceLine
let resizeObserver
const orderPriceLines = new Map()

function renderCandles(candles) {
  if (!candleSeries) return
  candleSeries.setData(candles.map(({ time, open, high, low, close }) => candleData({ time, open, high, low, close })))
  volumeSeries?.setData(candles.map((candle) => volumeData(candle, candle.volume ?? 0)))
  if (candles.length) chart.timeScale().fitContent()
  renderOrderOverlays()
  if (props.lastPrice != null) {
    updateLivePriceLine(props.lastPrice)
  }
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

function updateLivePriceLine(price) {
  if (!candleSeries || price == null) return
  if (livePriceLine) candleSeries.removePriceLine(livePriceLine)
  livePriceLine = candleSeries.createPriceLine({
    price: Number(price),
    color: '#4772a3',
    lineWidth: 1,
    lineStyle: 2,
    axisLabelVisible: true,
    title: 'LIVE',
  })
}

function applyLiveEvent(event) {
  if (!candleSeries || !event?.candle || !event?.volume || !event?.price) return
  const candle = event.candle
  candleSeries.update(candleData(candle))
  volumeSeries?.update(volumeData(candle, event.volume.value))
  updateLivePriceLine(event.price.bid ?? event.price.value)
}

function findMatchingBarTime(targetSec, candles) {
  if (!candles || !candles.length) return null
  if (targetSec < candles[0].time) return null
  let low = 0
  let high = candles.length - 1
  let matched = candles[0].time
  while (low <= high) {
    const mid = (low + high) >> 1
    if (candles[mid].time <= targetSec) {
      matched = candles[mid].time
      low = mid + 1
    } else {
      high = mid - 1
    }
  }
  return matched
}

function renderOrderOverlays() {
  if (!candleSeries) return

  // 1. Quản lý PriceLines cho các lệnh đang mở (Entry, SL, TP)
  const activeOrders = props.orders.filter((o) => ['OPEN', 'FILLED'].includes(o.status))
  const activeIds = new Set(activeOrders.map((o) => o.id))

  // Xóa các đường price line của lệnh đã đóng hoặc hủy
  for (const [id, lines] of orderPriceLines.entries()) {
    if (!activeIds.has(id)) {
      if (lines.entry) candleSeries.removePriceLine(lines.entry)
      if (lines.sl) candleSeries.removePriceLine(lines.sl)
      if (lines.tp) candleSeries.removePriceLine(lines.tp)
      orderPriceLines.delete(id)
    }
  }

  // Vẽ hoặc cập nhật price line cho các lệnh mở
  for (const order of activeOrders) {
    if (!orderPriceLines.has(order.id)) {
      const entryLine = candleSeries.createPriceLine({
        price: Number(order.entry_price),
        color: '#2196F3',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: `${order.order_type} #${order.id}`,
      })
      const slLine = candleSeries.createPriceLine({
        price: Number(order.stop_loss),
        color: '#F44336',
        lineWidth: 1,
        lineStyle: 0,
        axisLabelVisible: true,
        title: `SL #${order.id}`,
      })
      const tpLine = candleSeries.createPriceLine({
        price: Number(order.take_profit),
        color: '#4CAF50',
        lineWidth: 1,
        lineStyle: 0,
        axisLabelVisible: true,
        title: `TP #${order.id}`,
      })
      orderPriceLines.set(order.id, { entry: entryLine, sl: slLine, tp: tpLine })
    }
  }

  // 2. Vẽ Markers (Vào lệnh & Đóng lệnh) đã snap khớp chính xác với timestamp nến
  const markers = []
  for (const order of props.orders) {
    // Marker vào lệnh
    if (order.open_time) {
      const openSec = Math.floor(new Date(order.open_time).getTime() / 1000)
      const barTime = findMatchingBarTime(openSec, props.candles)
      if (barTime !== null) {
        markers.push({
          time: barTime,
          position: order.order_type === 'BUY' ? 'belowBar' : 'aboveBar',
          color: order.order_type === 'BUY' ? '#26a69a' : '#ef5350',
          shape: order.order_type === 'BUY' ? 'arrowUp' : 'arrowDown',
          text: `${order.order_type} ${order.lot_size}L`,
        })
      }
    }
    // Marker đóng lệnh
    if (order.status === 'CLOSED' && order.close_time) {
      const closeSec = Math.floor(new Date(order.close_time).getTime() / 1000)
      const barTime = findMatchingBarTime(closeSec, props.candles)
      if (barTime !== null) {
        const isWin = (order.realized_pnl || 0) >= 0
        markers.push({
          time: barTime,
          position: 'inBar',
          color: isWin ? '#26a69a' : '#ef5350',
          shape: 'circle',
          text: `${isWin ? '+' : ''}$${Number(order.realized_pnl || 0).toFixed(2)} (${order.close_reason || 'CLOSE'})`,
        })
      }
    }
  }

  // Sắp xếp markers theo thời gian tăng dần (bắt buộc bởi lightweight-charts)
  markers.sort((a, b) => a.time - b.time)
  try {
    candleSeries.setMarkers(markers)
  } catch {
    // Bỏ qua nếu có lỗi
  }
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
  if (props.lastPrice != null) {
    updateLivePriceLine(props.lastPrice)
  }
  volumeSeries.applyOptions({ visible: props.showVolume })
  resizeObserver = new ResizeObserver(([entry]) => chart?.applyOptions({ width: entry.contentRect.width }))
  resizeObserver.observe(host.value)
})

watch(() => props.candles, renderCandles)
watch(() => props.event, applyLiveEvent)
watch(() => props.lastPrice, (val) => { if (val != null) updateLivePriceLine(val) })
watch(() => props.orders, renderOrderOverlays, { deep: true })
watch(() => props.showVolume, (visible) => {
  volumeSeries?.applyOptions({ visible })
  chart?.priceScale('').applyOptions({ visible })
  candleSeries?.priceScale().applyOptions({ scaleMargins: { top: 0.06, bottom: visible ? 0.28 : 0.08 } })
})
onUnmounted(() => {
  resizeObserver?.disconnect()
  for (const [, lines] of orderPriceLines.entries()) {
    if (lines.entry) candleSeries?.removePriceLine(lines.entry)
    if (lines.sl) candleSeries?.removePriceLine(lines.sl)
    if (lines.tp) candleSeries?.removePriceLine(lines.tp)
  }
  orderPriceLines.clear()
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