<script setup>
import { computed } from 'vue'
import { Gauge, TrendingUp, TrendingDown, Minus, Info } from 'lucide-vue-next'

const props = defineProps({
  news: {
    type: Array,
    default: () => [],
  },
})

const analyzedNews = computed(() =>
  props.news.filter((item) => typeof item.sentiment_score === 'number')
)

const score = computed(() => {
  if (!analyzedNews.value.length) return null
  const total = analyzedNews.value.reduce((sum, item) => sum + item.sentiment_score, 0)
  return total / analyzedNews.value.length
})

const counts = computed(() => {
  let bull = 0
  let bear = 0
  let neut = 0
  for (const item of analyzedNews.value) {
    if (item.sentiment_score > 0.1) bull++
    else if (item.sentiment_score < -0.1) bear++
    else neut++
  }
  return { bull, bear, neut, total: analyzedNews.value.length }
})

const bias = computed(() => {
  if (score.value === null) return null
  if (score.value > 0.1) return 'BULLISH'
  if (score.value < -0.1) return 'BEARISH'
  return 'NEUTRAL'
})

const marker = computed(() => {
  if (score.value === null) return '50%'
  const clamped = Math.max(-1.0, Math.min(1.0, score.value))
  return `${Math.max(2, Math.min(98, (clamped + 1) * 50))}%`
})

const formattedScore = computed(() => {
  if (score.value === null) return '—'
  return score.value > 0 ? `+${score.value.toFixed(2)}` : score.value.toFixed(2)
})

const sentimentSummary = computed(() => {
  if (score.value === null) return 'Awaiting analysis'
  if (score.value > 0.1) {
    return 'Safe-haven & USD ease favoring Gold'
  } else if (score.value < -0.1) {
    return 'USD strength & yields pressuring Gold'
  }
  return 'Balanced macro conditions for Gold'
})
</script>

<template>
  <section class="sentiment-panel">
    <header>
      <div class="header-left">
        <Gauge :size="15" />
        <h2>News sentiment</h2>
      </div>
      <div class="header-right">
        <span v-if="bias" :class="['bias-pill', `bias-${bias.toLowerCase()}`]">
          <TrendingUp v-if="bias === 'BULLISH'" :size="10" />
          <TrendingDown v-else-if="bias === 'BEARISH'" :size="10" />
          <Minus v-else :size="10" />
          {{ bias }}
        </span>
        <span class="ai-badge">AI CONTEXT</span>
      </div>
    </header>

    <div class="sentiment-body">
      <div class="scale">
        <span :class="{ active: bias === 'BEARISH' }">BEARISH</span>
        <span :class="{ active: bias === 'NEUTRAL' }">NEUTRAL</span>
        <span :class="{ active: bias === 'BULLISH' }">BULLISH</span>
      </div>

      <div class="track-wrapper">
        <div class="track">
          <div class="center-tick" title="Neutral 0.00"></div>
          <i
            class="pointer"
            :style="{ left: marker }"
            :title="score !== null ? `Sentiment: ${formattedScore} (${bias})` : 'Awaiting analysis'"
          ></i>
        </div>
      </div>

      <div class="score-row">
        <div class="score-value">
          <strong :class="[score !== null ? (score > 0.1 ? 'text-bull' : score < -0.1 ? 'text-bear' : 'text-neutral') : '']">
            {{ formattedScore }}
          </strong>
          <span class="score-sub">{{ sentimentSummary }}</span>
        </div>

        <div v-if="counts.total > 0" class="breakdown-chips">
          <span class="chip chip-bull" title="Tin tức Bullish (Tăng)">{{ counts.bull }}↑</span>
          <span class="chip chip-neut" title="Tin tức Neutral (Trung tính)">{{ counts.neut }}–</span>
          <span class="chip chip-bear" title="Tin tức Bearish (Giảm)">{{ counts.bear }}↓</span>
        </div>
        <div v-else class="breakdown-chips">
          <span class="chip chip-empty">0 headlines</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.sentiment-panel {
  border: 1px solid #d5ded6;
  border-radius: 7px;
  background: #f8faf6;
  transition: border-color 0.2s, box-shadow 0.2s;
}

header {
  min-height: 43px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #e4e9e3;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #526359;
}

h2 {
  margin: 0;
  color: #29382e;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ai-badge {
  color: #87938a;
  font: 8px 'DM Mono', monospace;
  letter-spacing: 0.05em;
}

.bias-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;
  border-radius: 4px;
  font: 600 8px 'DM Mono', monospace;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.bias-bullish {
  background: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.bias-bearish {
  background: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}

.bias-neutral {
  background: #eceff1;
  color: #546e7a;
  border: 1px solid #cfd8dc;
}

.sentiment-body {
  padding: 12px 12px 11px;
}

.scale {
  display: flex;
  justify-content: space-between;
  color: #98a198;
  font: 8px 'DM Mono', monospace;
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}

.scale span.active {
  color: #29382e;
  font-weight: 700;
}

.track-wrapper {
  position: relative;
  padding: 4px 0;
}

.track {
  height: 6px;
  position: relative;
  border-radius: 6px;
  background: linear-gradient(90deg, #ce796b 0%, #d3bd7e 50%, #71a17b 100%);
}

.center-tick {
  position: absolute;
  top: 0;
  left: 50%;
  width: 2px;
  height: 6px;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.6);
  pointer-events: none;
}

.pointer {
  position: absolute;
  top: -3px;
  width: 12px;
  height: 12px;
  transform: translateX(-50%);
  border: 2px solid #f8faf6;
  border-radius: 50%;
  background: #273a2e;
  box-shadow: 0 0 0 1px #273a2e, 0 1px 3px rgba(0, 0, 0, 0.25);
  transition: left 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
}

.pointer:hover {
  transform: translateX(-50%) scale(1.15);
}

.score-row {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.score-value {
  display: flex;
  align-items: baseline;
  gap: 7px;
  min-width: 0;
  overflow: hidden;
}

.score-value strong {
  color: #33463a;
  font: 17px 'DM Mono', monospace;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.text-bull {
  color: #2e7d32 !important;
}

.text-bear {
  color: #c62828 !important;
}

.text-neutral {
  color: #455a64 !important;
}

.score-sub {
  color: #8b968e;
  font-size: 9px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.breakdown-chips {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}

.chip {
  padding: 1px 4px;
  border-radius: 3px;
  font: 8px 'DM Mono', monospace;
  font-weight: 600;
}

.chip-bull {
  background: #e8f5e9;
  color: #2e7d32;
}

.chip-neut {
  background: #eceff1;
  color: #607d8b;
}

.chip-bear {
  background: #ffebee;
  color: #c62828;
}

.chip-empty {
  color: #9e9e9e;
}
</style>