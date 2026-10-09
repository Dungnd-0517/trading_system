import { reactive } from 'vue'
import {
  closeOrder as closeOrderApi,
  createOrder as createOrderApi,
  executeSignal as executeSignalApi,
  fetchEconomicEvents,
  fetchNews,
  fetchNewsStatus,
  fetchOrders,
  fetchSignals as fetchSignalsApi,
  fetchSimulationAccount,
  fetchTradingConfig,
  partialCloseOrder as partialCloseOrderApi,
  updateTradingConfig,
} from '../services/api'

function playSignalSound() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(587.33, ctx.currentTime) // Note D5
    osc.frequency.setValueAtTime(880.0, ctx.currentTime + 0.12) // Note A5
    gain.gain.setValueAtTime(0.12, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.45)
  } catch {
    // Ignore autoplay restriction errors
  }
}

export const orderStore = reactive({
  orders: [],
  account: {
    initial_balance: 10000.0,
    current_balance: 10000.0,
    equity: 10000.0,
    margin_used: 0.0,
    free_margin: 10000.0,
    open_positions_count: 0,
  },
  news: [],
  events: [],
  sources: {},
  signals: [],
  config: {
    execution_mode: 'MANUAL',
    risk_per_trade_percent: 1.0,
    breakeven_r_multiple: 1.5,
    enable_partial_tp: true,
    partial_tp_ratio: 0.5,
    partial_tp_r_multiple: 2.0,
    news_circuit_breaker_enabled: true,
    news_circuit_breaker_buffer_mins: 30,
    max_open_positions: 2,
  },
  circuitBreaker: {
    active: false,
    reason: null,
    event: null,
  },
  lastSignalAlert: null,

  async refresh() {
    const [orders, news, events, sources, account, config, signals] = await Promise.allSettled([
      fetchOrders(),
      fetchNews(),
      fetchEconomicEvents(),
      fetchNewsStatus(),
      fetchSimulationAccount(),
      fetchTradingConfig(),
      fetchSignalsApi(20),
    ])
    if (orders.status === 'fulfilled') this.orders = orders.value
    if (news.status === 'fulfilled') this.news = news.value
    if (events.status === 'fulfilled') this.events = events.value
    if (sources.status === 'fulfilled') this.sources = sources.value
    if (account.status === 'fulfilled') this.account = account.value
    if (config.status === 'fulfilled') this.config = { ...this.config, ...config.value }
    if (signals.status === 'fulfilled') this.signals = signals.value
  },

  async refreshAccount() {
    try {
      this.account = await fetchSimulationAccount()
    } catch {
      // keep existing account state
    }
  },

  async refreshSources() {
    try {
      this.sources = await fetchNewsStatus()
    } catch {
      this.sources = {}
    }
  },

  async submitOrder(orderData) {
    const res = await createOrderApi(orderData)
    await this.refresh()
    return res
  },

  async closeOrder(orderId, reason = 'MANUAL_CLOSE') {
    try {
      const closed = await closeOrderApi(orderId, reason)
      this.applyOrderUpdate({ event: 'ORDER_CLOSED', data: closed })
      await this.refreshAccount()
      return closed
    } catch (err) {
      console.error('Failed to close order:', err)
      throw err
    }
  },

  async partialCloseOrder(orderId, ratio = 0.5, reason = 'MANUAL_PARTIAL_TP') {
    try {
      const res = await partialCloseOrderApi(orderId, ratio, reason)
      await this.refresh()
      return res
    } catch (err) {
      console.error('Failed to partial close order:', err)
      throw err
    }
  },

  async fetchSignals(limit = 50, status = '') {
    try {
      const data = await fetchSignalsApi(limit, status)
      this.signals = data
      return data
    } catch (err) {
      console.error('Failed to fetch signals:', err)
      throw err
    }
  },

  async executeSignal(signalId) {
    try {
      const res = await executeSignalApi(signalId)
      await this.refresh()
      return res
    } catch (err) {
      console.error('Failed to execute signal:', err)
      throw err
    }
  },

  async setExecutionMode(mode) {
    try {
      const res = await updateTradingConfig({ execution_mode: mode })
      this.config.execution_mode = mode
      return res
    } catch (err) {
      console.error('Failed to update execution mode:', err)
      throw err
    }
  },

  async updateConfig(newConfig) {
    try {
      const res = await updateTradingConfig(newConfig)
      this.config = { ...this.config, ...res.config }
      return res
    } catch (err) {
      console.error('Failed to update config:', err)
      throw err
    }
  },

  applyOrderUpdate(message) {
    if (!message?.data) return
    const incoming = message.data
    const index = this.orders.findIndex((item) => item.id === incoming.id)
    if (index === -1) {
      this.orders.unshift(incoming)
    } else {
      this.orders.splice(index, 1, { ...this.orders[index], ...incoming })
    }
    if (this.orders.length > 200) this.orders.length = 200
    this.refreshAccount()
  },

  applyNewsUpdate(message) {
    const target = message.kind === 'economic_event' ? this.events : this.news
    const incoming = message.data
    const index = target.findIndex((item) => item.id === incoming.id)
    if (index === -1) target.unshift(incoming)
    else target.splice(index, 1, incoming)
    if (target.length > 200) target.length = 200
  },

  applySignalUpdate(message) {
    if (!message?.data) return
    const sig = message.data
    const idx = this.signals.findIndex((s) => s.id === sig.id)
    if (idx === -1) {
      this.signals.unshift(sig)
    } else {
      this.signals.splice(idx, 1, { ...this.signals[idx], ...sig })
    }
    this.lastSignalAlert = sig
    playSignalSound()
  },

  applyCircuitBreakerUpdate(message) {
    this.circuitBreaker = {
      active: Boolean(message.active),
      reason: message.reason || null,
      event: message.event || null,
    }
  },
})

export const useOrderStore = () => orderStore
export default orderStore