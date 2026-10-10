<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock,
  ExternalLink,
  Filter,
  Globe2,
  Minus,
  Newspaper,
  RefreshCw,
  Search,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-vue-next'

const props = defineProps({
  news: {
    type: Array,
    default: () => [],
  },
  events: {
    type: Array,
    default: () => [],
  },
  sources: {
    type: Object,
    default: () => ({}),
  },
  initialSubTab: {
    type: String,
    default: 'calendar',
  },
})

const emit = defineEmits(['refresh'])

const activeSubTab = ref(props.initialSubTab || 'calendar') // 'calendar' | 'news'

watch(
  () => props.initialSubTab,
  (val) => {
    if (val) activeSubTab.value = val
  }
)

const now = ref(Date.now())
let countdownTimer

// Calendar filters
const calendarDayFilter = ref('ALL') // 'ALL' | 'YESTERDAY' | 'TODAY' | 'TOMORROW'
const calendarStarFilter = ref('ALL')
const calendarCurrencyFilter = ref('ALL')
const calendarSearch = ref('')

// News filters
const newsSourceFilter = ref('ALL')
const newsStarFilter = ref('ALL')
const newsSentimentFilter = ref('ALL')
const newsSearch = ref('')

// Source list
const knownSources = ['FairEconomy', 'Kitco News', 'FXStreet News', 'Finnhub']

function getSourceInfo(name) {
  return props.sources[name] || null
}

function sourceStatusLabel(sourceName) {
  const s = getSourceInfo(sourceName)
  if (!s) return 'WAITING'
  if (s.stale) return 'STALE'
  if (s.fallback_active) return 'FALLBACK'
  return s.status ? s.status.toUpperCase() : 'WAITING'
}

function sourceStatusClass(sourceName) {
  const lbl = sourceStatusLabel(sourceName)
  if (lbl === 'HEALTHY') return 'status-healthy'
  if (lbl === 'STALE' || lbl === 'UNAVAILABLE' || lbl === 'DEGRADED') return 'status-stale'
  return 'status-waiting'
}

// Extract available currencies from events
const availableCurrencies = computed(() => {
  const set = new Set()
  props.events.forEach((e) => {
    if (e.currency) set.add(e.currency.toUpperCase())
  })
  return Array.from(set).sort()
})

// Extract available sources from news
const availableNewsSources = computed(() => {
  const set = new Set()
  props.news.forEach((n) => {
    if (n.source) set.add(n.source)
  })
  return Array.from(set).sort()
})

function getLocalDateKey(dateOrIso, timeZone = 'Asia/Ho_Chi_Minh') {
  if (!dateOrIso) return null
  const d = typeof dateOrIso === 'string' || typeof dateOrIso === 'number' ? new Date(dateOrIso) : dateOrIso
  if (!d || isNaN(d.getTime())) return null
  try {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(d)
  } catch {
    return d.toISOString().slice(0, 10)
  }
}

// Filtered Events
const filteredEvents = computed(() => {
  return props.events.filter((evt) => {
    if (calendarDayFilter.value !== 'ALL') {
      const dNow = new Date(now.value)
      const tz = 'Asia/Ho_Chi_Minh'
      const eKey = getLocalDateKey(evt.event_timestamp || evt.provider_time_raw, tz)
      const todayKey = getLocalDateKey(dNow, tz)
      const yesterdayKey = getLocalDateKey(new Date(dNow.getTime() - 86400000), tz)
      const tomorrowKey = getLocalDateKey(new Date(dNow.getTime() + 86400000), tz)

      if (calendarDayFilter.value === 'TODAY' && eKey !== todayKey) return false
      if (calendarDayFilter.value === 'YESTERDAY' && eKey !== yesterdayKey) return false
      if (calendarDayFilter.value === 'TOMORROW' && eKey !== tomorrowKey) return false
    }

    if (calendarStarFilter.value !== 'ALL') {
      const targetStars = Number(calendarStarFilter.value)
      if (evt.impact_stars !== targetStars) return false
    }

    if (calendarCurrencyFilter.value !== 'ALL') {
      if ((evt.currency || '').toUpperCase() !== calendarCurrencyFilter.value) return false
    }

    if (calendarSearch.value.trim()) {
      const q = calendarSearch.value.trim().toLowerCase()
      const titleMatch = (evt.title || '').toLowerCase().includes(q)
      const descMatch = (evt.description || '').toLowerCase().includes(q)
      const srcMatch = (evt.source || '').toLowerCase().includes(q)
      if (!titleMatch && !descMatch && !srcMatch) return false
    }

    return true
  })
})

