import { reactive } from 'vue'
import { fetchHealth, fetchHistory } from '../services/api'

export const marketStore = reactive({
  symbol: 'XAUUSD',
  timeframe: 'M1',
  candles: [],
  chartEvent: null,
  lastPrice: null,
  quote: null,
  health: null,
  loading: false,
  error: '',
  _pollTimer: null,
  _syncing: false,

  async refresh() {
    this.loading = true
    try {
      const [candles, health] = await Promise.all([
        fetchHistory(this.symbol, this.timeframe),
        fetchHealth(),
      ])
      this.candles = candles
      this.health = health
      this.error = ''
    } catch {
      this.error = 'API chưa kết nối'
      this.health = null
    } finally {
      this.loading = false
    }
  },

  async syncHistory() {
    if (this._syncing) return
    this._syncing = true
    try {
      const candles = await fetchHistory(this.symbol, this.timeframe)
      if (Array.isArray(candles) && candles.length > 0) {
        const curLen = this.candles.length
        const newLen = candles.length
        if (curLen === 0 || curLen !== newLen) {
          this.candles = candles
        } else {
          const curLast = this.candles[curLen - 1]
          const newLast = candles[newLen - 1]
          if (
            curLast.time !== newLast.time ||
            curLast.close !== newLast.close ||
            curLast.high !== newLast.high ||
            curLast.low !== newLast.low ||
            curLast.open !== newLast.open ||
            curLast.volume !== newLast.volume
          ) {
            this.candles = candles
          }
        }
      }
    } catch {
      // Background sync retry silently
    } finally {
      this._syncing = false
    }
  },

  startPolling(intervalMs = 2500) {
    this.stopPolling()
    this._pollTimer = setInterval(() => {
      this.syncHistory()
    }, intervalMs)
  },

  stopPolling() {
    if (this._pollTimer) {
      clearInterval(this._pollTimer)
      this._pollTimer = null
    }
  },

  applyChartUpdate(event) {
    if (event.symbol !== this.symbol) return
    if (event.price) {
      this.lastPrice = event.price.bid ?? event.price.value
      this.quote = event.price
    }
    if (event.timeframe === this.timeframe) {
      this.chartEvent = event
      if (event.candle && Array.isArray(this.candles) && this.candles.length > 0) {
        const candleTime = Number(event.candle.time)
        const last = this.candles[this.candles.length - 1]
        const lastTime = Number(last.time)
        const updated = {
          time: candleTime,
          open: Number(event.candle.open),
          high: Number(event.candle.high),
          low: Number(event.candle.low),
          close: Number(event.candle.close),
          volume: Number(event.volume?.value ?? last.volume ?? 0),
        }
        if (candleTime === lastTime) {
          this.candles[this.candles.length - 1] = updated
        } else if (candleTime > lastTime) {
          this.candles.push(updated)
          if (this.candles.length > 500) {
            this.candles.shift()
          }
        }
      }
    }
  },
})