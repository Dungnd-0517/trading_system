<script setup>
import { computed, ref, onMounted } from 'vue'
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BookOpen,
  Brain,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  Layers,
  Lock,
  Maximize2,
  Minimize2,
  Newspaper,
  Radar,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Unlock,
  XCircle,
  Zap,
} from 'lucide-vue-next'
import { agentStore } from '../../stores/agentStore'

const emit = defineEmits(['open-knowledge', 'open-strategy', 'open-dialogue'])

// Card collapse state (mặc định mở cả 4 panel để quan sát toàn diện)
const openPanels = ref({
  arbiter: true,
  sentinel: true,
  vector: true,
  scribe: true,
})

const isHalting = ref(false)

const togglePanel = (panelName) => {
  openPanels.value[panelName] = !openPanels.value[panelName]
}

const areAllExpanded = computed(() =>
  Object.values(openPanels.value).every(Boolean)
)

const toggleAllPanels = () => {
  const target = !areAllExpanded.value
  openPanels.value = {
    arbiter: target,
    sentinel: target,
    vector: target,
    scribe: target,
  }
}

// Dữ liệu từ store
const dashboard = computed(() => agentStore.dashboard)
const arbiter = computed(() => dashboard.value.arbiter)
const sentinel = computed(() => dashboard.value.sentinel)
const vector = computed(() => dashboard.value.vector)
const scribe = computed(() => dashboard.value.scribe)
const loading = computed(() => dashboard.value.loading)
const lastUpdated = computed(() => dashboard.value.lastUpdated)

// 1. Arbiter Helpers
const isAllowed = computed(() => arbiter.value?.permission === 'ALLOWED')
const isRestricted = computed(() => arbiter.value?.permission === 'RESTRICTED')
const isBlocked = computed(() => arbiter.value?.permission === 'BLOCKED')

const arbiterBadge = computed(() => {
  if (isAllowed.value) {
    return { label: 'ALLOWED', cls: 'badge-allowed', icon: ShieldCheck }
  }
  if (isRestricted.value) {
    return { label: 'RESTRICTED', cls: 'badge-restricted', icon: ShieldAlert }
  }
  return { label: 'BLOCKED', cls: 'badge-blocked', icon: Lock }
})

const drawdownPct = computed(() => {
  const val = Number(arbiter.value?.daily_drawdown_pct ?? 0)
  return isNaN(val) ? 0 : Math.max(0, val)
})

const drawdownWidth = computed(() => {
  // Max limit là 3.0%
  const pct = (drawdownPct.value / 3.0) * 100
  return Math.min(100, Math.max(0, pct))
})

const riskWidth = computed(() => {
  // Risk từ 0.25% đến 1.50%
  const risk = Number(arbiter.value?.current_risk_percent ?? 1.0)
  const pct = ((risk - 0.25) / (1.50 - 0.25)) * 100
  return Math.min(100, Math.max(0, pct))
})

const handleToggleEmergencyHalt = async () => {
  isHalting.value = true
  try {
    await agentStore.toggleEmergencyHalt(
      isAllowed.value ? 'Khóa khẩn cấp từ Bàn điều hành Trader' : null
    )
  } catch (err) {
    console.error('Lỗi khi kích hoạt Emergency Halt:', err)
  } finally {
    isHalting.value = false
  }
}

// 2. Sentinel Helpers
const circuitBreakerBadge = computed(() => {
  const status = sentinel.value?.circuit_breaker_status || 'NORMAL'
  if (status === 'HALT_ACTIVE' || sentinel.value?.circuit_breaker_active) {
    return { label: 'HALT ACTIVE', cls: 'badge-halt', icon: AlertTriangle }
  }
  if (status === 'APPROACHING') {
    return { label: 'APPROACHING', cls: 'badge-approaching', icon: Clock }
  }
  return { label: 'NORMAL', cls: 'badge-normal', icon: CheckCircle2 }
})

const sentimentScore = computed(() => {
  const score = Number(sentinel.value?.sentiment_score ?? 0)
  return isNaN(score) ? 0 : score
})

const sentimentPercentPosition = computed(() => {
  // Score từ -1.0 tới +1.0 -> map sang 0% tới 100%
  const clamped = Math.max(-1, Math.min(1, sentimentScore.value))
  return ((clamped + 1) / 2) * 100
})

