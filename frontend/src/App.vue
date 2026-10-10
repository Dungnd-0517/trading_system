<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  Activity,
  BarChart2,
  Bell,
  BrainCircuit,
  CircleHelp,
  History,
  LayoutDashboard,
  Newspaper,
  Radio,
  RefreshCw,
  Settings2,
  ShieldAlert,
  Zap,
} from 'lucide-vue-next'
import TradingViewChart from './components/Chart/TradingViewChart.vue'
import ChartOverlayControls from './components/Chart/ChartOverlayControls.vue'
import NewsStream from './components/News/NewsStream.vue'
import SentimentGauge from './components/News/SentimentGauge.vue'
import OrderBookTable from './components/Simulation/OrderBookTable.vue'
import MetricsCards from './components/Simulation/MetricsCards.vue'
import MarketAnalysisStatus from './components/Simulation/MarketAnalysisStatus.vue'
import InsightsPanel from './components/AIAnalysis/InsightsPanel.vue'
import OrdersHistory from './components/Orders/OrdersHistory.vue'
import NewsEventsView from './components/News/NewsEventsView.vue'
import StrategyAnalysisView from './components/Strategy/StrategyAnalysisView.vue'
import BacktestLabView from './components/Strategy/BacktestLabView.vue'
import SettingsView from './components/Settings/SettingsView.vue'
import { marketStore } from './stores/marketStore'
import { orderStore } from './stores/orderStore'
import { connectMarketStream } from './services/websocket'

const activeTab = ref('cockpit')
const calendarInitialSubTab = ref('calendar')
const streamConnected = ref(false)
const showVolume = ref(true)
const now = ref(new Date())
const priceDirection = ref('neutral')
let clockTimer
let sourceTimer
let socket

function openFullCalendar() {
  activeTab.value = 'news'
  calendarInitialSubTab.value = 'calendar'
}

function openFullNews() {
  activeTab.value = 'news'
  calendarInitialSubTab.value = 'news'
}

const dbConnected = computed(() => marketStore.health?.services?.postgres === true)
const redisConnected = computed(() => marketStore.health?.services?.redis === true)

function selectTimeframe(timeframe) {
  marketStore.timeframe = timeframe
  marketStore.chartEvent = null
  marketStore.refresh()
}

onMounted(() => {
  marketStore.refresh()
  marketStore.startPolling(2500)
  orderStore.refresh()
  socket = connectMarketStream(
    (event) => {
      if (event.type === 'chart.update') {
        const prev = marketStore.lastPrice
        marketStore.applyChartUpdate(event)
        const curr = marketStore.lastPrice
        if (prev !== null && curr !== null) {
          priceDirection.value = curr > prev ? 'tick-up' : curr < prev ? 'tick-down' : priceDirection.value
        }
      }
      if (event.type === 'order.update') orderStore.applyOrderUpdate(event)
      if (event.type === 'news.upsert') orderStore.applyNewsUpdate(event)
      if (event.type === 'signal.new') orderStore.applySignalUpdate(event)
      if (event.type === 'circuit_breaker.update') orderStore.applyCircuitBreakerUpdate(event)
      if (event.type === 'candle' && event.symbol === marketStore.symbol) marketStore.refresh()
    },
    (value) => {
      streamConnected.value = value
    }
  )
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 1000)
  sourceTimer = window.setInterval(() => {
    orderStore.refreshSources()
  }, 60_000)
})

onUnmounted(() => {
  marketStore.stopPolling()
  window.clearInterval(clockTimer)
  window.clearInterval(sourceTimer)
  socket?.close()
})
</script>

