<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  ArrowUpRight,
  CalendarDays,
  ExternalLink,
  Newspaper,
} from 'lucide-vue-next'

const props = defineProps({
  news: { type: Array, default: () => [] },
  events: { type: Array, default: () => [] },
  sources: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['navigate-calendar', 'navigate-news'])

// Timezone preference (defaults to ICT 'Asia/Ho_Chi_Minh', switchable to UTC)
const activeTimezone = ref('Asia/Ho_Chi_Minh')
const isUtc = computed(() => activeTimezone.value === 'UTC')

function loadTimezonePreference() {
  try {
    const raw = localStorage.getItem('fieldnote_user_settings')
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed.displayTimezone === 'UTC') {
        activeTimezone.value = 'UTC'
        return
      }
    }
  } catch {
    // fallback
  }
  activeTimezone.value = 'Asia/Ho_Chi_Minh'
}

function toggleTimezone() {
  activeTimezone.value = activeTimezone.value === 'UTC' ? 'Asia/Ho_Chi_Minh' : 'UTC'
}

// 3 Day Tabs: 'yesterday' | 'today' | 'tomorrow' (default: 'today')
const activeDayTab = ref('today')

const now = ref(Date.now())
let clockTimer

function sourceLabel(source) {
  const status = props.sources[source]
  if (!status) return 'WAITING'
  if (status.stale) return 'STALE'
  if (status.fallback_active) return 'FALLBACK'
  return status.status?.toUpperCase() ?? 'WAITING'
}

function sourceClass(source) {
  const label = sourceLabel(source)
  return label === 'HEALTHY' ? 'healthy' : label === 'STALE' || label === 'UNAVAILABLE' ? 'stale' : 'fallback'
}

function stars(item) {
  if (item.classification_status === 'UNKNOWN' || !item.impact_stars) return 'UNCLASSIFIED'
  return `${'★'.repeat(item.impact_stars)}${'☆'.repeat(3 - item.impact_stars)}`
}

function countdown(event) {
  if (event.timezone_status !== 'VERIFIED' || !event.event_timestamp) {
    return { text: 'TIME UNVERIFIED', status: 'unverified' }
  }
  const seconds = Math.floor((new Date(event.event_timestamp).getTime() - now.value) / 1000)
  if (seconds <= 0) {
    return { text: 'RELEASED', status: 'released' }
  }
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const text = hours ? `IN ${hours}H ${minutes}M` : `IN ${minutes}M`
  return { text, status: 'upcoming' }
}

function formatEventTime(iso) {
  if (!iso) return '--:--'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '--:--'
  return d.toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: activeTimezone.value,
  })
}

function formatNewsTime(iso) {
  if (!iso) return '--:--'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '--:--'
  return d.toLocaleTimeString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: activeTimezone.value,
  })
}

// Date key helper YYYY-MM-DD
function getDayKey(dateOrIso, timeZone) {
  if (!dateOrIso) return null
  const d = typeof dateOrIso === 'string' || typeof dateOrIso === 'number' ? new Date(dateOrIso) : dateOrIso
  if (!d || isNaN(d.getTime())) return null
  try {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone: timeZone || activeTimezone.value,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(d)
  } catch {
    return d.toISOString().slice(0, 10)
  }
}

// Day keys for Yesterday, Today, Tomorrow
const dayKeys = computed(() => {
  const currentDate = new Date(now.value)
  const tz = activeTimezone.value

  const todayKey = getDayKey(currentDate, tz)
  const yesterdayKey = getDayKey(new Date(currentDate.getTime() - 86400000), tz)
  const tomorrowKey = getDayKey(new Date(currentDate.getTime() + 86400000), tz)

  return { yesterday: yesterdayKey, today: todayKey, tomorrow: tomorrowKey }
})

// Filter and sort events chronologically
function filterEventsByDayKey(key) {
  if (!key) return []
  return props.events
    .filter((e) => {
      const eKey = getDayKey(e.event_timestamp || e.provider_time_raw, activeTimezone.value)
      return eKey === key
    })
    .slice()
    .sort((a, b) => {
      const ta = a.event_timestamp ? new Date(a.event_timestamp).getTime() : 0
      const tb = b.event_timestamp ? new Date(b.event_timestamp).getTime() : 0
      return ta - tb
    })
}

const yesterdayEvents = computed(() => filterEventsByDayKey(dayKeys.value.yesterday))
const todayEvents = computed(() => filterEventsByDayKey(dayKeys.value.today))
const tomorrowEvents = computed(() => filterEventsByDayKey(dayKeys.value.tomorrow))