const sentimentLabel = computed(() => {
  const s = sentimentScore.value
  if (s > 0.2) return { text: `Bullish (+${s.toFixed(2)})`, cls: 'txt-bullish' }
  if (s < -0.2) return { text: `Bearish (${s.toFixed(2)})`, cls: 'txt-bearish' }
  return { text: `Neutral (${s.toFixed(2)})`, cls: 'txt-neutral' }
})

const dxyBadge = computed(() => {
  const bias = sentinel.value?.dxy_bias || 'NEUTRAL'
  if (bias === 'BEARISH_DXY') {
    return { label: 'DXY WEAK (VÀNG +)', cls: 'dxy-gold-pos' }
  }
  if (bias === 'BULLISH_DXY') {
    return { label: 'DXY STRONG (VÀNG -)', cls: 'dxy-gold-neg' }
  }
  return { label: 'DXY NEUTRAL', cls: 'dxy-neutral' }
})

const formatCountdown = (seconds) => {
  if (!seconds || seconds <= 0) return 'Đang diễn ra'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins > 60) {
    const hours = Math.floor(mins / 60)
    return `${hours}h ${mins % 60}m`
  }
  return `${mins}m ${secs}s`
}

// 3. Vector Helpers
const vectorBiasBadge = computed(() => {
  const bias = vector.value?.bias || 'NEUTRAL'
  if (bias === 'BULLISH') return { label: 'BULLISH', cls: 'bias-bullish', icon: TrendingUp }
  if (bias === 'BEARISH') return { label: 'BEARISH', cls: 'bias-bearish', icon: TrendingDown }
  return { label: 'NEUTRAL', cls: 'bias-neutral', icon: Activity }
})

const vectorRegimeLabel = computed(() => {
  const r = vector.value?.regime || 'COMPRESSION_CHOP'
  if (r === 'TRENDING_EXPANSION') return 'TRENDING'
  if (r === 'HIGH_VOLATILITY') return 'VOLATILE'
  return 'CHOP / NÉN'
})

const confidenceVal = computed(() => {
  const val = Number(vector.value?.confidence ?? 50)
  return Math.min(100, Math.max(0, val))
})

const ragSimilarityVal = computed(() => {
  const val = Number(vector.value?.rag_similarity ?? 0)
  return Math.min(100, Math.max(0, val))
})

// 4. Scribe Helpers
const lastTrade = computed(() => scribe.value?.last_trade)
const hasTrade = computed(() => Boolean(lastTrade.value && lastTrade.value.id))

const lastTradeBadge = computed(() => {
  if (!hasTrade.value) return { label: 'NO TRADES', cls: 'outcome-neutral' }
  const outcome = lastTrade.value?.outcome || 'NONE'
  if (outcome === 'WIN') return { label: 'WIN', cls: 'outcome-win' }
  if (outcome === 'LOSS') return { label: 'LOSS', cls: 'outcome-loss' }
  return { label: outcome, cls: 'outcome-neutral' }
})

const formatPnl = (val) => {
  const num = Number(val || 0)
  const sign = num > 0 ? '+' : ''
  return `${sign}$${num.toFixed(2)}`
}

const activeRules = computed(() => scribe.value?.active_memory_rules || [])

const refreshCouncil = () => {
  agentStore.hydrateCouncilState()
}

onMounted(() => {
  // Nạp snapshot ban đầu nếu chưa có dữ liệu
  if (!lastUpdated.value) {
    agentStore.hydrateCouncilState()
  }
})
</script>

