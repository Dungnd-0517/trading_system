import { reactive } from 'vue'
import { fetchEconomicEvents, fetchNews, fetchNewsStatus, fetchOrders } from '../services/api'

export const orderStore = reactive({
  orders: [],
  news: [],
  events: [],
  sources: {},
  async refresh() {
    const [orders, news, events, sources] = await Promise.allSettled([
      fetchOrders(), fetchNews(), fetchEconomicEvents(), fetchNewsStatus(),
    ])
    if (orders.status === 'fulfilled') this.orders = orders.value
    if (news.status === 'fulfilled') this.news = news.value
    if (events.status === 'fulfilled') this.events = events.value
    if (sources.status === 'fulfilled') this.sources = sources.value
  },
  async refreshSources() {
    try {
      this.sources = await fetchNewsStatus()
    } catch {
      this.sources = {}
    }
  },
  applyNewsUpdate(message) {
    const target = message.kind === 'economic_event' ? this.events : this.news
    const incoming = message.data
    const index = target.findIndex((item) => item.id === incoming.id)
    if (index === -1) target.unshift(incoming)
    else target.splice(index, 1, incoming)
    if (target.length > 200) target.length = 200
  },
})