// Filtered News
const filteredNews = computed(() => {
  return props.news.filter((item) => {
    if (newsSourceFilter.value !== 'ALL' && item.source !== newsSourceFilter.value) {
      return false
    }

    if (newsStarFilter.value !== 'ALL') {
      const targetStars = Number(newsStarFilter.value)
      if (item.impact_stars !== targetStars) return false
    }

    if (newsSentimentFilter.value !== 'ALL') {
      const score = item.sentiment_score
      if (score === null || score === undefined) {
        if (newsSentimentFilter.value !== 'NEUTRAL') return false
      } else {
        if (newsSentimentFilter.value === 'BULLISH' && score <= 0.1) return false
        if (newsSentimentFilter.value === 'BEARISH' && score >= -0.1) return false
        if (newsSentimentFilter.value === 'NEUTRAL' && (score > 0.1 || score < -0.1)) return false
      }
    }

    if (newsSearch.value.trim()) {
      const q = newsSearch.value.trim().toLowerCase()
      const titleMatch = (item.title || '').toLowerCase().includes(q)
      const aiMatch = (item.ai_analysis_summary || '').toLowerCase().includes(q)
      if (!titleMatch && !aiMatch) return false
    }

    return true
  })
})

function formatCountdown(event) {
  if (event.timezone_status !== 'VERIFIED' || !event.event_timestamp) {
    return { text: 'TIME UNVERIFIED', isVerified: false, isReleased: false }
  }
  const diffSec = Math.floor((new Date(event.event_timestamp).getTime() - now.value) / 1000)
  if (diffSec <= 0) {
    return { text: 'RELEASED', isVerified: true, isReleased: true }
  }
  const hours = Math.floor(diffSec / 3600)
  const minutes = Math.floor((diffSec % 3600) / 60)
  const text = hours > 0 ? `IN ${hours}H ${minutes}M` : `IN ${minutes}M`
  return { text, isVerified: true, isReleased: false }
}

function formatEventTime(iso) {
  if (!iso) return { utc: '--:--', ict: '--:--' }
  const d = new Date(iso)
  return {
    utc: d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }),
    ict: d.toLocaleTimeString('vi-VN', { hour12: false, hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Ho_Chi_Minh' }),
    date: d.toLocaleDateString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', month: '2-digit', day: '2-digit' }),
  }
}

function formatNewsTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const diffMin = Math.floor((now.value - d.getTime()) / 60000)
  if (diffMin < 1) return 'Vừa xong'
  if (diffMin < 60) return `${diffMin}m trước`
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return `${diffHours}h trước`
  return d.toLocaleDateString('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function starString(stars) {
  if (!stars) return '☆☆☆'
  return `${'★'.repeat(stars)}${'☆'.repeat(3 - stars)}`
}

onMounted(() => {
  countdownTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 10_000)
})

onUnmounted(() => {
  window.clearInterval(countdownTimer)
})
</script>

