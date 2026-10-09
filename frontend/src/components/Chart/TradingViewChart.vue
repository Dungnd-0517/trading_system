<script setup>
import { createChart, CrosshairMode } from 'lightweight-charts'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { settingsStore } from '../../stores/settingsStore'

const props = defineProps({
  symbol: { type: String, default: 'XAUUSD' },
  timeframe: { type: String, default: 'M1' },
  candles: { type: Array, default: () => [] },
  event: { type: Object, default: null },
  orders: { type: Array, default: () => [] },
  showVolume: { type: Boolean, default: true },
  lastPrice: { type: Number, default: null },
  showEma: { type: Boolean, default: null },
  emaPeriod: { type: Number, default: null },
  emaColor: { type: String, default: null },
})

const activeShowEma = computed(() => (props.showEma !== null ? props.showEma : settingsStore.showEma))
const activeEmaPeriod = computed(() => (props.emaPeriod !== null ? props.emaPeriod : settingsStore.emaPeriod))
const activeEmaColor = computed(() => (props.emaColor !== null ? props.emaColor : settingsStore.emaColor))

const host = ref(null)
const hoveredCandle = ref(null)
const candleMap = new Map()
let chart
let candleSeries
let volumeSeries
let emaSeries = null
let emaMap = new Map()
let livePriceLine
let resizeObserver
let crosshairHandler
const orderPriceLines = new Map()
let hasInitialFit = false

watch([() => props.symbol, () => props.timeframe], () => {
  hasInitialFit = false
})

function computeEMA(candles, period = 20) {
  if (!candles || !candles.length || period <= 0) return []
  const k = 2 / (period + 1)
  const result = []

  if (candles.length >= period) {
    let sum = 0
    for (let i = 0; i < period; i++) {
      sum += Number(candles[i].close)
    }
    let prev = sum / period
    result.push({ time: candles[period - 1].time, value: Number(prev.toFixed(2)) })

    for (let i = period; i < candles.length; i++) {
      const close = Number(candles[i].close)
      prev = close * k + prev * (1 - k)
      result.push({ time: candles[i].time, value: Number(prev.toFixed(2)) })
    }
  } else {
    let prev = Number(candles[0].close)
    result.push({ time: candles[0].time, value: Number(prev.toFixed(2)) })
    for (let i = 1; i < candles.length; i++) {
      const close = Number(candles[i].close)
      prev = close * k + prev * (1 - k)
      result.push({ time: candles[i].time, value: Number(prev.toFixed(2)) })
    }
  }
  return result
}

function updateEmaSeries() {
  if (!chart) return
  if (!activeShowEma.value) {
    if (emaSeries) {
      chart.removeSeries(emaSeries)
      emaSeries = null
    }
    emaMap.clear()
    return
  }

  if (!emaSeries) {
    emaSeries = chart.addLineSeries({
      color: activeEmaColor.value || '#eab308',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerVisible: true,
      title: `EMA ${activeEmaPeriod.value}`,
    })
  } else {
    emaSeries.applyOptions({
      color: activeEmaColor.value || '#eab308',
      title: `EMA ${activeEmaPeriod.value}`,
      visible: true,
    })
  }

  const emaData = computeEMA(props.candles, activeEmaPeriod.value)
  emaMap = new Map(emaData.map((d) => [d.time, d.value]))
  emaSeries.setData(emaData)
}

function renderCandles(candles) {
  if (!candleSeries) return
  candleMap.clear()
  for (const c of candles) {
    candleMap.set(c.time, c)
  }
  candleSeries.setData(candles.map(({ time, open, high, low, close }) => candleData({ time, open, high, low, close })))
  volumeSeries?.setData(candles.map((candle) => volumeData(candle, candle.volume ?? 0)))
  updateEmaSeries()
  if (candles.length && !hasInitialFit) {
    chart.timeScale().fitContent()
    hasInitialFit = true
  }
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
  candleMap.set(candle.time, candle)
  candleSeries.update(candleData(candle))
  volumeSeries?.update(volumeData(candle, event.volume.value))
  updateLivePriceLine(event.price.bid ?? event.price.value)

  if (activeShowEma.value && emaSeries && props.candles.length) {
    const period = activeEmaPeriod.value
    const k = 2 / (period + 1)
    const close = Number(candle.close)
    const prevEma = emaMap.get(candle.time) ?? (emaMap.size ? Array.from(emaMap.values())[emaMap.size - 1] : close)
    const newEma = Number((close * k + prevEma * (1 - k)).toFixed(2))
    emaMap.set(candle.time, newEma)
    emaSeries.update({ time: candle.time, value: newEma })
  }
}

