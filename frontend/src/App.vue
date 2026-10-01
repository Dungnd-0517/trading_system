<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Activity, Bell, CircleHelp, Radio, RefreshCw, Settings2 } from 'lucide-vue-next'
import TradingViewChart from './components/Chart/TradingViewChart.vue'
import ChartOverlayControls from './components/Chart/ChartOverlayControls.vue'
import NewsStream from './components/News/NewsStream.vue'
import SentimentGauge from './components/News/SentimentGauge.vue'
import OrderBookTable from './components/Simulation/OrderBookTable.vue'
import MetricsCards from './components/Simulation/MetricsCards.vue'
import InsightsPanel from './components/AIAnalysis/InsightsPanel.vue'
import { marketStore } from './stores/marketStore'
import { orderStore } from './stores/orderStore'
import { connectMarketStream } from './services/websocket'

const streamConnected = ref(false)
const now = ref(new Date())
let clockTimer
let socket
const dbConnected = computed(() => marketStore.health?.services?.postgres === true)
const redisConnected = computed(() => marketStore.health?.services?.redis === true)

function selectTimeframe(timeframe) {
  marketStore.timeframe = timeframe
  marketStore.refresh()
}

onMounted(() => {
  marketStore.refresh()
  orderStore.refresh()
  socket = connectMarketStream((tick) => {
    if (tick.symbol === marketStore.symbol && tick.type === 'candle') marketStore.refresh()
  }, (value) => { streamConnected.value = value })
  clockTimer = window.setInterval(() => { now.value = new Date() }, 1000)
})
onUnmounted(() => {
  window.clearInterval(clockTimer)
  socket?.close()
})
</script>

<template>
  <main class="workspace">
    <header class="topbar">
      <a class="brand" href="#top" aria-label="Trading System home">
        <span class="brand-mark"><Activity :size="18" /></span>
        <span>FIELDNOTE <small>MARKETS</small></span>
      </a>
      <div class="topbar-center">
        <span class="eyebrow">PAPER EXECUTION</span>
        <span class="mode-dot"></span>
        <span>SIMULATOR</span>
      </div>
      <div class="topbar-actions">
        <span class="clock">{{ now.toLocaleTimeString('vi-VN', { hour12: false, timeZone: 'Asia/Ho_Chi_Minh' }) }} <small>ICT</small></span>
        <button class="icon-button" aria-label="Notifications"><Bell :size="17" /></button>
        <button class="icon-button" aria-label="Settings"><Settings2 :size="17" /></button>
        <span class="avatar">Q</span>
      </div>
    </header>

    <section class="status-strip" aria-label="Service status">
      <span class="status-label">SYSTEM STATUS</span>
      <span class="service-state"><i :class="dbConnected ? 'up' : 'down'"></i> POSTGRES <b>{{ dbConnected ? 'CONNECTED' : 'OFFLINE' }}</b></span>
      <span class="service-state"><i :class="redisConnected ? 'up' : 'down'"></i> REDIS <b>{{ redisConnected ? 'CONNECTED' : 'OFFLINE' }}</b></span>
      <span class="service-state"><i :class="streamConnected ? 'up' : 'down'"></i> MARKET STREAM <b>{{ streamConnected ? 'LIVE' : 'WAITING' }}</b></span>
      <span class="status-spacer"></span>
      <span class="read-only"><Radio :size="13" /> PAPER MODE · NO LIVE ORDERS</span>
    </section>

    <section class="instrument-bar">
      <div class="instrument-title"><span class="asset-icon">Au</span><div><h1>XAUUSD</h1><span>Gold / U.S. Dollar</span></div></div>
      <div class="instrument-price"><strong>--</strong><span>Awaiting market data</span></div>
      <div class="timeframes" role="group" aria-label="Chart timeframe">
        <button v-for="frame in ['M1', 'M5', 'M15', 'H1']" :key="frame" :class="{ selected: marketStore.timeframe === frame }" @click="selectTimeframe(frame)">{{ frame }}</button>
      </div>
      <div class="instrument-tools"><button class="text-button" @click="marketStore.refresh"><RefreshCw :size="14" /> Refresh</button><button class="icon-button" aria-label="Help"><CircleHelp :size="16" /></button></div>
    </section>

    <div v-if="marketStore.error" class="connection-notice">{{ marketStore.error }} · Kiểm tra backend và Docker services.</div>

    <section class="main-grid">
      <div class="chart-column">
        <div class="chart-panel">
          <ChartOverlayControls />
          <TradingViewChart :candles="marketStore.candles" />
          <div class="chart-foot"><span>{{ marketStore.candles.length ? `${marketStore.candles.length} bars loaded` : 'NO HISTORICAL DATA' }}</span><span>UTC · {{ marketStore.timeframe }}</span></div>
        </div>
        <MetricsCards :orders="orderStore.orders" />
        <OrderBookTable :orders="orderStore.orders" />
      </div>
      <aside class="right-column">
        <InsightsPanel />
        <SentimentGauge :news="orderStore.news" />
        <NewsStream :news="orderStore.news" />
      </aside>
    </section>
    <footer class="footer"><span>FIELDNOTE MARKETS <b>·</b> STAGE 01</span><span>Market data and simulated fills only. Not investment advice.</span></footer>
  </main>
</template>