<template>
  <div class="news-events-container">
    <!-- Header -->
    <div class="view-header">
      <div class="header-left">
        <span class="icon-chip"><Globe2 :size="18" /></span>
        <div>
          <h2>Market News &amp; Economic Calendar</h2>
          <p>Luồng tin tức tài chính và lịch phát hành chỉ số kinh tế toàn cầu theo thời gian thực</p>
        </div>
      </div>
      <div class="header-actions">
        <button class="refresh-btn" @click="emit('refresh')">
          <RefreshCw :size="13" /> Đồng bộ nguồn tin
        </button>
      </div>
    </div>

    <!-- Source Health Monitor Cards -->
    <section class="sources-strip">
      <div class="sources-label">
        <span>DATA FEEDS STATUS:</span>
      </div>
      <div class="sources-grid">
        <div
          v-for="source in knownSources"
          :key="source"
          :class="['source-card', sourceStatusClass(source)]"
        >
          <div class="source-card-head">
            <span class="indicator-dot"></span>
            <strong class="source-name">{{ source }}</strong>
            <span class="source-badge">{{ sourceStatusLabel(source) }}</span>
          </div>
          <div class="source-card-body">
            <span v-if="getSourceInfo(source)">
              Mode: <b>{{ getSourceInfo(source)?.mode || 'primary' }}</b> ·
              Success: <b>{{ getSourceInfo(source)?.primary_successes ?? 0 }}</b>
            </span>
            <span v-else class="text-muted">Chưa kích hoạt / Polling</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Sub Navigation Tabs -->
    <div class="sub-nav">
      <button
        :class="['sub-nav-item', { active: activeSubTab === 'calendar' }]"
        @click="activeSubTab = 'calendar'"
      >
        <CalendarDays :size="15" />
        <span>Economic Calendar</span>
        <span class="count-badge">{{ events.length }}</span>
      </button>
      <button
        :class="['sub-nav-item', { active: activeSubTab === 'news' }]"
        @click="activeSubTab = 'news'"
      >
        <Newspaper :size="15" />
        <span>Breaking News &amp; Headlines</span>
        <span class="count-badge">{{ news.length }}</span>
      </button>
    </div>

    <!-- TAB 1: ECONOMIC CALENDAR -->
    <section v-if="activeSubTab === 'calendar'" class="tab-content">
      <!-- Calendar Filters -->
      <div class="filter-toolbar">
        <div class="search-box">
          <Search :size="14" />
          <input
            v-model="calendarSearch"
            type="text"
            placeholder="Tìm theo tên sự kiện, tiền tệ, nguồn..."
          />
          <button v-if="calendarSearch" class="clear-search" @click="calendarSearch = ''">×</button>
        </div>

        <div class="filter-group">
          <span class="filter-label"><Filter :size="12" /> Impact:</span>
          <div class="segmented-control">
            <button :class="{ active: calendarStarFilter === 'ALL' }" @click="calendarStarFilter = 'ALL'">Tất cả</button>
            <button :class="{ active: calendarStarFilter === '3' }" @click="calendarStarFilter = '3'">★★★ Cao</button>
            <button :class="{ active: calendarStarFilter === '2' }" @click="calendarStarFilter = '2'">★★ Vừa</button>
            <button :class="{ active: calendarStarFilter === '1' }" @click="calendarStarFilter = '1'">★ Thấp</button>
          </div>
        </div>

        <div class="filter-group">
          <span class="filter-label"><CalendarDays :size="12" /> Ngày:</span>
          <div class="segmented-control">
            <button :class="{ active: calendarDayFilter === 'ALL' }" @click="calendarDayFilter = 'ALL'">Tất cả</button>
            <button :class="{ active: calendarDayFilter === 'YESTERDAY' }" @click="calendarDayFilter = 'YESTERDAY'">Hôm qua</button>
            <button :class="{ active: calendarDayFilter === 'TODAY' }" @click="calendarDayFilter = 'TODAY'">Hôm nay</button>
            <button :class="{ active: calendarDayFilter === 'TOMORROW' }" @click="calendarDayFilter = 'TOMORROW'">Ngày mai</button>
          </div>
        </div>

        <div class="filter-group">
          <span class="filter-label">Tiền tệ:</span>
          <select v-model="calendarCurrencyFilter" class="select-dropdown">
            <option value="ALL">Tất cả tiền tệ</option>
            <option v-for="curr in availableCurrencies" :key="curr" :value="curr">{{ curr }}</option>
          </select>
        </div>

        <button
          v-if="calendarSearch || calendarStarFilter !== 'ALL' || calendarCurrencyFilter !== 'ALL' || calendarDayFilter !== 'ALL'"
          class="reset-btn"
          @click="calendarSearch = ''; calendarStarFilter = 'ALL'; calendarCurrencyFilter = 'ALL'; calendarDayFilter = 'ALL'"
        >
          Reset
        </button>
      </div>

      <!-- Calendar Events Table / List -->
      <div class="events-wrapper">
        <div v-if="filteredEvents.length" class="events-list">
          <article
            v-for="event in filteredEvents"
            :key="event.id"
            :class="['event-item', `impact-stars-${event.impact_stars || 0}`]"
          >
            <!-- Time Column -->
            <div class="event-time-col">
              <span class="event-time-ict">{{ formatEventTime(event.event_timestamp).ict }} <small>ICT</small></span>
              <span class="event-time-utc">{{ formatEventTime(event.event_timestamp).utc }} <small>UTC</small></span>
              <span v-if="formatEventTime(event.event_timestamp).date" class="event-date">
                {{ formatEventTime(event.event_timestamp).date }}
              </span>
            </div>

            <!-- Currency & Stars -->
            <div class="event-meta-col">
              <span class="curr-badge">{{ event.currency || 'USD' }}</span>
              <span :class="['stars-badge', `stars-${event.impact_stars}`]">
                {{ starString(event.impact_stars) }}
              </span>
            </div>

            <!-- Main Content -->
            <div class="event-body-col">
              <div class="event-title-row">
                <h4 class="event-title">{{ event.title }}</h4>
                <div class="countdown-tag-wrapper">
                  <span
                    :class="[
                      'countdown-tag',
                      formatCountdown(event).isReleased ? 'tag-released' : '',
                      !formatCountdown(event).isVerified ? 'tag-unverified' : 'tag-active',
                    ]"
                  >
                    <Clock v-if="formatCountdown(event).isVerified" :size="11" />
                    <AlertTriangle v-else :size="11" />
                    {{ formatCountdown(event).text }}
                  </span>
                </div>
              </div>

              <p v-if="event.description" class="event-desc">{{ event.description }}</p>

              <!-- Values comparison (Actual / Forecast / Previous) -->
              <div class="values-grid">
                <div class="val-box">
                  <span class="val-label">ACTUAL:</span>
                  <strong :class="['val-value', event.actual_value ? 'highlight-val' : 'muted-val']">
                    {{ event.actual_value || '--' }}
                  </strong>
                </div>
                <div class="val-box">
                  <span class="val-label">FORECAST:</span>
                  <strong class="val-value">{{ event.forecast_value || '--' }}</strong>
                </div>
                <div class="val-box">
                  <span class="val-label">PREVIOUS:</span>
                  <strong class="val-value">{{ event.previous_value || '--' }}</strong>
                </div>
                <div class="val-box source-attr">
                  <span class="val-label">SOURCE:</span>
                  <span class="attr-text">{{ event.source }} (Rev #{{ event.revision_no }})</span>
                </div>
              </div>
            </div>
          </article>
        </div>

        <!-- Empty state -->
        <div v-else class="empty-state">
          <CalendarDays :size="36" class="empty-icon" />
          <h4>Không có sự kiện kinh tế phù hợp</h4>
          <p>Thử điều chỉnh bộ lọc hoặc xóa từ khóa tìm kiếm</p>
        </div>
      </div>
    </section>

    <!-- TAB 2: BREAKING NEWS & HEADLINES -->
    <section v-if="activeSubTab === 'news'" class="tab-content">
      <!-- News Filters -->
      <div class="filter-toolbar">
        <div class="search-box">
          <Search :size="14" />
          <input
            v-model="newsSearch"
            type="text"
            placeholder="Tìm kiếm tin tức hoặc phân tích AI..."
          />
          <button v-if="newsSearch" class="clear-search" @click="newsSearch = ''">×</button>
        </div>

        <div class="filter-group">
          <span class="filter-label">Nguồn tin:</span>
          <select v-model="newsSourceFilter" class="select-dropdown">
            <option value="ALL">Tất cả nguồn</option>
            <option v-for="src in availableNewsSources" :key="src" :value="src">{{ src }}</option>
          </select>
        </div>

        <div class="filter-group">
          <span class="filter-label">Impact:</span>
          <div class="segmented-control">
            <button :class="{ active: newsStarFilter === 'ALL' }" @click="newsStarFilter = 'ALL'">Tất cả</button>
            <button :class="{ active: newsStarFilter === '3' }" @click="newsStarFilter = '3'">★★★ 3 Sao</button>
            <button :class="{ active: newsStarFilter === '2' }" @click="newsStarFilter = '2'">★★ 2 Sao</button>
            <button :class="{ active: newsStarFilter === '1' }" @click="newsStarFilter = '1'">★ 1 Sao</button>
          </div>
        </div>

        <div class="filter-group">
          <span class="filter-label">Sentiment:</span>
          <div class="segmented-control">
            <button :class="{ active: newsSentimentFilter === 'ALL' }" @click="newsSentimentFilter = 'ALL'">Tất cả</button>
            <button :class="{ active: newsSentimentFilter === 'BULLISH' }" @click="newsSentimentFilter = 'BULLISH'">Bullish</button>
            <button :class="{ active: newsSentimentFilter === 'BEARISH' }" @click="newsSentimentFilter = 'BEARISH'">Bearish</button>
            <button :class="{ active: newsSentimentFilter === 'NEUTRAL' }" @click="newsSentimentFilter = 'NEUTRAL'">Neutral</button>
          </div>
        </div>

        <button
          v-if="newsSearch || newsSourceFilter !== 'ALL' || newsStarFilter !== 'ALL' || newsSentimentFilter !== 'ALL'"
          class="reset-btn"
          @click="newsSearch = ''; newsSourceFilter = 'ALL'; newsStarFilter = 'ALL'; newsSentimentFilter = 'ALL'"
        >
          Reset
        </button>
      </div>

      <!-- News Articles Stream -->
      <div class="news-wrapper">
        <div v-if="filteredNews.length" class="news-grid">
          <article
            v-for="item in filteredNews"
            :key="item.id"
            class="news-card"
          >
            <div class="news-card-header">
              <div class="header-tags">
                <span class="news-source-tag">{{ item.source }}</span>
                <span v-if="item.impact_stars" class="news-stars">{{ starString(item.impact_stars) }}</span>
                <span class="news-time">{{ formatNewsTime(item.published_at) }}</span>
              </div>
              <!-- Sentiment Pill -->
              <div
                v-if="item.sentiment_score !== null && item.sentiment_score !== undefined"
                :class="[
                  'sentiment-pill',
                  item.sentiment_score > 0.1 ? 'sent-bull' : item.sentiment_score < -0.1 ? 'sent-bear' : 'sent-neutral',
                ]"
              >
                <TrendingUp v-if="item.sentiment_score > 0.1" :size="12" />
                <TrendingDown v-else-if="item.sentiment_score < -0.1" :size="12" />
                <Minus v-else :size="12" />
                <span>{{ Number(item.sentiment_score) > 0 ? '+' : '' }}{{ Number(item.sentiment_score).toFixed(2) }}</span>
              </div>
            </div>

            <h3 class="news-headline">
              <a
                v-if="item.source_url"
                :href="item.source_url"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ item.title }}
                <ExternalLink :size="12" class="ext-icon" />
              </a>
              <span v-else>{{ item.title }}</span>
            </h3>

            <!-- AI Summary if exists -->
            <div v-if="item.ai_analysis_summary" class="ai-summary-box">
              <div class="ai-badge">
                <Sparkles :size="11" /> AI INSIGHT
              </div>
              <p>{{ item.ai_analysis_summary }}</p>
            </div>

            <!-- Card footer -->
            <div class="news-card-foot">
              <span class="pub-date">Published: {{ new Date(item.published_at).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false }) }} ICT</span>
              <a
                v-if="item.source_url"
                :href="item.source_url"
                target="_blank"
                rel="noopener noreferrer"
                class="read-source-link"
              >
                Xem bài viết gốc <ExternalLink :size="11" />
              </a>
            </div>
          </article>
        </div>

        <!-- Empty state -->
        <div v-else class="empty-state">
          <Newspaper :size="36" class="empty-icon" />
          <h4>Không tìm thấy tin tức nào</h4>
          <p>Thử điều chỉnh bộ lọc nguồn tin hoặc nội dung tìm kiếm</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.news-events-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px 0 24px;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 4px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-chip {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 9px;
  background: #225c43;
  color: #c9f06b;
  box-shadow: 0 2px 6px #225c432b;
}