<template>
  <main class="workspace">
    <!-- Topbar with Brand, Main Navigation, Balance and Actions -->
    <header class="topbar">
      <a class="brand" href="#top" aria-label="Trading System home" @click.prevent="activeTab = 'cockpit'">
        <span class="brand-mark"><Activity :size="18" /></span>
        <span>FIELDNOTE <small>MARKETS</small></span>
      </a>

      <!-- Primary Navigation Bar -->
      <nav class="main-nav" role="tablist" aria-label="Main menu navigation">
        <button
          role="tab"
          :aria-selected="activeTab === 'cockpit'"
          :class="['nav-tab', { active: activeTab === 'cockpit' }]"
          @click="activeTab = 'cockpit'"
        >
          <LayoutDashboard :size="14" />
          <span>Trading Cockpit</span>
        </button>

        <button
          role="tab"
          :aria-selected="activeTab === 'orders'"
          :class="['nav-tab', { active: activeTab === 'orders' }]"
          @click="activeTab = 'orders'"
        >
          <History :size="14" />
          <span>Orders History</span>
          <span v-if="orderStore.orders.length" class="nav-badge">{{ orderStore.orders.length }}</span>
        </button>

        <button
          role="tab"
          :aria-selected="activeTab === 'news'"
          :class="['nav-tab', { active: activeTab === 'news' }]"
          @click="activeTab = 'news'"
        >
          <Newspaper :size="14" />
          <span>News &amp; Events</span>
          <span v-if="orderStore.news.length || orderStore.events.length" class="nav-badge">
            {{ orderStore.news.length + orderStore.events.length }}
          </span>
        </button>

        <button
          role="tab"
          :aria-selected="activeTab === 'strategy'"
          :class="['nav-tab', { active: activeTab === 'strategy' }]"
          @click="activeTab = 'strategy'"
        >
          <BrainCircuit :size="14" />
          <span>Strategy &amp; Analysis</span>
        </button>

        <button
          role="tab"
          :aria-selected="activeTab === 'backtest'"
          :class="['nav-tab', { active: activeTab === 'backtest' }]"
          @click="activeTab = 'backtest'"
        >
          <BarChart2 :size="14" />
          <span>Backtest Lab</span>
        </button>

        <button
          role="tab"
          :aria-selected="activeTab === 'settings'"
          :class="['nav-tab', { active: activeTab === 'settings' }]"
          @click="activeTab = 'settings'"
        >
          <Settings2 :size="14" />
          <span>Settings</span>
        </button>
      </nav>

      <div class="topbar-center">
        <span class="account-badge">
          BALANCE: ${{ Number(orderStore.account?.current_balance || 10000).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}
          <small class="equity-badge">EQUITY: ${{ Number(orderStore.account?.equity || 10000).toLocaleString('en-US', { minimumFractionDigits: 2 }) }}</small>
        </span>
      </div>

      <div class="topbar-actions">
        <span class="clock">{{ now.toLocaleTimeString('vi-VN', { hour12: false, timeZone: 'Asia/Ho_Chi_Minh' }) }} <small>ICT</small></span>
        <button
          class="icon-button"
          :class="{ active: activeTab === 'news' }"
          aria-label="Notifications"
          title="Tin tức &amp; Sự kiện"
          @click="activeTab = 'news'"
        >
          <Bell :size="17" />
        </button>
        <button
          class="icon-button"
          :class="{ active: activeTab === 'settings' }"
          aria-label="Settings"
          title="Cài đặt hệ thống"
          @click="activeTab = 'settings'"
        >
          <Settings2 :size="17" />
        </button>
        <span class="avatar">Q</span>
      </div>
    </header>

    <!-- System Status Strip (Subheader) -->
    <section class="status-strip" aria-label="Service status">
      <span class="status-label">SYSTEM STATUS</span>
      <span class="service-state"><i :class="dbConnected ? 'up' : 'down'"></i> POSTGRES <b>{{ dbConnected ? 'CONNECTED' : 'OFFLINE' }}</b></span>
      <span class="service-state"><i :class="redisConnected ? 'up' : 'down'"></i> REDIS <b>{{ redisConnected ? 'CONNECTED' : 'OFFLINE' }}</b></span>
      <span class="service-state"><i :class="streamConnected ? 'up' : 'down'"></i> MARKET STREAM <b>{{ streamConnected ? 'LIVE' : 'WAITING' }}</b></span>
      
      <span class="status-spacer"></span>

      <!-- Mode control moved to subheader for a more spacious topbar -->
      <div class="trading-mode-pill">
        <span class="mode-label">MODE:</span>
        <button
          class="mode-btn"
          :class="{ active: orderStore.config.execution_mode === 'MANUAL' }"
          @click="orderStore.setExecutionMode('MANUAL')"
          title="Chế độ Manual: Chỉ báo tín hiệu, trader duyệt tay"
        >
          MANUAL
        </button>
        <button
          class="mode-btn"
          :class="{ active: orderStore.config.execution_mode === 'SEMI_AUTO' }"
          @click="orderStore.setExecutionMode('SEMI_AUTO')"
          title="Chế độ Semi-Auto: Xác nhận nhanh"
        >
          SEMI
        </button>
        <button
          class="mode-btn auto-btn"
          :class="{ active: orderStore.config.execution_mode === 'FULL_AUTO' }"
          @click="orderStore.setExecutionMode('FULL_AUTO')"
          title="Chế độ Full-Auto: Tự động tính lot và mở lệnh"
        >
          <Zap :size="9" /> FULL AUTO
        </button>
      </div>

      <span v-if="orderStore.circuitBreaker?.active" class="circuit-breaker-badge" :title="orderStore.circuitBreaker.reason">
        <ShieldAlert :size="11" /> CIRCUIT BREAKER
      </span>

      <span class="read-only"><Radio :size="13" /> PAPER MODE · NO LIVE ORDERS</span>
    </section>

    <!-- Instrument Bar with Gold Price & View Context -->
    <section class="instrument-bar">
      <div class="instrument-title">
        <span class="asset-icon">Au</span>
        <div>
          <h1>XAUUSD</h1>
          <span>Gold / U.S. Dollar</span>
        </div>
      </div>

      <div class="instrument-price">
        <strong :class="priceDirection">{{ marketStore.lastPrice === null ? '--' : marketStore.lastPrice.toFixed(2) }}</strong>
        <span>
          {{
            streamConnected
              ? (marketStore.quote?.bid && marketStore.quote?.ask) || (marketStore.chartEvent?.price?.bid && marketStore.chartEvent?.price?.ask)
                ? `BID ${(marketStore.quote?.bid ?? marketStore.chartEvent?.price?.bid).toFixed(2)} · ASK ${(marketStore.quote?.ask ?? marketStore.chartEvent?.price?.ask).toFixed(2)} (SPD ${((marketStore.quote?.ask ?? marketStore.chartEvent?.price?.ask) - (marketStore.quote?.bid ?? marketStore.chartEvent?.price?.bid)).toFixed(2)})`
                : 'LIVE PRICE'
              : 'Awaiting market data'
          }}
        </span>
      </div>

      <!-- Timeframe selector on Cockpit; active view tag on other tabs -->
      <div v-if="activeTab === 'cockpit'" class="timeframes" role="group" aria-label="Chart timeframe">
        <button
          v-for="frame in ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']"
          :key="frame"
          :class="{ selected: marketStore.timeframe === frame }"
          @click="selectTimeframe(frame)"
        >
          {{ frame }}
        </button>
      </div>
      <div v-else class="view-indicator">
        <span class="active-view-tag">
          {{
            activeTab === 'orders'
              ? 'VIEW: ORDERS HISTORY'
              : activeTab === 'news'
              ? 'VIEW: NEWS & EVENTS'
              : activeTab === 'strategy'
              ? 'VIEW: STRATEGY & ANALYSIS'
              : activeTab === 'backtest'
              ? 'VIEW: BACKTEST LAB'
              : 'VIEW: SYSTEM SETTINGS'
          }}
        </span>
      </div>

      <div class="instrument-tools">
        <button class="text-button" @click="marketStore.refresh">
          <RefreshCw :size="14" /> Refresh
        </button>
        <button class="icon-button" aria-label="Help"><CircleHelp :size="16" /></button>
      </div>
    </section>

    <div v-if="marketStore.error" class="connection-notice">{{ marketStore.error }} · Kiểm tra backend và Docker services.</div>

    <!-- VIEW 1: TRADING COCKPIT -->
    <section v-if="activeTab === 'cockpit'" class="main-grid">
      <div class="chart-column">
        <div class="chart-panel">
          <ChartOverlayControls v-model:show-volume="showVolume" />
          <TradingViewChart
            :symbol="marketStore.symbol"
            :timeframe="marketStore.timeframe"
            :candles="marketStore.candles"
            :event="marketStore.chartEvent"
            :orders="orderStore.orders"
            :show-volume="showVolume"
            :last-price="marketStore.lastPrice"
          />
          <div class="chart-foot">
            <span>{{ marketStore.candles.length ? `${marketStore.candles.length} bars loaded` : 'NO HISTORICAL DATA' }}</span>
            <span>ICT (UTC+7, Vietnam) · {{ marketStore.timeframe }}</span>
          </div>
        </div>
        <MetricsCards :orders="orderStore.orders" />
        <OrderBookTable :orders="orderStore.orders" />
        <MarketAnalysisStatus
          :symbol="marketStore.symbol"
          :last-price="marketStore.lastPrice"
          :account="orderStore.account"
        />
      </div>
      <aside class="right-column">
        <InsightsPanel @open-strategy="activeTab = 'strategy'" />
        <SentimentGauge :news="orderStore.news" />
        <NewsStream
          :news="orderStore.news"
          :events="orderStore.events"
          :sources="orderStore.sources"
          @navigate-calendar="openFullCalendar"
          @navigate-news="openFullNews"
        />
      </aside>
    </section>

    <!-- VIEW 2: ORDERS HISTORY -->
    <OrdersHistory
      v-else-if="activeTab === 'orders'"
      :orders="orderStore.orders"
    />

    <!-- VIEW 3: NEWS & EVENTS -->
    <NewsEventsView
      v-else-if="activeTab === 'news'"
      :news="orderStore.news"
      :events="orderStore.events"
      :sources="orderStore.sources"
      :initial-sub-tab="calendarInitialSubTab"
      @refresh="orderStore.refresh"
    />

    <!-- VIEW 4: STRATEGY & ANALYSIS -->
    <StrategyAnalysisView
      v-else-if="activeTab === 'strategy'"
      :candles="marketStore.candles"
      :last-price="marketStore.lastPrice"
      :timeframe="marketStore.timeframe"
      :news="orderStore.news"
      :events="orderStore.events"
      @navigate-cockpit="activeTab = 'cockpit'"
    />

    <!-- VIEW 5: BACKTEST LAB -->
    <BacktestLabView
      v-else-if="activeTab === 'backtest'"
    />

    <!-- VIEW 6: SETTINGS -->
    <SettingsView
      v-else-if="activeTab === 'settings'"
    />

    <footer class="footer">
      <span>FIELDNOTE MARKETS <b>·</b> STAGE 01</span>
      <span>Market data and simulated fills only. Not investment advice.</span>
    </footer>
  </main>
</template>