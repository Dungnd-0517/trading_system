import { reactive } from 'vue'
import { fetchHealth, fetchHistory } from '../services/api'

export const marketStore = reactive({
  symbol: 'XAUUSD',
  timeframe: 'M1',
  candles: [],
  chartEvent: null,
  lastPrice: null,
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
    if (event.symbol !== this.symbol || event.timeframe !== this.timeframe) return
    this.chartEvent = event
    this.lastPrice = event.price.value
  },
})