.view-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #1b2a23;
  letter-spacing: -0.02em;
}

.view-header p {
  margin: 2px 0 0;
  font-size: 12px;
  color: #6d7d74;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #f4f7f2;
  border: 1px solid #d0dbce;
  border-radius: 6px;
  font: 11px 'DM Mono', monospace;
  color: #225c43;
  cursor: pointer;
  transition: all 0.15s ease;
}

.refresh-btn:hover {
  background: #e4eee2;
}

/* Source Strip */
.sources-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f8faf6;
  border: 1px solid #d5ded6;
  border-radius: 8px;
}

.sources-label {
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  color: #728479;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.sources-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  flex: 1;
}

.source-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #dee6dc;
  background: #ffffff;
  min-width: 175px;
  flex: 1;
}

.source-card-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #8e9e94;
}

.source-name {
  font-size: 11px;
  color: #1b2a23;
}

.source-badge {
  margin-left: auto;
  font: 8px 'DM Mono', monospace;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
}

.source-card.status-healthy .indicator-dot { background: #2e7a52; box-shadow: 0 0 0 2px #2e7a5220; }
.source-card.status-healthy .source-badge { background: #e3f3e6; color: #1e7043; }

.source-card.status-stale .indicator-dot { background: #c25243; }
.source-card.status-stale .source-badge { background: #fde8e5; color: #b83d30; }

.source-card.status-waiting .indicator-dot { background: #d09d3b; }
.source-card.status-waiting .source-badge { background: #fdf3dc; color: #8e6c1e; }

.source-card-body {
  font: 9px 'DM Mono', monospace;
  color: #6d7f74;
}

.source-card-body b {
  color: #2b3d32;
}

/* Sub Nav */
.sub-nav {
  display: flex;
  gap: 8px;
  border-bottom: 2px solid #e0e7de;
  padding-bottom: 2px;
}

.sub-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: transparent;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #64766c;
  border-radius: 6px 6px 0 0;
  position: relative;
  transition: all 0.15s ease;
}

.sub-nav-item:hover {
  color: #225c43;
  background: #f0f4ee;
}

.sub-nav-item.active {
  color: #225c43;
  background: #ffffff;
  font-weight: 700;
  border: 1px solid #d5ded6;
  border-bottom: 2px solid #ffffff;
  margin-bottom: -3px;
}

.count-badge {
  padding: 2px 6px;
  background: #e4ece1;
  border-radius: 10px;
  font: 10px 'DM Mono', monospace;
  color: #3b5044;
}

.sub-nav-item.active .count-badge {
  background: #225c43;
  color: #c9f06b;
}

/* Tab Content */
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Filter Toolbar */
.filter-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #f4f7f2;
  border: 1px solid #d9e2da;
  border-radius: 7px;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 1px solid #ccd8cd;
  border-radius: 5px;
  padding: 0 9px;
  min-width: 250px;
}

.search-box svg { color: #7d8f84; }
.search-box input {
  border: none;
  background: transparent;
  padding: 7px 6px;
  font-size: 12px;
  color: #1b2a23;
  width: 100%;
  outline: none;
}
.clear-search {
  border: none;
  background: transparent;
  font-size: 14px;
  color: #809087;
  cursor: pointer;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font: 10px 'DM Mono', monospace;
  color: #67786f;
  display: flex;
  align-items: center;
  gap: 4px;
}

.segmented-control {
  display: flex;
  background: #e2e8e0;
  border-radius: 5px;
  padding: 2px;
}

.segmented-control button {
  border: none;
  background: transparent;
  padding: 4px 8px;
  font-size: 11px;
  color: #55665d;
  border-radius: 4px;
  font-weight: 500;
}

.segmented-control button.active {
  background: #ffffff;
  color: #225c43;
  font-weight: 700;
  box-shadow: 0 1px 3px #00000015;
}

.select-dropdown {
  background: #ffffff;
  border: 1px solid #ccd8cd;
  border-radius: 5px;
  padding: 5px 8px;
  font-size: 11px;
  color: #2b3b32;
  outline: none;
  cursor: pointer;
}

.reset-btn {
  margin-left: auto;
  border: 1px solid #d2ded0;
  background: #ffffff;
  color: #63776c;
  padding: 5px 10px;
  border-radius: 5px;
  font-size: 11px;
  cursor: pointer;
}

/* Events List */
.events-wrapper {
  background: #ffffff;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  overflow: hidden;
}

.events-list {
  display: flex;
  flex-direction: column;
}

.event-item {
  display: grid;
  grid-template-columns: 110px 90px 1fr;
  gap: 16px;
  padding: 14px 18px;
  border-bottom: 1px solid #edf1eb;
  transition: background 0.15s ease;
}

.event-item:hover {
  background: #f8faf6;
}

.event-item:last-child {
  border-bottom: none;
}

.event-time-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font: 11px 'DM Mono', monospace;
}

.event-time-ict {
  font-weight: 700;
  color: #23342a;
}

.event-time-ict small, .event-time-utc small {
  color: #839489;
  font-size: 8px;
}

.event-time-utc {
  font-size: 10px;
  color: #6e8074;
}

.event-date {
  font-size: 9px;
  color: #92a298;
}

.event-meta-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.curr-badge {
  display: inline-block;
  padding: 2px 6px;
  background: #eef3ec;
  border: 1px solid #d5ded4;
  border-radius: 4px;
  font: 10px 'DM Mono', monospace;
  font-weight: 700;
  color: #225c43;
  width: fit-content;
}

.stars-badge {
  font: 11px 'DM Mono', monospace;
  color: #bfa14c;
  letter-spacing: 1px;
}

.stars-3 { color: #d09028; font-weight: 700; }
.stars-2 { color: #bca04a; }
.stars-1 { color: #8e9e93; }

.event-body-col {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.event-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.event-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #1b2a23;
  line-height: 1.3;
}

.countdown-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  white-space: nowrap;
}

.tag-active {
  background: #fdf3dc;
  color: #966f1b;
  border: 1px solid #fae1ad;
}

.tag-released {
  background: #e3f2e6;
  color: #237b4b;
  border: 1px solid #cae8d0;
}

.tag-unverified {
  background: #f7ebe9;
  color: #b5473a;
  border: 1px solid #f2cfca;
}

.event-desc {
  margin: 0;
  font-size: 11px;
  color: #64756b;
  line-height: 1.4;
}

.values-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  padding: 8px 12px;
  background: #f5f8f3;
  border: 1px solid #e2e8df;
  border-radius: 5px;
}

.val-box {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font: 10px 'DM Mono', monospace;
}

.val-label {
  color: #7b8d81;
  font-size: 9px;
}

.val-value {
  color: #25372d;
  font-size: 11px;
}

.highlight-val {
  color: #1e7043;
  font-weight: 700;
}

.muted-val {
  color: #95a39a;
}

.source-attr {
  margin-left: auto;
}

.attr-text {
  color: #708277;
  font-size: 9px;
}

/* News Grid */
.news-wrapper {
  background: #fbfdfa;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  padding: 14px;
}

.news-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.news-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: #ffffff;
  border: 1px solid #dbe3dc;
  border-radius: 7px;
  box-shadow: 0 1px 2px #00000008;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.news-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px #0000000d;
}

.news-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-tags {
  display: flex;
  align-items: center;
  gap: 6px;
}

.news-source-tag {
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  padding: 2px 6px;
  background: #edf3ec;
  color: #225c43;
  border-radius: 4px;
}

.news-stars {
  font: 10px 'DM Mono', monospace;
  color: #d09028;
}

.news-time {
  font: 9px 'DM Mono', monospace;
  color: #85968b;
}

.sentiment-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
}

.sent-bull {
  background: #e3f4e6;
  color: #1e7043;
  border: 1px solid #c2e5c8;
}

.sent-bear {
  background: #fde8e5;
  color: #b83d30;
  border: 1px solid #f6c0ba;
}

.sent-neutral {
  background: #f0f3ef;
  color: #63756a;
}

.news-headline {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #1b2a23;
  line-height: 1.35;
}

.news-headline a {
  color: #1b2a23;
  text-decoration: none;
  display: inline;
}

.news-headline a:hover {
  color: #225c43;
  text-decoration: underline;
}

.ext-icon {
  display: inline-block;
  margin-left: 3px;
  color: #798d81;
}

.ai-summary-box {
  padding: 9px 12px;
  background: #f4f8f3;
  border-left: 3px solid #225c43;
  border-radius: 0 5px 5px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: 8px 'DM Mono', monospace;
  font-weight: 700;
  color: #225c43;
  letter-spacing: 0.05em;
}

.ai-summary-box p {
  margin: 0;
  font-size: 11px;
  color: #3b4e43;
  line-height: 1.45;
}

.news-card-foot {
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #edf1eb;
  font: 9px 'DM Mono', monospace;
  color: #8c9e93;
}

.read-source-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: #225c43;
  text-decoration: none;
  font-weight: 600;
}

.read-source-link:hover {
  text-decoration: underline;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 16px;
  gap: 8px;
}

.empty-icon {
  color: #a4b4a9;
}

.empty-state h4 {
  margin: 0;
  font-size: 14px;
  color: #314238;
}

.empty-state p {
  margin: 0;
  font-size: 12px;
  color: #798b80;
}

@media (max-width: 900px) {
  .news-grid {
    grid-template-columns: 1fr;
  }
  .event-item {
    grid-template-columns: 90px 1fr;
  }
  .event-meta-col {
    grid-column: 1 / -1;
    flex-direction: row;
    align-items: center;
  }
}

@media (max-width: 600px) {
  .view-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .sources-grid {
    flex-direction: column;
  }
  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .values-grid {
    flex-direction: column;
    gap: 6px;
  }
}
</style>