function formatBarTime(timeSec) {
  if (!timeSec) return ''
  // Quy đổi về múi giờ Việt Nam (UTC+7, ICT)
  const vnDate = new Date((Number(timeSec) + 7 * 3600) * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  const YYYY = vnDate.getUTCFullYear()
  const MM = pad(vnDate.getUTCMonth() + 1)
  const DD = pad(vnDate.getUTCDate())
  const HH = pad(vnDate.getUTCHours())
  const mm = pad(vnDate.getUTCMinutes())
  return `${YYYY}-${MM}-${DD} ${HH}:${mm} (ICT)`
}

function formatVolume(vol) {
  if (vol == null) return null
  const v = Number(vol)
  if (isNaN(v)) return null
  if (v >= 1000000) return (v / 1000000).toFixed(2) + 'M'
  if (v >= 1000) return (v / 1000).toFixed(2) + 'K'
  return v.toLocaleString('en-US')
}

const latestCandle = computed(() => {
  if (!props.candles || !props.candles.length) return null
  const c = props.candles[props.candles.length - 1]
  const open = Number(c.open)
  const high = Number(c.high)
  const low = Number(c.low)
  const close = Number(c.close)
  const change = close - open
  const changePercent = open !== 0 ? (change / open) * 100 : 0
  const emaVal = activeShowEma.value && emaMap.has(c.time) ? emaMap.get(c.time) : null
  return {
    time: c.time,
    timeFormatted: formatBarTime(c.time),
    open,
    high,
    low,
    close,
    change,
    changePercent,
    isUp: close >= open,
    volume: c.volume ?? null,
    ema: emaVal,
    isHovered: false,
  }
})

const activeCandle = computed(() => hoveredCandle.value || latestCandle.value)

const tooltipStyle = computed(() => {
  if (!hoveredCandle.value || !host.value) return { display: 'none' }
  const x = hoveredCandle.value.x
  const y = hoveredCandle.value.y
  const containerW = host.value.clientWidth || 600
  const containerH = host.value.clientHeight || 390

  const tooltipW = 200
  const tooltipH = 175

  let left = x + 16
  if (left + tooltipW > containerW - 12) {
    left = Math.max(8, x - tooltipW - 16)
  }

  let top = y - tooltipH / 2
  if (top < 8) {
    top = 8
  } else if (top + tooltipH > containerH - 8) {
    top = Math.max(8, containerH - tooltipH - 8)
  }

  return {
    left: `${left}px`,
    top: `${top}px`,
  }
})

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

  // 2. Tối giản biểu thị lệnh buy/sell trên biểu đồ:
  // - Điểm vào lệnh (Entry): lệnh BUY hiển thị mũi tên xanh dưới nến, lệnh SELL hiển thị mũi tên đỏ trên nến
  // - Điểm thoát lệnh (Exit price): lệnh đóng cũng được tính là 1 lệnh SELL (mũi tên đỏ trên nến) đối với BUY, hoặc BUY đối với SELL
  // - Tối ưu kích thước mũi tên cho phù hợp (size: 1, lược bỏ chữ hiển thị)
  // - Khử trùng lặp: nếu có nhiều hơn 1 lệnh buy hoặc sell trên cùng 1 nến thì chỉ hiển thị 1 mũi tên tại nến đó
  const buyBars = new Set()
  const sellBars = new Set()

  for (const order of props.orders) {
    // 2.1 Điểm vào lệnh (Entry)
    if (order.open_time) {
      const openSec = Math.floor(new Date(order.open_time).getTime() / 1000)
      const barTime = findMatchingBarTime(openSec, props.candles)
      if (barTime !== null) {
        if (order.order_type === 'BUY') {
          buyBars.add(barTime)
        } else {
          sellBars.add(barTime)
        }
      }
    }

    // 2.2 Điểm thoát lệnh (Exit price)
    if (order.status === 'CLOSED' && order.close_time) {
      const closeSec = Math.floor(new Date(order.close_time).getTime() / 1000)
      const barTime = findMatchingBarTime(closeSec, props.candles)
      if (barTime !== null) {
        // Exit price được tính là lệnh SELL (điểm thoát lệnh) đối với lệnh BUY
        if (order.order_type === 'BUY') {
          sellBars.add(barTime)
        } else {
          buyBars.add(barTime)
        }
      }
    }
  }

  const markers = []

  // Marker BUY: arrowUp bên dưới nến, màu xanh ngọc, kích thước chuẩn size: 1
  for (const barTime of buyBars) {
    markers.push({
      time: barTime,
      position: 'belowBar',
      color: '#26a69a',
      shape: 'arrowUp',
      size: 1,
    })
  }

  // Marker SELL: arrowDown bên trên nến, màu đỏ cam, kích thước chuẩn size: 1
  for (const barTime of sellBars) {
    markers.push({
      time: barTime,
      position: 'aboveBar',
      color: '#ef5350',
      shape: 'arrowDown',
      size: 1,
    })
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
    timeScale: {
      borderColor: '#e1e7e0',
      timeVisible: true,
      secondsVisible: false,
      tickMarkFormatter: (timeSec, tickMarkType) => {
        if (typeof timeSec !== 'number') return null
        const vnDate = new Date((timeSec + 7 * 3600) * 1000)
        const pad = (n) => String(n).padStart(2, '0')
        const DD = pad(vnDate.getUTCDate())
        const MM = pad(vnDate.getUTCMonth() + 1)
        const YYYY = vnDate.getUTCFullYear()
        const HH = pad(vnDate.getUTCHours())
        const mm = pad(vnDate.getUTCMinutes())

        switch (tickMarkType) {
          case 0: // Year
            return `${YYYY}`
          case 1: // Month
            return `${MM}/${YYYY}`
          case 2: // DayOfMonth
            return `${DD}/${MM}`
          case 3: // Time
            return `${HH}:${mm}`
          case 4: // TimeWithSeconds
            return `${HH}:${mm}:${pad(vnDate.getUTCSeconds())}`
          default:
            return `${HH}:${mm}`
        }
      },
    },
    localization: {
      locale: 'vi-VN',
      dateFormat: 'dd/MM/yyyy',
      timeFormatter: (timeSec) => {
        if (typeof timeSec === 'number') {
          const vnDate = new Date((timeSec + 7 * 3600) * 1000)
          const pad = (n) => String(n).padStart(2, '0')
          const DD = pad(vnDate.getUTCDate())
          const MM = pad(vnDate.getUTCMonth() + 1)
          const YYYY = vnDate.getUTCFullYear()
          const HH = pad(vnDate.getUTCHours())
          const mm = pad(vnDate.getUTCMinutes())
          return `${DD}/${MM}/${YYYY} ${HH}:${mm} (ICT)`
        }
        return String(timeSec)
      },
    },
  })
  candleSeries = chart.addCandlestickSeries({
    upColor: '#2c7858', downColor: '#cf6858', borderVisible: false,
    wickUpColor: '#2c7858', wickDownColor: '#cf6858',
    lastValueVisible: true,
  })
  candleSeries.priceScale().applyOptions({ scaleMargins: { top: 0.10, bottom: props.showVolume ? 0.28 : 0.08 } })
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

  crosshairHandler = (param) => {
    if (
      !param ||
      !param.time ||
      !param.point ||
      param.point.x < 0 ||
      param.point.x > (host.value?.clientWidth || 0) ||
      param.point.y < 0 ||
      param.point.y > (host.value?.clientHeight || 0)
    ) {
      hoveredCandle.value = null
      return
    }

    const barData = param.seriesData.get(candleSeries)
    if (!barData) {
      hoveredCandle.value = null
      return
    }

    const open = Number(barData.open)
    const high = Number(barData.high)
    const low = Number(barData.low)
    const close = Number(barData.close)
    const change = close - open
    const changePercent = open !== 0 ? (change / open) * 100 : 0
    const isUp = close >= open

    let vol = null
    if (volumeSeries) {
      const volData = param.seriesData.get(volumeSeries)
      if (volData?.value != null) {
        vol = volData.value
      }
    }
    if (vol == null && candleMap.has(param.time)) {
      vol = candleMap.get(param.time).volume ?? null
    }

    const emaVal = activeShowEma.value && emaMap.has(param.time) ? emaMap.get(param.time) : null

    hoveredCandle.value = {
      time: param.time,
      timeFormatted: formatBarTime(param.time),
      open,
      high,
      low,
      close,
      change,
      changePercent,
      isUp,
      volume: vol,
      ema: emaVal,
      isHovered: true,
      x: param.point.x,
      y: param.point.y,
    }
  }

  chart.subscribeCrosshairMove(crosshairHandler)
})

