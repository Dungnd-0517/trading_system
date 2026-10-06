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
  applyChartUpdate(event) {
    if (event.symbol !== this.symbol) return
    if (event.price) {
      this.lastPrice = event.price.bid ?? event.price.value
      this.quote = event.price
    }
    if (event.timeframe === this.timeframe) {
      this.chartEvent = event
    }
  },
})