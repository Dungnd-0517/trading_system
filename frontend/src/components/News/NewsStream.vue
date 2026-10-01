<script setup>
import { Newspaper } from 'lucide-vue-next'

defineProps({ news: { type: Array, default: () => [] } })
</script>

<template>
  <section class="news-panel">
    <header><div><Newspaper :size="15" /><h2>News stream</h2></div><span class="feed-state">RSS / API</span></header>
    <ul v-if="news.length" class="news-list">
      <li v-for="item in news" :key="item.id">
        <time>{{ new Date(item.published_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) }}</time>
        <div><p>{{ item.title }}</p><span>{{ item.source }} · {{ item.impact_level }}</span></div>
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
.news-list { margin: 0; padding: 0 12px; list-style: none; }
.news-list li { display: grid; grid-template-columns: 42px 1fr; gap: 8px; padding: 10px 0; border-bottom: 1px solid #edf0eb; }
.news-list li:last-child { border: 0; }
time { color: #9b7462; font: 9px 'DM Mono', monospace; padding-top: 2px; }
p { margin: 0 0 5px; color: #37463c; font-size: 10px; line-height: 1.5; }
li span { color: #929c94; font: 8px 'DM Mono', monospace; }
.empty-news { padding: 19px 12px; color: #909b92; font-size: 10px; }
</style>