watch(() => props.candles, renderCandles)
watch(() => props.event, applyLiveEvent)
watch(() => props.lastPrice, (val) => { if (val != null) updateLivePriceLine(val) })
watch(() => props.orders, renderOrderOverlays, { deep: true })
watch([activeShowEma, activeEmaPeriod, activeEmaColor], () => {
  updateEmaSeries()
})
watch(() => props.showVolume, (visible) => {
  volumeSeries?.applyOptions({ visible })
  chart?.priceScale('').applyOptions({ visible })
  candleSeries?.priceScale().applyOptions({ scaleMargins: { top: 0.10, bottom: visible ? 0.28 : 0.08 } })
})
onUnmounted(() => {
  resizeObserver?.disconnect()
  if (crosshairHandler && chart) {
    chart.unsubscribeCrosshairMove(crosshairHandler)
  }
  if (emaSeries && chart) {
    chart.removeSeries(emaSeries)
    emaSeries = null
  }
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
    <!-- 1. Thanh Legend Bar cố định góc trên biểu đồ (Top Legend Bar) -->
    <div v-if="activeCandle" class="candle-legend-bar" :class="{ 'is-hovered': activeCandle.isHovered }">
      <div class="legend-meta">
        <span class="symbol-tag">{{ symbol }}</span>
        <span class="time-tag">{{ activeCandle.timeFormatted }}</span>
        <span v-if="activeCandle.isHovered" class="hover-tag">HOVER</span>
      </div>
      <div class="ohlc-strip">
        <span class="ohlc-cell"><span class="lbl">O</span><b :class="activeCandle.isUp ? 'val-up' : 'val-down'">{{ activeCandle.open.toFixed(2) }}</b></span>
        <span class="ohlc-cell"><span class="lbl">H</span><b :class="activeCandle.isUp ? 'val-up' : 'val-down'">{{ activeCandle.high.toFixed(2) }}</b></span>
        <span class="ohlc-cell"><span class="lbl">L</span><b :class="activeCandle.isUp ? 'val-up' : 'val-down'">{{ activeCandle.low.toFixed(2) }}</b></span>
        <span class="ohlc-cell"><span class="lbl">C</span><b :class="activeCandle.isUp ? 'val-up' : 'val-down'">{{ activeCandle.close.toFixed(2) }}</b></span>
        <span class="ohlc-cell change-cell">
          <span class="lbl">CHG</span>
          <b :class="activeCandle.isUp ? 'val-up' : 'val-down'">
            {{ activeCandle.change >= 0 ? '+' : '' }}{{ activeCandle.change.toFixed(2) }}
            ({{ activeCandle.changePercent >= 0 ? '+' : '' }}{{ activeCandle.changePercent.toFixed(2) }}%)
          </b>
        </span>
        <span v-if="activeCandle.volume != null" class="ohlc-cell vol-cell">
          <span class="lbl">VOL</span>
          <b class="val-vol">{{ formatVolume(activeCandle.volume) }}</b>
        </span>
        <span v-if="activeShowEma && activeCandle.ema != null" class="ohlc-cell ema-cell">
          <span class="lbl" :style="{ color: activeEmaColor }">EMA ({{ activeEmaPeriod }})</span>
          <b class="val-ema" :style="{ color: activeEmaColor }">${{ activeCandle.ema.toFixed(2) }}</b>
        </span>
      </div>
    </div>

    <!-- 2. Tooltip nổi thông minh bám theo Crosshair khi hover (Floating Tooltip) -->
    <div
      v-if="hoveredCandle"
      class="candle-floating-tooltip"
      :style="tooltipStyle"
    >
      <div class="tt-header" :class="hoveredCandle.isUp ? 'tt-up' : 'tt-down'">
        <div class="tt-time-row">
          <span class="tt-symbol">{{ symbol }}</span>
          <span class="tt-time">{{ hoveredCandle.timeFormatted }}</span>
        </div>
        <span class="tt-trend-badge">{{ hoveredCandle.isUp ? 'BULLISH ▲' : 'BEARISH ▼' }}</span>
      </div>
      <div class="tt-body">
        <div class="tt-row"><span class="tt-k">Open (O)</span><span class="tt-v">{{ hoveredCandle.open.toFixed(2) }}</span></div>
        <div class="tt-row"><span class="tt-k">High (H)</span><span class="tt-v">{{ hoveredCandle.high.toFixed(2) }}</span></div>
        <div class="tt-row"><span class="tt-k">Low (L)</span><span class="tt-v">{{ hoveredCandle.low.toFixed(2) }}</span></div>
        <div class="tt-row"><span class="tt-k">Close (C)</span><span class="tt-v">{{ hoveredCandle.close.toFixed(2) }}</span></div>
        <div class="tt-divider"></div>
        <div class="tt-row">
          <span class="tt-k">Biên độ</span>
          <span class="tt-v" :class="hoveredCandle.isUp ? 'val-up' : 'val-down'">
            {{ hoveredCandle.change >= 0 ? '+' : '' }}{{ hoveredCandle.change.toFixed(2) }} ({{ hoveredCandle.changePercent >= 0 ? '+' : '' }}{{ hoveredCandle.changePercent.toFixed(2) }}%)
          </span>
        </div>
        <div v-if="hoveredCandle.volume != null" class="tt-row">
          <span class="tt-k">Khối lượng</span>
          <span class="tt-v val-vol">{{ Number(hoveredCandle.volume).toLocaleString('en-US') }}</span>
        </div>
        <div v-if="activeShowEma && hoveredCandle.ema != null" class="tt-row">
          <span class="tt-k" :style="{ color: activeEmaColor }">EMA ({{ activeEmaPeriod }})</span>
          <span class="tt-v" :style="{ color: activeEmaColor }">${{ hoveredCandle.ema.toFixed(2) }}</span>
        </div>
      </div>
    </div>

    <div ref="host" class="chart-host"></div>
    <div v-if="!candles.length" class="empty-chart"><span>Waiting for candle feed</span><small>Historical data appears after ingestion is configured.</small></div>
  </div>
</template>

<style scoped>
.chart-wrap { position: relative; min-height: 390px; }
.chart-host { width: 100%; height: 390px; }
.empty-chart { position: absolute; inset: 0 0 22px; display: flex; flex-direction: column; gap: 5px; align-items: center; justify-content: center; pointer-events: none; color: #78857c; font-size: 12px; }
.empty-chart small { color: #a0aaa1; font-size: 10px; }

/* CANDLE LEGEND BAR */
.candle-legend-bar {
  position: absolute;
  top: 8px;
  left: 10px;
  z-index: 5;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(225, 231, 224, 0.9);
  padding: 4px 10px;
  border-radius: 6px;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: #5c6961;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.candle-legend-bar.is-hovered {
  background: rgba(255, 255, 255, 0.96);
  border-color: #38644e;
  box-shadow: 0 2px 10px rgba(56, 100, 78, 0.08);
}

.legend-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.symbol-tag {
  font-weight: 700;
  color: #1a2920;
  background: #eef3ec;
  padding: 1px 5px;
  border-radius: 3px;
  letter-spacing: 0.3px;
}

.time-tag {
  color: #728178;
}

.hover-tag {
  font-size: 8px;
  background: #e6f4ea;
  color: #236841;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  border: 1px solid #b7e1c1;
}

.ohlc-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ohlc-cell {
  display: flex;
  align-items: center;
  gap: 3px;
}

.lbl {
  color: #8c9990;
  font-size: 9px;
  text-transform: uppercase;
}

.val-up {
  color: #2c7858;
  font-weight: 600;
}

.val-down {
  color: #cf6858;
  font-weight: 600;
}

.val-vol {
  color: #4772a3;
  font-weight: 600;
}

.val-ema {
  font-weight: 700;
}

.ema-cell {
  background: rgba(234, 179, 8, 0.08);
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid rgba(234, 179, 8, 0.25);
}

/* FLOATING TOOLTIP */
.candle-floating-tooltip {
  position: absolute;
  z-index: 10;
  pointer-events: none;
  width: 195px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 6px;
  border: 1px solid #dce2db;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.05);
  font-family: 'DM Mono', monospace;
  overflow: hidden;
  animation: fadeInTooltip 0.1s ease-out;
}

@keyframes fadeInTooltip {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}

.tt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 9px;
  border-bottom: 1px solid #edf0ec;
  font-size: 9px;
}

.tt-header.tt-up {
  background: #f0f7f3;
  border-bottom-color: #d1e7d8;
}

.tt-header.tt-down {
  background: #fcf2f0;
  border-bottom-color: #f7d5d0;
}

.tt-time-row {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.tt-symbol {
  font-weight: 700;
  color: #1a2920;
  font-size: 10px;
}

.tt-time {
  font-size: 8.5px;
  color: #748178;
}

.tt-trend-badge {
  font-size: 8.5px;
  font-weight: 700;
  padding: 2px 5px;
  border-radius: 3px;
}

.tt-up .tt-trend-badge {
  background: #2c7858;
  color: #fff;
}

.tt-down .tt-trend-badge {
  background: #cf6858;
  color: #fff;
}

.tt-body {
  padding: 6px 9px;
  display: flex;
  flex-direction: column;
  gap: 3.5px;
}

.tt-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 9.5px;
}

.tt-k {
  color: #7b887f;
}

.tt-v {
  font-weight: 600;
  color: #243329;
}

.tt-divider {
  height: 1px;
  background: #edf1ec;
  margin: 2px 0;
}
</style>