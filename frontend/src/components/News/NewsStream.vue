<script setup>
import { ExternalLink, Newspaper } from 'lucide-vue-next'
import { onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  news: { type: Array, default: () => [] },
  events: { type: Array, default: () => [] },
  sources: { type: Object, default: () => ({}) },
})
const now = ref(Date.now())
let timer

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
  if (event.timezone_status !== 'VERIFIED' || !event.event_timestamp) return 'TIME UNVERIFIED'
  const seconds = Math.floor((new Date(event.event_timestamp).getTime() - now.value) / 1000)
  if (seconds <= 0) return 'RELEASED'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return hours ? `IN ${hours}H ${minutes}M` : `IN ${minutes}M`
}

function utcTime(value) {
  return new Date(value).toLocaleTimeString('vi-VN', {
    hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
  })
}

onMounted(() => { timer = window.setInterval(() => { now.value = Date.now() }, 30_000) })
onUnmounted(() => window.clearInterval(timer))
</script>

<template>
  <section class="news-panel">
    <header><div><Newspaper :size="15" /><h2>News &amp; events</h2></div><span class="feed-state">UTC</span></header>
    <div class="source-status" aria-label="News source status">
      <span v-for="source in ['FairEconomy', 'Kitco News', 'FXStreet News']" :key="source" :class="['source-pill', sourceClass(source)]">
        <i></i>{{ source }} · {{ sourceLabel(source) }}
      </span>
    </div>
    <h3>Economic calendar</h3>
    <ul v-if="events.length" class="news-list">
      <li v-for="event in events" :key="`event-${event.id}`">
        <time>{{ event.event_timestamp ? utcTime(event.event_timestamp) : '--:--' }}</time>
        <div class="news-copy">
          <p>{{ event.title }}</p>
          <span>{{ event.currency }} · {{ event.source }} · {{ stars(event) }}</span>
          <small :class="{ unverified: event.timezone_status !== 'VERIFIED' }">{{ countdown(event) }}</small>
        </div>
      </li>
    </ul>
    <div v-else class="empty-news">No economic events collected</div>
    <h3>Breaking news</h3>
    <ul v-if="news.length" class="news-list">
      <li v-for="item in news" :key="`news-${item.id}`">
        <time>{{ utcTime(item.published_at) }}</time>
        <div class="news-copy">
          <p>{{ item.title }}</p>
          <span>{{ item.source }} · {{ stars(item) }}</span>
          <a v-if="item.source_url" :href="item.source_url" target="_blank" rel="noopener noreferrer" :aria-label="`Open source article: ${item.title}`"><ExternalLink :size="12" /> Source</a>
        </div>
      </li>
    </ul>
    <div v-else class="empty-news">No headlines collected</div>
  </section>
</template>

<style scoped>
.news-panel { border: 1px solid #d5ded6; border-radius: 7px; background: #f8faf6; }
header { min-height: 43px; display: flex; align-items: center; justify-content: space-between; padding: 0 12px; border-bottom: 1px solid #e4e9e3; }
header div { display: flex; align-items: center; gap: 8px; color: #526359; }
h2 { margin: 0; color: #29382e; font-size: 11px; font-weight: 700; }
.feed-state { color: #87938a; font: 9px 'DM Mono', monospace; }
.source-status { display: flex; flex-wrap: wrap; gap: 5px; padding: 9px 12px 2px; }
.source-pill { display: inline-flex; align-items: center; gap: 5px; color: #68766d; font: 8px 'DM Mono', monospace; }
.source-pill i { width: 5px; height: 5px; border-radius: 50%; background: #b6a06b; }
.source-pill.healthy i { background: #52936d; }
.source-pill.stale i { background: #cf6858; }
h3 { margin: 10px 12px 0; color: #9b7462; font: 8px 'DM Mono', monospace; text-transform: uppercase; }
.news-list { margin: 0; padding: 0 12px; list-style: none; }
.news-list li { display: grid; grid-template-columns: 42px 1fr; gap: 8px; padding: 10px 0; border-bottom: 1px solid #edf0eb; }
.news-list li:last-child { border: 0; }
time { color: #9b7462; font: 9px 'DM Mono', monospace; padding-top: 2px; }
p { margin: 0 0 5px; color: #37463c; font-size: 10px; line-height: 1.5; }
li span, li small { color: #929c94; font: 8px 'DM Mono', monospace; }
.news-copy { min-width: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 3px; }
.news-copy a { display: inline-flex; align-items: center; gap: 4px; color: #4772a3; font: 8px 'DM Mono', monospace; text-decoration: none; }
.news-copy a:hover { text-decoration: underline; }
li small.unverified { color: #b35d52; }
.empty-news { padding: 19px 12px; color: #909b92; font-size: 10px; }
</style>