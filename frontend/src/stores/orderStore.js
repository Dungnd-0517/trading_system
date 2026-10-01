import { reactive } from 'vue'
import { fetchNews, fetchOrders } from '../services/api'

export const orderStore = reactive({
  orders: [],
  news: [],
  async refresh() {
    try {
      const [orders, news] = await Promise.all([fetchOrders(), fetchNews()])
      this.orders = orders
      this.news = news
    } catch {
      this.orders = []
      this.news = []
    }
  },
})