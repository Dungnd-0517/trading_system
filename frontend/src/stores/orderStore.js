import { reactive } from 'vue'
import {
  closeOrder as closeOrderApi,
  createOrder as createOrderApi,
  fetchEconomicEvents,
  fetchNews,
  fetchNewsStatus,
  fetchOrders,
  fetchSimulationAccount,
} from '../services/api'

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

  async refresh() {
    const [orders, news, events, sources, account] = await Promise.allSettled([
      fetchOrders(),
      fetchNews(),
      fetchEconomicEvents(),
      fetchNewsStatus(),
      fetchSimulationAccount(),
    ])
    if (orders.status === 'fulfilled') this.orders = orders.value
    if (news.status === 'fulfilled') this.news = news.value
    if (events.status === 'fulfilled') this.events = events.value
    if (sources.status === 'fulfilled') this.sources = sources.value
    if (account.status === 'fulfilled') this.account = account.value
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
})