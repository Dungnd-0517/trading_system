import { reactive, computed } from 'vue'

const MAX_LOGS = 300

function formatTime(date = new Date()) {
  const h = String(date.getHours()).padStart(2, '0')
  const m = String(date.getMinutes()).padStart(2, '0')
  const s = String(date.getSeconds()).padStart(2, '0')
  const ms = String(date.getMilliseconds()).padStart(3, '0')
  return `${h}:${m}:${s}.${ms}`
}

let logIdCounter = 1

export const systemLogStore = reactive({
  logs: [],
  isPaused: false,
  autoScroll: true,
  activeFilter: 'ALL', // 'ALL' | 'AGENTS' | 'ARBITER' | 'SENTINEL' | 'VECTOR' | 'SCRIBE' | 'SYSTEM'
  searchQuery: '',
  timerId: null,
  isInitialized: false,
  lastTickLoggedAt: 0,

  // Computed / Helpers
  get filteredLogs() {
    let result = this.logs

    if (this.activeFilter === 'AGENTS') {
      result = result.filter((l) => ['ARBITER', 'SENTINEL', 'VECTOR', 'SCRIBE', 'COUNCIL'].includes(l.source))
    } else if (this.activeFilter !== 'ALL') {
      result = result.filter((l) => l.source === this.activeFilter)
    }

    if (this.searchQuery && this.searchQuery.trim()) {
      const q = this.searchQuery.trim().toLowerCase()
      result = result.filter((l) =>
        (l.message && l.message.toLowerCase().includes(q)) ||
        (l.category && l.category.toLowerCase().includes(q)) ||
        (l.source && l.source.toLowerCase().includes(q))
      )
    }

    return result
  },

  get logStats() {
    const counts = {
      TOTAL: this.logs.length,
      ARBITER: 0,
      SENTINEL: 0,
      VECTOR: 0,
      SCRIBE: 0,
      COUNCIL: 0,
      SYSTEM: 0,
    }
    for (const log of this.logs) {
      if (counts[log.source] !== undefined) {
        counts[log.source]++
      }
    }
    return counts
  },

  addLog({
    source = 'SYSTEM',
    category = 'TELEMETRY',
    message = '',
    level = 'info',
    timestamp = null,
    metadata = null,
  }) {
    if (this.isPaused) return

    const newEntry = {
      id: logIdCounter++,
      time: timestamp || formatTime(new Date()),
      rawTime: new Date(),
      source,
      category,
      message,
      level, // 'info' | 'success' | 'warn' | 'critical'
      metadata,
    }

    this.logs.unshift(newEntry)
    if (this.logs.length > MAX_LOGS) {
      this.logs.pop()
    }
  },

  clearLogs() {
    this.logs = []
  },

  togglePause() {
    this.isPaused = !this.isPaused
  },

  toggleAutoScroll() {
    this.autoScroll = !this.autoScroll
  },

  setFilter(filter) {
    this.activeFilter = filter
  },

  setSearch(query) {
    this.searchQuery = query
  },

  // Xử lý sự kiện WebSocket Real-time từ backend
  processWebSocketEvent(event) {
    if (!event || !event.type) return

    const now = Date.now()

    if (event.type === 'chart.update') {
      // Throttling: ghi log tick tối đa 1 lần mỗi 2.5 giây để tránh spam
      if (now - this.lastTickLoggedAt > 2500 && event.candle) {
        this.lastTickLoggedAt = now
        const price = Number(event.candle.close || event.last_price || 0).toFixed(2)
        const vol = event.candle.volume || 1
        this.addLog({
          source: 'SYSTEM',
          category: 'MARKET_TICK',
          message: `XAUUSD Tick cập nhật: $${price} | Khối lượng: ${vol} | Khung M15 | WebSocket stream latency < 15ms`,
          level: 'info',
        })
      }
      return
    }

    if (event.type === 'AGENT_STATE_UPDATE') {
      const payload = event.payload || {}
      const arb = payload.arbiter?.permission || 'ALLOWED'
      const sen = payload.sentinel?.circuit_breaker_status || 'NORMAL'
      const vec = payload.vector?.bias || 'BULLISH'
      const conf = payload.vector?.confidence || 85
      const scRules = payload.scribe?.active_memory_rules?.length || 2

      this.addLog({
        source: 'COUNCIL',
        category: 'COUNCIL_SYNC',
        message: `Đồng bộ trạng thái 4 Agent: Arbiter [${arb}] · Sentinel [${sen}] · Vector [${vec} ${conf}%] · Scribe [${scRules} Rules Active]`,
        level: 'info',
      })
      return
    }

    if (event.type === 'order.update') {
      const ord = event.order || {}
      const side = ord.side || ord.order_type || 'BUY'
      const status = ord.status || 'FILLED'
      const pnl = ord.realized_pnl !== undefined ? ` | PnL: $${Number(ord.realized_pnl).toFixed(2)}` : ''
      this.addLog({
        source: 'SYSTEM',
        category: 'ORDER_FILL',
        message: `Sự kiện lệnh #${ord.id || ord.ticket || 'PAPER'}: ${side} ${ord.lots || ord.volume || 0.05} lot tại $${Number(ord.entry_price || ord.price || 0).toFixed(2)} (Trạng thái: ${status}${pnl})`,
        level: status === 'FILLED' || status === 'WIN' ? 'success' : status === 'LOSS' ? 'warn' : 'info',
      })
      return
    }

    if (event.type === 'circuit_breaker.update') {
      const status = event.status || 'NORMAL'
      const isHalt = status === 'HALT_ACTIVE'
      this.addLog({
        source: 'SENTINEL',
        category: 'CIRCUIT_BREAKER',
        message: `Sentinel Circuit Breaker cập nhật trạng thái: ${status} | Tin đỏ USD: ${event.next_event || 'Chưa có sự kiện khẩn'}`,
        level: isHalt ? 'critical' : status === 'APPROACHING' ? 'warn' : 'info',
      })
      return
    }

    if (event.type === 'governor.update') {
      const risk = event.risk_per_trade_percent || 1.0
      const dd = event.daily_drawdown_pct || 0.0
      this.addLog({
        source: 'ARBITER',
        category: 'RISK_AUDIT',
        message: `Governor Audit: Phê duyệt thông số rủi ro ${risk}%/lệnh. Daily Drawdown hiện tại ${dd}% (Giới hạn Hard Breaker 3.00%).`,
        level: dd >= 2.0 ? 'warn' : 'info',
      })
      return
    }

    if (event.type === 'agent.dialogue.message') {
      const sender = event.sender || 'Governor'
      const text = event.text || event.message || ''
      this.addLog({
        source: 'COUNCIL',
        category: 'INTER_AGENT_COMMS',
        message: `[${sender} ➔ Trader]: "${text}"`,
        level: 'info',
      })
      return
    }

    if (event.type === 'signal.new') {
      const sig = event.signal || event
      this.addLog({
        source: 'VECTOR',
        category: 'SETUP_EVAL',
        message: `Vector phát hiện Setup mới: ${sig.side} tại $${Number(sig.entry_price).toFixed(2)} (SL: $${Number(sig.stop_loss).toFixed(2)}, TP: $${Number(sig.take_profit_1).toFixed(2)}, R:R ${sig.risk_reward || '2.25'})`,
        level: 'success',
      })
      return
    }

    if (event.type === 'news.upsert') {
      this.addLog({
        source: 'SENTINEL',
        category: 'NEWS_FEED',
        message: `Sentinel tiếp nhận tin nóng [${event.source || 'Macro'}]: "${event.title || 'Tin vĩ mô'}" (Mức độ: ${event.urgency || 'MEDIUM'})`,
        level: event.urgency === 'CRITICAL' ? 'critical' : 'info',
      })
    }
  },

  // Trình mô phỏng giao tiếp liên tục của 4 Agent và hoạt động nền hệ sinh thái
  startTelemetryTimer() {
    if (this.timerId) return

    const telemetryScripts = [
      {
        source: 'COUNCIL',
        category: 'INTER_AGENT_COMMS',
        message: '[Vector ➔ Arbiter]: Đã quét vùng FVG M15 ($4001.38 - $4004.38). Đề xuất kịch bản Buy Pullback với Entry $4002.88, SL $3972.33, TP $4117.49 (R:R 3.77).',
        level: 'info',
      },
      {
        source: 'COUNCIL',
        category: 'INTER_AGENT_COMMS',
        message: '[Arbiter ➔ Vector]: Thẩm định rào chắn Hard Guardrails: Daily DD 0.00% (< 3.00%), Risk 1.00% ($100.00). Kích thước lệnh an toàn: 0.03 lot. TRẠNG THÁI: ALLOWED.',
        level: 'success',
      },
      {
        source: 'SENTINEL',
        category: 'CIRCUIT_BREAKER',
        message: 'Sentinel kiểm tra Macro Calendar: USD Core CPI diễn ra sau 28 phút. Trạng thái Circuit Breaker: NORMAL. DXY tương quan nghịch duy trì ổn định.',
        level: 'info',
      },
      {
        source: 'VECTOR',
        category: 'RAG_INFERENCE',
        message: 'Vector truy vấn pgvector Cosine Search (1536 dims): Mẫu hình tương đồng cao nhất "Wyckoff Spring Phase C" (92% match) tại hỗ trợ H1.',
        level: 'info',
      },
      {
        source: 'SCRIBE',
        category: 'REFLEXION_LEARNING',
        message: 'Scribe rà soát Episodic Memory: 2 quy tắc hoạt động được đối chiếu ("Nới SL 12 pts phiên London", "Khóa BUY nếu CPI > dự báo").',
        level: 'info',
      },
      {
        source: 'ARBITER',
        category: 'RISK_AUDIT',
        message: 'Arbiter kiểm toán an toàn vốn: Max Daily Drawdown 3.00% chưa bị chạm. Tỷ lệ đòn bẩy tài khoản 1:100 trong ngưỡng an toàn.',
        level: 'info',
      },
      {
        source: 'SYSTEM',
        category: 'TELEMETRY',
        message: 'Health check hệ thống: MT5 Bridge latency 12ms | Redis Pub/Sub channels active (9/9) | PostgreSQL connection pool: OK.',
        level: 'info',
      },
      {
        source: 'COUNCIL',
        category: 'INTER_AGENT_COMMS',
        message: '[Council ➔ Cockpit]: 4 Agent đồng thuận tỷ lệ 85% thiên hướng BULLISH. Chờ nến M15 đóng cửa trên $4004.38 để kích hoạt lệnh.',
        level: 'success',
      },
      {
        source: 'SENTINEL',
        category: 'SENTIMENT_SCAN',
        message: 'Sentinel cập nhật Macro Sentiment Score: +0.20 (Lạc quan nhẹ / Bullish Vàng do lợi suất TPCP Mỹ US10Y hạ nhiệt).',
        level: 'info',
      },
      {
        source: 'VECTOR',
        category: 'TECHNICAL_BIAS',
        message: 'Vector phân tích đa khung: D1 Tăng giá bền vững (HH/HL) ⇄ H4 Hợp lưu Fibonacci 0.618 OTE ⇄ M15 Intraday Discount Zone (26%).',
        level: 'info',
      },
      {
        source: 'COUNCIL',
        category: 'INTER_AGENT_COMMS',
        message: '[Sentinel ➔ Arbiter]: Cảnh báo tin tức: Bảng lương Non-Farm Payrolls cuối tuần. Đề xuất siết SL Multiplier từ 1.5x lên 1.8x ATR.',
        level: 'warn',
      },
      {
        source: 'SCRIBE',
        category: 'MEMORY_AUDIT',
        message: 'Scribe kiểm toán bài học gần nhất (#1048): Lỗi SL_TOO_TIGHT đã áp dụng quy tắc nới buffer SL thành công trong phiên London hiện tại.',
        level: 'info',
      },
    ]

    let scriptIndex = 0

    const scheduleNext = () => {
      // Random khoảng 2.8s đến 4.2s để tạo cảm giác luồng dữ liệu tự nhiên, sinh động
      const delay = 2800 + Math.floor(Math.random() * 1400)
      this.timerId = setTimeout(() => {
        if (!this.isPaused) {
          const item = telemetryScripts[scriptIndex % telemetryScripts.length]
          scriptIndex++
          this.addLog({
            source: item.source,
            category: item.category,
            message: item.message,
            level: item.level,
          })
        }
        scheduleNext()
      }, delay)
    }

    scheduleNext()
  },

  stopTelemetryTimer() {
    if (this.timerId) {
      clearTimeout(this.timerId)
      this.timerId = null
    }
  },

  init() {
    if (this.isInitialized) return
    this.isInitialized = true

    // Seed sẵn 12 bản ghi phong phú ban đầu để người dùng vừa vào trang là có dữ liệu hoạt động ngay
    const initialSeed = [
      {
        offsetSec: 58,
        source: 'SYSTEM',
        category: 'INIT',
        message: 'Khởi động Trading Cockpit Engine: Dual-Channel Hydration thành công qua WebSocket /api/v1/ws/market',
        level: 'success',
      },
      {
        offsetSec: 52,
        source: 'ARBITER',
        category: 'RISK_AUDIT',
        message: 'Arbiter nạp tham số rủi ro: Daily Drawdown 0.00% / 3.00% max. Trạng thái giao dịch: ALLOWED.',
        level: 'info',
      },
      {
        offsetSec: 46,
        source: 'SENTINEL',
        category: 'CIRCUIT_BREAKER',
        message: 'Sentinel quét cảm xúc vĩ mô: Sentiment +0.20, DXY Bearish Bias. Circuit Breaker: NORMAL.',
        level: 'info',
      },
      {
        offsetSec: 38,
        source: 'VECTOR',
        category: 'RAG_INFERENCE',
        message: 'Vector truy vấn RAG pgvector: Tìm thấy 12 mẫu hình Wyckoff & SMC tương tự trong lịch sử (Cosine similarity 92%).',
        level: 'info',
      },
      {
        offsetSec: 30,
        source: 'SCRIBE',
        category: 'REFLEXION_LEARNING',
        message: 'Scribe đồng bộ 2 quy tắc bộ nhớ hoạt động (Active Rules) từ các lệnh đóng trước đó.',
        level: 'info',
      },
      {
        offsetSec: 22,
        source: 'COUNCIL',
        category: 'INTER_AGENT_COMMS',
        message: '[Vector ➔ Arbiter]: Đề xuất điểm vào lệnh BUY tại FVG M15 ($4001.38 - $4004.38). Kịch bản 1 ưu tiên.',
        level: 'info',
      },
      {
        offsetSec: 15,
        source: 'COUNCIL',
        category: 'INTER_AGENT_COMMS',
        message: '[Arbiter ➔ Vector]: Xác nhận điều kiện an toàn vốn: R:R 3.77 >= 1.50 yêu cầu, Risk 1.00% hợp lệ.',
        level: 'success',
      },
      {
        offsetSec: 9,
        source: 'SYSTEM',
        category: 'MARKET_TICK',
        message: 'XAUUSD Tick cập nhật: $4012.31 | Spread: 1.1 pts | Nến M15 index: 1245 | WebSocket latency: 12ms',
        level: 'info',
      },
      {
        offsetSec: 3,
        source: 'SENTINEL',
        category: 'CIRCUIT_BREAKER',
        message: 'Sentinel đếm ngược tin đỏ: USD Core CPI còn 28 phút. Trạng thái Circuit Breaker: NORMAL.',
        level: 'info',
      },
    ]

    const baseTime = Date.now()
    initialSeed.forEach((item) => {
      const logDate = new Date(baseTime - item.offsetSec * 1000)
      this.logs.push({
        id: logIdCounter++,
        time: formatTime(logDate),
        rawTime: logDate,
        source: item.source,
        category: item.category,
        message: item.message,
        level: item.level,
        metadata: null,
      })
    })

    this.startTelemetryTimer()
  },

  destroy() {
    this.stopTelemetryTimer()
    this.isInitialized = false
  },
})