const activeDayEvents = computed(() => {
  if (activeDayTab.value === 'yesterday') return yesterdayEvents.value
  if (activeDayTab.value === 'tomorrow') return tomorrowEvents.value
  return todayEvents.value
})

const activeTabLabel = computed(() => {
  if (activeDayTab.value === 'yesterday') return 'Yesterday'
  if (activeDayTab.value === 'tomorrow') return 'Tomorrow'
  return 'Today'
})

onMounted(() => {
  loadTimezonePreference()
  clockTimer = window.setInterval(() => {
    now.value = Date.now()
  }, 10_000)
})

onUnmounted(() => {
  window.clearInterval(clockTimer)
})
</script>

<template>
  <section class="news-panel">
    <!-- Panel Header with Title and Timezone indicator -->
    <header class="panel-header">
      <div class="panel-title">
        <Newspaper :size="15" />
        <h2>News &amp; Events</h2>
      </div>
      <div class="header-right">
        <button
          type="button"
          class="feed-state-btn"
          :title="`Múi giờ hiển thị: ${isUtc ? 'UTC' : 'ICT'}. Nhấp để chuyển đổi.`"
          @click="toggleTimezone"
        >
          {{ isUtc ? 'UTC' : 'ICT' }}
        </button>
      </div>
    </header>

    <!-- Source Health Pills -->
    <div class="source-status" aria-label="News source status">
      <span
        v-for="source in ['FairEconomy', 'Kitco News', 'FXStreet News']"
        :key="source"
        :class="['source-pill', sourceClass(source)]"
      >
        <i></i>{{ source }} · {{ sourceLabel(source) }}
      </span>
    </div>

    <!-- Section: Economic Calendar -->
    <div class="calendar-section">
      <div class="section-headline">
        <div class="headline-title">
          <CalendarDays :size="13" />
          <h3>Economic Calendar</h3>
        </div>
        <button
          type="button"
          class="btn-shortcut-all"
          title="Chuyển sang màn hình hiển thị toàn bộ Economic Calendar"
          @click="emit('navigate-calendar')"
        >
          <span>Toàn bộ lịch</span>
          <ArrowUpRight :size="12" />
        </button>
      </div>

      <!-- 3 Day Tabs: Yesterday, Today (default), Tomorrow -->
      <div class="day-tabs-bar" role="tablist" aria-label="Lịch kinh tế theo ngày">
        <button
          role="tab"
          type="button"
          :aria-selected="activeDayTab === 'yesterday'"
          :class="['day-tab-btn', { active: activeDayTab === 'yesterday' }]"
          @click="activeDayTab = 'yesterday'"
        >
          <span>Yesterday</span>
          <span class="day-badge">{{ yesterdayEvents.length }}</span>
        </button>

        <button
          role="tab"
          type="button"
          :aria-selected="activeDayTab === 'today'"
          :class="['day-tab-btn', { active: activeDayTab === 'today' }]"
          @click="activeDayTab = 'today'"
        >
          <span>Today</span>
          <span class="day-badge">{{ todayEvents.length }}</span>
        </button>

        <button
          role="tab"
          type="button"
          :aria-selected="activeDayTab === 'tomorrow'"
          :class="['day-tab-btn', { active: activeDayTab === 'tomorrow' }]"
          @click="activeDayTab = 'tomorrow'"
        >
          <span>Tomorrow</span>
          <span class="day-badge">{{ tomorrowEvents.length }}</span>
        </button>
      </div>

      <!-- Day Events List -->
      <ul v-if="activeDayEvents.length" class="news-list calendar-list">
        <li
          v-for="event in activeDayEvents"
          :key="`event-${event.id}`"
          :class="['calendar-item', `impact-${event.impact_stars || 0}`]"
        >
          <div class="time-col">
            <time>{{ formatEventTime(event.event_timestamp) }}</time>
            <span
              :class="['release-tag', countdown(event).status]"
              :title="countdown(event).text"
            >
              {{ countdown(event).text }}
            </span>
          </div>

          <div class="news-copy">
            <p class="event-title">{{ event.title }}</p>
            <div class="event-meta">
              <span class="currency-tag">{{ event.currency }}</span>
              <span :class="['stars-tag', `stars-${event.impact_stars || 0}`]">
                {{ stars(event) }}
              </span>
              <span class="source-tag">{{ event.source }}</span>
            </div>

            <!-- Economic Values (Actual, Forecast, Previous) -->
            <div
              v-if="event.actual_value || event.forecast_value || event.previous_value"
              class="event-values"
            >
              <span v-if="event.actual_value" class="val-pill actual">
                <small>Act:</small> <b>{{ event.actual_value }}</b>
              </span>
              <span v-if="event.forecast_value" class="val-pill forecast">
                <small>Frc:</small> {{ event.forecast_value }}
              </span>
              <span v-if="event.previous_value" class="val-pill previous">
                <small>Prev:</small> {{ event.previous_value }}
              </span>
            </div>
          </div>
        </li>
      </ul>
      <div v-else class="empty-news">
        Không có sự kiện kinh tế nào cho {{ activeTabLabel }}
      </div>

      <!-- Button chuyển hướng sang màn hình hiển thị toàn bộ Economic calendar (News & Events) -->
      <div class="calendar-footer-btn-wrapper">
        <button
          type="button"
          class="btn-full-calendar-nav"
          title="Chuyển hướng sang màn hình hiển thị toàn bộ Economic Calendar (News & Events)"
          @click="emit('navigate-calendar')"
        >
          <CalendarDays :size="13" />
          <span>Xem toàn bộ Economic Calendar</span>
          <ArrowUpRight :size="13" />
        </button>
      </div>
    </div>

    <!-- Section: Breaking News -->
    <div class="news-section">
      <div class="section-headline">
        <div class="headline-title">
          <Newspaper :size="13" />
          <h3>Breaking News</h3>
        </div>
        <button
          type="button"
          class="btn-shortcut-all"
          title="Chuyển sang toàn bộ tin tức (News & Events)"
          @click="emit('navigate-news')"
        >
          <span>Xem tất cả</span>
          <ArrowUpRight :size="12" />
        </button>
      </div>

      <ul v-if="news.length" class="news-list headlines-list">
        <li v-for="item in news.slice(0, 10)" :key="`news-${item.id}`">
          <time>{{ formatNewsTime(item.published_at) }}</time>
          <div class="news-copy">
            <p>{{ item.title }}</p>
            <div class="news-meta">
              <span class="source-tag">{{ item.source }}</span>
              <span v-if="item.impact_stars" :class="['stars-tag', `stars-${item.impact_stars}`]">{{ stars(item) }}</span>
              <a
                v-if="item.source_url"
                :href="item.source_url"
                target="_blank"
                rel="noopener noreferrer"
                :aria-label="`Open source article: ${item.title}`"
              >
                <ExternalLink :size="10" /> Source
              </a>
            </div>
          </div>
        </li>
      </ul>
      <div v-else class="empty-news">No headlines collected</div>
    </div>
  </section>
