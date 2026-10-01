<script setup>
import { computed } from 'vue'
import { Gauge } from 'lucide-vue-next'

const props = defineProps({ news: { type: Array, default: () => [] } })
const score = computed(() => {
  const values = props.news.map((item) => item.sentiment_score).filter((value) => typeof value === 'number')
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null
})
const marker = computed(() => `${Math.max(0, Math.min(100, ((score.value ?? 0) + 1) * 50))}%`)
</script>

<template>
  <section class="sentiment-panel">
    <header><div><Gauge :size="15" /><h2>News sentiment</h2></div><span>AI CONTEXT</span></header>
    <div class="sentiment-body">
      <div class="scale"><span>BEARISH</span><span>NEUTRAL</span><span>BULLISH</span></div>
      <div class="track"><i :style="{ left: marker }"></i></div>
      <div class="score-row"><strong>{{ score === null ? '—' : score.toFixed(2) }}</strong><span>{{ score === null ? 'Awaiting analysis' : `${props.news.length} headlines` }}</span></div>
    </div>
  </section>
</template>

<style scoped>
.sentiment-panel { border: 1px solid #d5ded6; border-radius: 7px; background: #f8faf6; }
header { min-height: 43px; display: flex; align-items: center; justify-content: space-between; padding: 0 12px; border-bottom: 1px solid #e4e9e3; }
header div { display: flex; align-items: center; gap: 8px; color: #526359; }
h2 { margin: 0; color: #29382e; font-size: 11px; }
header > span { color: #87938a; font: 8px 'DM Mono', monospace; }
.sentiment-body { padding: 13px 12px 12px; }
.scale { display: flex; justify-content: space-between; color: #98a198; font: 8px 'DM Mono', monospace; }
.track { height: 6px; position: relative; margin: 10px 0; border-radius: 6px; background: linear-gradient(90deg, #ce796b 0%, #d3bd7e 50%, #71a17b 100%); }
.track i { position: absolute; top: -3px; width: 12px; height: 12px; transform: translateX(-50%); border: 2px solid #f8faf6; border-radius: 50%; background: #273a2e; box-shadow: 0 0 0 1px #273a2e; }
.score-row { display: flex; align-items: baseline; gap: 7px; }
.score-row strong { color: #33463a; font: 17px 'DM Mono', monospace; }
.score-row span { color: #8b968e; font-size: 9px; }
</style>