<template>
  <div class="council-deck" role="region" aria-label="Bàn điều hành Agent Council Deck">
    <!-- Header Bàn Điều Hành -->
    <div class="deck-topbar">
      <div class="deck-title-group">
        <span class="syndicate-icon">
          <Zap :size="14" />
        </span>
        <div>
          <h2 class="deck-title">COUNCIL DECK</h2>
          <span class="deck-subtitle">4-Agent Executive Syndicate</span>
        </div>
      </div>

      <div class="deck-actions">
        <button
          class="deck-btn"
          @click="toggleAllPanels"
          :title="areAllExpanded ? 'Thu gọn tất cả' : 'Mở rộng tất cả'"
          aria-label="Toggle all panels"
        >
          <Minimize2 v-if="areAllExpanded" :size="13" />
          <Maximize2 v-else :size="13" />
        </button>

        <button
          class="deck-btn"
          :class="{ spinning: loading }"
          @click="refreshCouncil"
          title="Làm mới trạng thái Hội đồng"
          aria-label="Refresh council state"
        >
          <RefreshCw :size="13" />
        </button>
      </div>
    </div>

    <!-- Thông báo kết nối / Last Updated -->
    <div class="deck-status-line">
      <span class="pulse-dot" :class="{ active: !loading }"></span>
      <span class="status-text">
        <template v-if="loading">Đang đồng bộ dữ liệu...</template>
        <template v-else-if="lastUpdated">
          Cập nhật: {{ lastUpdated.toLocaleTimeString() }}
        </template>
        <template v-else>Sẵn sàng kết nối stream</template>
      </span>
      <button class="hitl-link" @click="emit('open-dialogue')" title="Mở phòng đối thoại Trader - Governor">
        HITL Dialogue <ExternalLink :size="10" />
      </button>
    </div>

    <!-- DANH SÁCH 4 AGENT CARDS (ACCORDION) -->
    <div class="cards-stack">
      <!-- ================= 1. ARBITER PANEL ================= -->
      <article class="agent-card arbiter-card" :class="{ collapsed: !openPanels.arbiter }">
        <header class="card-header" @click="togglePanel('arbiter')">
          <div class="agent-id">
            <span class="agent-symbol symbol-arbiter">
              <ShieldCheck v-if="isAllowed" :size="14" />
              <ShieldAlert v-else :size="14" />
            </span>
            <div class="agent-names">
              <strong class="agent-code">ARBITER</strong>
              <small class="agent-role">Risk &amp; Guardrails</small>
            </div>
          </div>

          <div class="header-badges">
            <span class="badge" :class="arbiterBadge.cls">
              <component :is="arbiterBadge.icon" :size="11" />
              {{ arbiterBadge.label }}
            </span>
            <button class="chevron-btn" :aria-label="openPanels.arbiter ? 'Collapse Arbiter' : 'Expand Arbiter'">
              <ChevronUp v-if="openPanels.arbiter" :size="14" />
              <ChevronDown v-else :size="14" />
            </button>
          </div>
        </header>

        <div v-show="openPanels.arbiter" class="card-body">
          <!-- Meters Row: Risk & Drawdown -->
          <div class="metrics-grid">
            <div class="meter-box">
              <div class="meter-head">
                <span class="meter-label">RISK PER TRADE</span>
                <strong class="meter-val">{{ (arbiter?.current_risk_percent ?? 1.0).toFixed(2) }}%</strong>
              </div>
              <div class="meter-bar-track">
                <div class="meter-bar-fill fill-arbiter" :style="{ width: `${riskWidth}%` }"></div>
              </div>
              <div class="meter-sub">SL: {{ (arbiter?.sl_multiplier ?? 1.5).toFixed(2) }}x ATR</div>
            </div>

            <div class="meter-box">
              <div class="meter-head">
                <span class="meter-label">DAILY DRAWDOWN</span>
                <strong class="meter-val" :class="{ 'txt-warn': drawdownPct >= 2.0, 'txt-alert': drawdownPct >= 3.0 }">
                  {{ drawdownPct.toFixed(2) }}%
                </strong>
              </div>
              <div class="meter-bar-track">
                <div
                  class="meter-bar-fill"
                  :class="drawdownPct >= 2.5 ? 'fill-red' : drawdownPct >= 1.5 ? 'fill-amber' : 'fill-green'"
                  :style="{ width: `${drawdownWidth}%` }"
                ></div>
              </div>
              <div class="meter-sub">Rào cứng: 3.00% Max</div>
            </div>
          </div>

          <!-- Rationale -->
          <div class="rationale-box">
            <span class="box-tag">PHÁN QUYẾT:</span>
            <p class="rationale-text">{{ arbiter?.reason_summary || 'Chờ đánh giá từ Governor...' }}</p>
          </div>

          <!-- Action Nút Khẩn Cấp -->
          <div class="card-action-row">
            <button
              class="emergency-btn"
              :class="isAllowed ? 'btn-danger' : 'btn-resume'"
              :disabled="isHalting"
              @click="handleToggleEmergencyHalt"
            >
              <template v-if="isHalting">
                <RefreshCw :size="12" class="spinning" /> Đang gửi chỉ thị...
              </template>
              <template v-else-if="isAllowed">
                <Lock :size="12" /> KHÓA GIAO DỊCH KHẨN CẤP
              </template>
              <template v-else>
                <Unlock :size="12" /> MỞ LẠI QUYỀN GIAO DỊCH
              </template>
            </button>
          </div>
        </div>
      </article>

      <!-- ================= 2. SENTINEL PANEL ================= -->
      <article class="agent-card sentinel-card" :class="{ collapsed: !openPanels.sentinel }">
        <header class="card-header" @click="togglePanel('sentinel')">
          <div class="agent-id">
            <span class="agent-symbol symbol-sentinel">
              <Radar :size="14" />
            </span>
            <div class="agent-names">
              <strong class="agent-code">SENTINEL</strong>
              <small class="agent-role">Macro &amp; Breaker</small>
            </div>
          </div>

          <div class="header-badges">
            <span class="badge" :class="circuitBreakerBadge.cls">
              <component :is="circuitBreakerBadge.icon" :size="11" />
              {{ circuitBreakerBadge.label }}
            </span>
            <button class="chevron-btn" :aria-label="openPanels.sentinel ? 'Collapse Sentinel' : 'Expand Sentinel'">
              <ChevronUp v-if="openPanels.sentinel" :size="14" />
              <ChevronDown v-else :size="14" />
            </button>
          </div>
        </header>

        <div v-show="openPanels.sentinel" class="card-body">
          <!-- Sentiment Gauge & DXY -->
          <div class="sentiment-box">
            <div class="gauge-head">
              <span class="meter-label">MACRO SENTIMENT</span>
              <span class="gauge-val" :class="sentimentLabel.cls">{{ sentimentLabel.text }}</span>
            </div>

            <!-- Visual Gradient Bar with Pointer -->
            <div class="sentiment-track">
              <div class="zone-bearish" title="Bearish (-1.0 to -0.2)"></div>
              <div class="zone-neutral" title="Neutral (-0.2 to +0.2)"></div>
              <div class="zone-bullish" title="Bullish (+0.2 to +1.0)"></div>
              <div class="sentiment-needle" :style="{ left: `${sentimentPercentPosition}%` }"></div>
            </div>

            <div class="gauge-scale">
              <span>-1.0</span>
              <span>0.0</span>
              <span>+1.0</span>
            </div>
          </div>

          <!-- DXY & Next Event Row -->
          <div class="macro-sub-grid">
            <div class="sub-item">
              <span class="sub-label">DXY CORRELATION</span>
              <span class="tag-pill" :class="dxyBadge.cls">{{ dxyBadge.label }}</span>
            </div>

            <div class="sub-item">
              <span class="sub-label">SỰ KIỆN ĐỎ USD</span>
              <div v-if="sentinel?.next_event" class="event-brief">
                <span class="event-title" :title="sentinel.next_event.title">
                  {{ sentinel.next_event.title }}
                </span>
                <span class="event-clock">
                  <Clock :size="10" />
                  {{ formatCountdown(sentinel.next_event.countdown_seconds) }}
                </span>
              </div>
              <span v-else class="text-muted">Không có tin đỏ trong 24h</span>
            </div>
          </div>

          <!-- Recent News Mini Feed -->
          <div v-if="sentinel?.recent_news?.length" class="news-mini-feed">
            <span class="feed-title">TIN NÓNG GẦN NHẤT:</span>
            <div
              v-for="(n, idx) in sentinel.recent_news.slice(0, 2)"
              :key="n.id || idx"
              class="news-line"
            >
              <span
                class="urgency-tag"
                :class="n.urgency === 'CRITICAL' ? 'urg-crit' : n.urgency === 'HIGH' ? 'urg-high' : 'urg-med'"
              >
                {{ n.urgency || 'NEWS' }}
              </span>
              <span class="news-text" :title="n.title">{{ n.title }}</span>
              <small class="news-time">{{ n.time_ago || '' }}</small>
            </div>
          </div>
        </div>
      </article>

      <!-- ================= 3. VECTOR PANEL ================= -->
      <article class="agent-card vector-card" :class="{ collapsed: !openPanels.vector }">
        <header class="card-header" @click="togglePanel('vector')">
          <div class="agent-id">
            <span class="agent-symbol symbol-vector">
              <Layers :size="14" />
            </span>
            <div class="agent-names">
              <strong class="agent-code">VECTOR</strong>
              <small class="agent-role">Technical &amp; RAG</small>
            </div>
          </div>

          <div class="header-badges">
            <span class="badge" :class="vectorBiasBadge.cls">
              <component :is="vectorBiasBadge.icon" :size="11" />
              {{ vectorBiasBadge.label }}
            </span>
            <button class="chevron-btn" :aria-label="openPanels.vector ? 'Collapse Vector' : 'Expand Vector'">
              <ChevronUp v-if="openPanels.vector" :size="14" />
              <ChevronDown v-else :size="14" />
            </button>
          </div>
        </header>

        <div v-show="openPanels.vector" class="card-body">
          <!-- Bars: Confidence & RAG Similarity -->
          <div class="metrics-grid">
            <div class="meter-box">
              <div class="meter-head">
                <span class="meter-label">CONFIDENCE</span>
                <strong class="meter-val">{{ confidenceVal }}%</strong>
              </div>
              <div class="meter-bar-track">
                <div class="meter-bar-fill fill-blue" :style="{ width: `${confidenceVal}%` }"></div>
              </div>
              <div class="meter-sub">Trường phái: {{ vector?.primary_school || 'GENERAL' }}</div>
            </div>

            <div class="meter-box">
              <div class="meter-head">
                <span class="meter-label">RAG SIMILARITY</span>
                <strong class="meter-val txt-purple">{{ ragSimilarityVal }}%</strong>
              </div>
              <div class="meter-bar-track">
                <div class="meter-bar-fill fill-purple" :style="{ width: `${ragSimilarityVal}%` }"></div>
              </div>
              <div class="meter-sub">Regime: {{ vectorRegimeLabel }}</div>
            </div>
          </div>

          <!-- RAG Pattern Match -->
          <div v-if="vector?.pattern_match" class="rag-match-box">
            <div class="rag-match-head">
              <BookOpen :size="11" />
              <span class="box-tag">MẪU HÌNH KHỚP VECTOR:</span>
            </div>
            <p class="match-name">{{ vector.pattern_match }}</p>
          </div>

          <!-- Suggested Setup Box -->
          <div v-if="vector?.suggested_trade_setup" class="setup-box">
            <div class="setup-head">
              <span class="setup-act" :class="vector.suggested_trade_setup.action === 'BUY' ? 'act-buy' : 'act-sell'">
                SETUP: {{ vector.suggested_trade_setup.action }}
              </span>
              <span class="setup-rr">
                R:R {{ (vector.suggested_trade_setup.planned_risk_reward ?? 1.5).toFixed(2) }}
              </span>
            </div>

            <div class="setup-coords">
              <div class="coord-item">
                <span class="c-lbl">Zone</span>
                <span class="c-val">
                  {{ vector.suggested_trade_setup.entry_zone?.[0] || '—' }} - {{ vector.suggested_trade_setup.entry_zone?.[1] || '—' }}
                </span>
              </div>
              <div class="coord-item">
                <span class="c-lbl">SL</span>
                <span class="c-val txt-red">{{ vector.suggested_trade_setup.suggested_sl || '—' }}</span>
              </div>
              <div class="coord-item">
                <span class="c-lbl">TP</span>
                <span class="c-val txt-green">{{ vector.suggested_trade_setup.suggested_tp || '—' }}</span>
              </div>
            </div>

            <p v-if="vector.action_recommendation" class="setup-recom">
              {{ vector.action_recommendation }}
            </p>
          </div>
        </div>
      </article>

      <!-- ================= 4. SCRIBE PANEL ================= -->
      <article class="agent-card scribe-card" :class="{ collapsed: !openPanels.scribe }">
        <header class="card-header" @click="togglePanel('scribe')">
          <div class="agent-id">
            <span class="agent-symbol symbol-scribe">
              <Brain :size="14" />
            </span>
            <div class="agent-names">
              <strong class="agent-code">SCRIBE</strong>
              <small class="agent-role">Reflexion &amp; Memory</small>
            </div>
          </div>

          <div class="header-badges">
            <span class="badge" :class="lastTradeBadge.cls">
              {{ lastTradeBadge.label }}
            </span>
            <button class="chevron-btn" :aria-label="openPanels.scribe ? 'Collapse Scribe' : 'Expand Scribe'">
              <ChevronUp v-if="openPanels.scribe" :size="14" />
              <ChevronDown v-else :size="14" />
            </button>
          </div>
        </header>

        <div v-show="openPanels.scribe" class="card-body">
          <!-- Post-Mortem Card -->
          <div v-if="hasTrade" class="post-mortem-box">
            <div class="pm-head">
              <div class="pm-ticket">
                <strong>Lệnh #{{ lastTrade.id }}</strong>
                <span class="pm-type" :class="lastTrade.order_type === 'BUY' ? 'txt-bullish' : 'txt-bearish'">
                  {{ lastTrade.order_type }}
                </span>
              </div>
              <strong class="pm-pnl" :class="lastTrade.realized_pnl >= 0 ? 'txt-green' : 'txt-red'">
                {{ formatPnl(lastTrade.realized_pnl) }}
              </strong>
            </div>

            <div v-if="lastTrade.mistake_category" class="pm-mistake">
              <span class="mistake-badge">{{ lastTrade.mistake_category }}</span>
              <p v-if="lastTrade.root_cause" class="mistake-cause">{{ lastTrade.root_cause }}</p>
            </div>

            <div v-if="lastTrade.lesson_learned" class="pm-lesson">
              <span class="box-tag">BÀI HỌC REFLEXION:</span>
              <p class="lesson-text">{{ lastTrade.lesson_learned }}</p>
            </div>
          </div>

          <div v-else class="empty-scribe">
            <p>Chưa có dữ liệu lệnh vừa đóng. Scribe sẽ kích hoạt ngay khi lệnh kết thúc.</p>
          </div>

          <!-- Active Memory Rules -->
          <div v-if="activeRules.length" class="active-rules-box">
            <div class="rules-head">
              <span class="box-tag">QUY TẮC ĐÃ THĂNG CẤP BỘ NHỚ:</span>
            </div>
            <ul class="rules-list">
              <li v-for="(rule, idx) in activeRules.slice(0, 3)" :key="idx" class="rule-item">
                <CheckCircle2 :size="11" class="rule-icon" />
                <span>{{ rule }}</span>
              </li>
            </ul>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.council-deck {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--paper, #f8faf6);
  border: 1px solid var(--line, #d9e0d9);
  border-radius: 7px;
  padding: 12px;
  color: var(--ink, #1b2a23);
  font-family: inherit;
}

/* Deck Topbar */
.deck-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line, #d9e0d9);
}

.deck-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.syndicate-icon {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: #225c43;
  color: #c9f06b;
}

.deck-title {
  margin: 0;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.04em;
  line-height: 1.15;
}

.deck-subtitle {
  font-size: 9px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
  display: block;
}

.deck-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.deck-btn {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border: 1px solid var(--line, #d9e0d9);
  border-radius: 4px;
  background: #ffffff;
  color: var(--muted, #77847c);
  transition: all 0.15s ease;
}

.deck-btn:hover {
  background: #e3ebe1;
  color: var(--ink, #1b2a23);
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

/* Status Line */
.deck-status-line {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
  padding: 2px 2px 6px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c5c9c4;
}

.pulse-dot.active {
  background: #54a267;
  box-shadow: 0 0 0 2px #54a26733;
}

.status-text {
  flex: 1;
}

.hitl-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: transparent;
  border: 0;
  color: #225c43;
  font-size: 10px;
  font-weight: 700;
  text-decoration: underline;
  padding: 0;
  cursor: pointer;
}

/* Cards Stack */
.cards-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.agent-card {
  border: 1px solid var(--line, #d9e0d9);
  border-radius: 6px;
  background: #ffffff;
  overflow: hidden;
  transition: all 0.2s ease;
}

.agent-card:hover {
  border-color: #bccac0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 10px;
  background: #f4f7f3;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid transparent;
}

.agent-card:not(.collapsed) .card-header {
  border-bottom-color: #e5ece4;
}

.agent-id {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-symbol {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 5px;
}

.symbol-arbiter {
  background: #f5eedb;
  color: #8b6b23;
  border: 1px solid #d0b674;
}

.symbol-sentinel {
  background: #eee8f5;
  color: #6a429b;
  border: 1px solid #c9b4e6;
}

.symbol-vector {
  background: #e5eff9;
  color: #2264a6;
  border: 1px solid #b5d3f3;
}

.symbol-scribe {
  background: #e6f5ec;
  color: #225c43;
  border: 1px solid #a9d9b8;
}

.agent-names {
  display: flex;
  flex-direction: column;
}

.agent-code {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.05em;
  line-height: 1.1;
}

.agent-role {
  font-size: 8.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
}

.header-badges {
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 9.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.03em;
}

.badge-allowed {
  background: #e2ede0;
  color: #225c43;
  border: 1px solid #b7d6b3;
}

.badge-restricted {
  background: #fdf5e6;
  color: #b37400;
  border: 1px solid #edd5a6;
}

.badge-blocked, .badge-halt {
  background: #fbeae8;
  color: #c65345;
  border: 1px solid #f0beba;
}

.badge-normal {
  background: #e8ece9;
  color: #4b6053;
  border: 1px solid #cbd6cf;
}

.badge-approaching {
  background: #fdf3e2;
  color: #b56c00;
  border: 1px solid #eed6ab;
}

.bias-bullish {
  background: #e3f2e7;
  color: #236c3e;
  border: 1px solid #b5d9be;
}

.bias-bearish {
  background: #fae8e6;
  color: #b54035;
  border: 1px solid #f1bab5;
}

.bias-neutral {
  background: #edf0ed;
  color: #55665c;
  border: 1px solid #ccd6ce;
}

.outcome-win {
  background: #e0f3e6;
  color: #1e6b3b;
  border: 1px solid #abdcb8;
}

.outcome-loss {
  background: #fde8e5;
  color: #bb3b2e;
  border: 1px solid #f3b5ad;
}

.outcome-neutral {
  background: #ebeeee;
  color: #637171;
  border: 1px solid #cad4d4;
}

.chevron-btn {
  background: transparent;
  border: 0;
  color: var(--muted, #77847c);
  padding: 0;
  display: grid;
  place-items: center;
}

/* Card Body */
.card-body {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11px;
}

/* Metrics Grid & Bars */
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.meter-box {
  background: #f8faf8;
  border: 1px solid #e2ebe2;
  border-radius: 5px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.meter-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.meter-label {
  font-size: 8.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
  font-weight: 600;
}

.meter-val {
  font-size: 11px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 700;
}

.meter-bar-track {
  height: 5px;
  background: #e4ebe4;
  border-radius: 3px;
  overflow: hidden;
}

.meter-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.fill-arbiter {
  background: #cb9a50;
}

.fill-green {
  background: #489b60;
}

.fill-amber {
  background: #d49339;
}

.fill-red {
  background: #c65345;
}

.fill-blue {
  background: #367dc2;
}

.fill-purple {
  background: #7a50b3;
}

.meter-sub {
  font-size: 8.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
}

/* Rationale & Box Tag */
.rationale-box {
  background: #fafaf8;
  border-left: 2px solid #cb9a50;
  padding: 6px 8px;
  border-radius: 0 4px 4px 0;
}

.box-tag {
  font-size: 8px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 700;
  color: var(--muted, #77847c);
  letter-spacing: 0.04em;
  display: block;
  margin-bottom: 2px;
}

.rationale-text {
  margin: 0;
  font-size: 10px;
  color: #3b4b42;
  line-height: 1.35;
}

/* Emergency Button */
.card-action-row {
  margin-top: 2px;
}

.emergency-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 28px;
  border-radius: 5px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  font-family: var(--mono, 'DM Mono', monospace);
  border: 1px solid transparent;
  transition: all 0.15s ease;
}

.btn-danger {
  background: #faeae8;
  color: #b83d31;
  border-color: #eebeba;
}

.btn-danger:hover {
  background: #b83d31;
  color: #ffffff;
}

.btn-resume {
  background: #e2ede0;
  color: #225c43;
  border-color: #b7d6b3;
}

.btn-resume:hover {
  background: #225c43;
  color: #c9f06b;
}

/* Sentiment Gauge */
.sentiment-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #f8faf8;
  border: 1px solid #e2ebe2;
  border-radius: 5px;
  padding: 7px 8px;
}

.gauge-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.gauge-val {
  font-size: 10px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 700;
}

.sentiment-track {
  position: relative;
  height: 8px;
  border-radius: 4px;
  display: flex;
  overflow: visible;
  margin: 4px 0 2px;
}

.zone-bearish {
  flex: 4;
  background: #f0a79e;
  border-radius: 4px 0 0 4px;
}

.zone-neutral {
  flex: 2;
  background: #d6ded8;
}

.zone-bullish {
  flex: 4;
  background: #9bd4ab;
  border-radius: 0 4px 4px 0;
}

.sentiment-needle {
  position: absolute;
  top: -2px;
  width: 4px;
  height: 12px;
  background: #1b2a23;
  border-radius: 2px;
  transform: translateX(-50%);
  box-shadow: 0 0 2px rgba(0,0,0,0.4);
  transition: left 0.3s ease;
}

.gauge-scale {
  display: flex;
  justify-content: space-between;
  font-size: 8px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
}

/* Macro Sub Grid */
.macro-sub-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.sub-item {
  background: #f8faf8;
  border: 1px solid #e2ebe2;
  border-radius: 5px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sub-label {
  font-size: 8px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
  font-weight: 700;
}

.tag-pill {
  display: inline-block;
  font-size: 9px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 700;
  padding: 2px 5px;
  border-radius: 4px;
  width: fit-content;
}

.dxy-gold-pos {
  background: #e2ede0;
  color: #225c43;
}

.dxy-gold-neg {
  background: #fbeae8;
  color: #c65345;
}

.dxy-neutral {
  background: #e8ece9;
  color: #55665c;
}

.event-brief {
  display: flex;
  flex-direction: column;
}

.event-title {
  font-size: 9.5px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-clock {
  font-size: 9px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: #c65345;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-weight: 700;
}

/* News Mini Feed */
.news-mini-feed {
  background: #fafaf9;
  border: 1px solid #e8ede8;
  border-radius: 5px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.feed-title {
  font-size: 8px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 700;
  color: var(--muted, #77847c);
}

.news-line {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 9.5px;
  line-height: 1.25;
}

.urgency-tag {
  font-size: 7.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 3px;
  flex-shrink: 0;
}

.urg-crit {
  background: #c65345;
  color: #ffffff;
}

.urg-high {
  background: #e5822e;
  color: #ffffff;
}

.urg-med {
  background: #d6e2d9;
  color: #294736;
}

.news-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.news-time {
  font-size: 8px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
  flex-shrink: 0;
}

/* Vector RAG Match & Setup */
.rag-match-box {
  background: #f6f4fa;
  border: 1px solid #dfd8ed;
  border-radius: 5px;
  padding: 6px 8px;
}

.rag-match-head {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #6a429b;
}

.match-name {
  margin: 3px 0 0;
  font-size: 10px;
  font-weight: 700;
  color: #3b2859;
}

.setup-box {
  background: #f7fafc;
  border: 1px solid #d8e5f2;
  border-radius: 5px;
  padding: 7px 8px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.setup-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setup-act {
  font-size: 9.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 3px;
}

.act-buy {
  background: #e2ede0;
  color: #225c43;
}

.act-sell {
  background: #faeae8;
  color: #b83d31;
}

.setup-rr {
  font-size: 9.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 700;
  color: #2264a6;
}

.setup-coords {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 4px;
  background: #ffffff;
  border: 1px solid #e1e9f0;
  border-radius: 4px;
  padding: 4px 6px;
}

.coord-item {
  display: flex;
  flex-direction: column;
}

.c-lbl {
  font-size: 7.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  color: var(--muted, #77847c);
}

.c-val {
  font-size: 9.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 700;
}

.setup-recom {
  margin: 0;
  font-size: 9.5px;
  color: #4b5e6e;
  line-height: 1.3;
}

/* Scribe Post Mortem */
.post-mortem-box {
  background: #f9fbf9;
  border: 1px solid #dbe6dc;
  border-radius: 5px;
  padding: 7px 8px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.pm-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pm-ticket {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-family: var(--mono, 'DM Mono', monospace);
}

.pm-type {
  font-weight: 800;
}

.pm-pnl {
  font-size: 11px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 800;
}

.pm-mistake {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mistake-badge {
  display: inline-block;
  font-size: 8.5px;
  font-family: var(--mono, 'DM Mono', monospace);
  font-weight: 800;
  background: #fdedeb;
  color: #b83d31;
  border: 1px solid #f1c5c0;
  border-radius: 3px;
  padding: 1px 5px;
  width: fit-content;
}

.mistake-cause {
  margin: 0;
  font-size: 9.5px;
  color: #55665c;
  line-height: 1.3;
}

.pm-lesson {
  background: #ffffff;
  border: 1px solid #e1ebe2;
  border-radius: 4px;
  padding: 5px 6px;
}

.lesson-text {
  margin: 0;
  font-size: 9.5px;
  color: #225c43;
  line-height: 1.35;
  font-weight: 600;
}

.empty-scribe {
  background: #f8faf8;
  border: 1px dashed #d5ded6;
  border-radius: 5px;
  padding: 10px;
  text-align: center;
  color: var(--muted, #77847c);
  font-size: 9.5px;
}

.empty-scribe p {
  margin: 0;
}

.active-rules-box {
  background: #fafbf9;
  border: 1px solid #e2ebe3;
  border-radius: 5px;
  padding: 6px 8px;
}

.rules-list {
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rule-item {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  font-size: 9px;
  line-height: 1.3;
  color: #2b3d32;
}

.rule-icon {
  color: #225c43;
  flex-shrink: 0;
  margin-top: 1px;
}

/* Colors & Utility */
.txt-bullish { color: #236c3e; }
.txt-bearish { color: #b54035; }
.txt-neutral { color: #55665c; }
.txt-green { color: #236c3e; }
.txt-red { color: #b83d31; }
.txt-warn { color: #cb9a50; }
.txt-alert { color: #b83d31; }
.txt-purple { color: #6a429b; }
.text-muted { color: var(--muted, #77847c); font-size: 9px; font-style: italic; }
</style>