</template>

<style scoped>
.news-panel {
  border: 1px solid #d5ded6;
  border-radius: 7px;
  background: #f8faf6;
  display: flex;
  flex-direction: column;
}

.panel-header {
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #e4e9e3;
  background: #f4f7f2;
  border-radius: 6px 6px 0 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #35473d;
}

h2 {
  margin: 0;
  color: #223328;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.feed-state-btn {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border: 1px solid #c9d5cb;
  border-radius: 4px;
  background: #ffffff;
  color: #4a5c51;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.feed-state-btn:hover {
  background: #e5ece3;
  color: #225c43;
}

.source-status {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  padding: 8px 12px 6px;
  border-bottom: 1px solid #edf1eb;
}

.source-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #68766d;
  font: 8px 'DM Mono', monospace;
}

.source-pill i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #b6a06b;
}

.source-pill.healthy i {
  background: #52936d;
}

.source-pill.stale i {
  background: #cf6858;
}

/* Sections */
.calendar-section {
  padding: 10px 12px 8px;
  border-bottom: 1px solid #e7ede5;
}

.news-section {
  padding: 10px 12px 10px;
}

.section-headline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.headline-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #9b7462;
}

h3 {
  margin: 0;
  color: #9b7462;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.btn-shortcut-all {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 7px;
  border: 1px solid #d4ded3;
  border-radius: 4px;
  background: #fbfdfb;
  color: #225c43;
  font: 9px 'DM Mono', monospace;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-shortcut-all:hover {
  background: #e2ede0;
  border-color: #b7ceb4;
  color: #194431;
}

/* Day tabs */
.day-tabs-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #eaf0e8;
  padding: 3px;
  border-radius: 6px;
  margin-bottom: 9px;
  border: 1px solid #d8e2d6;
}

.day-tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 25px;
  padding: 0 4px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: #55675c;
  font: 9px 'DM Mono', monospace;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.day-tab-btn:hover {
  background: #f3f7f2;
  color: #225c43;
}

.day-tab-btn.active {
  background: #ffffff;
  color: #225c43;
  font-weight: 700;
  border-color: #cfdccd;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.08);
}

.day-badge {
  font: 8px 'DM Mono', monospace;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 4px;
  background: #d7e2d6;
  color: #405247;
}

.day-tab-btn.active .day-badge {
  background: #225c43;
  color: #c9f06b;
}

/* Event & News Lists */
.news-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.calendar-list {
  max-height: 290px;
  overflow-y: auto;
  padding-right: 2px;
}

.headlines-list {
  max-height: 230px;
  overflow-y: auto;
  padding-right: 2px;
}

/* Scrollbar */
.calendar-list::-webkit-scrollbar,
.headlines-list::-webkit-scrollbar {
  width: 4px;
}

.calendar-list::-webkit-scrollbar-thumb,
.headlines-list::-webkit-scrollbar-thumb {
  background: #cbd6cb;
  border-radius: 2px;
}

.calendar-item {
  display: grid;
  grid-template-columns: 56px 1fr;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #edf0eb;
}

.calendar-item:last-child {
  border-bottom: 0;
}

.headlines-list li {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #edf0eb;
}

.headlines-list li:last-child {
  border-bottom: 0;
}

.time-col {
  display: flex;
  flex-direction: column;
  gap: 3px;
  align-items: flex-start;
}

time {
  color: #9b7462;
  font: 9px 'DM Mono', monospace;
  font-weight: 600;
  padding-top: 1px;
}

.release-tag {
  display: inline-block;
  font: 7px 'DM Mono', monospace;
  font-weight: 700;
  padding: 1px 3px;
  border-radius: 3px;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.release-tag.released {
  background: #e2ede0;
  color: #3b7450;
}

.release-tag.upcoming {
  background: #fbf3e0;
  color: #a46c24;
}

.release-tag.unverified {
  background: #fdeae8;
  color: #ba4737;
}

.news-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
}

.event-title {
  margin: 0;
  color: #29382e;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.45;
}

.headlines-list p {
  margin: 0;
  color: #37463c;
  font-size: 10px;
  line-height: 1.45;
}

.event-meta,
.news-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  color: #8c978e;
  font: 8px 'DM Mono', monospace;
}

.currency-tag {
  display: inline-block;
  padding: 1px 4px;
  border-radius: 3px;
  background: #e1ede0;
  color: #225c43;
  font-weight: 700;
  font-size: 8px;
}

.stars-tag {
  font-size: 8px;
  font-weight: 700;
}

.stars-tag.stars-3 {
  color: #b54029;
}

.stars-tag.stars-2 {
  color: #b77626;
}

.stars-tag.stars-1 {
  color: #6d7f73;
}

.source-tag {
  color: #7b887f;
}

.news-meta a {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: #3f6e9f;
  font: 8px 'DM Mono', monospace;
  text-decoration: none;
}

.news-meta a:hover {
  text-decoration: underline;
}

/* Economic values strip */
.event-values {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 3px;
}

.val-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 5px;
  border-radius: 3px;
  background: #eef3ed;
  border: 1px solid #dce4dc;
  font: 8px 'DM Mono', monospace;
  color: #4f6055;
}

.val-pill small {
  color: #819185;
}

.val-pill.actual {
  background: #e5f3e7;
  border-color: #9ecda9;
  color: #1a562c;
}

.val-pill.actual b {
  font-weight: 700;
}

.empty-news {
  padding: 16px 10px;
  color: #8f9b91;
  font-size: 10px;
  text-align: center;
  font-style: italic;
  background: #f4f7f2;
  border-radius: 5px;
  margin: 6px 0;
}

/* Bottom CTA button */
.calendar-footer-btn-wrapper {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #dbe3d9;
}

.btn-full-calendar-nav {
  width: 100%;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid #c4d7c2;
  border-radius: 5px;
  background: #eef5ed;
  color: #225c43;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-full-calendar-nav:hover {
  background: #dfecdc;
  border-color: #aecdab;
  color: #17422f;
  box-shadow: 0 1px 3px rgba(34, 92, 67, 0.1);
}
</style>