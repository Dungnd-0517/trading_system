<script setup>
import { ArrowUpRight, BrainCircuit } from 'lucide-vue-next'

const emit = defineEmits(['open-strategy'])
</script>

<template>
  <section class="insights-panel">
    <header>
      <div><BrainCircuit :size="15" /><h2>Market Context &amp; Strategy</h2></div>
      <button class="stage-link" title="Xem chi tiết chiến lược SMC" @click="emit('open-strategy')">
        <span>SMC STRATEGY</span>
        <ArrowUpRight :size="10" />
      </button>
    </header>
    <div class="insight-body">
      <div class="context-state">
        <span class="state-mark">SMC</span>
        <div>
          <small>STRATEGY MODEL</small>
          <strong>D1/H4 Bias &middot; H1 POI &middot; M15 CHoCH</strong>
        </div>
      </div>
      <p>Hệ thống giám sát cấu trúc thị trường Smart Money Concepts và các phiên thanh khoản Kill Zone.</p>
      <div class="insight-divider"></div>
      <div class="suggestion"><span>EXECUTION MODE</span><b>Paper Trading 24/7</b></div>
      <div class="suggestion"><span>KILL ZONES</span><b>London &middot; New York AM</b></div>
      <div class="action-row">
        <button class="view-strategy-btn" @click="emit('open-strategy')">
          <span>Xem chi tiết chiến lược &amp; phân tích</span>
          <ArrowUpRight :size="11" />
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.insights-panel {
  overflow: hidden;
  border: 1px solid #d5ded6;
  border-radius: 7px;
  background: #f8faf6;
}

header {
  min-height: 43px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #e4e9e3;
}

header div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #526359;
}

h2 {
  margin: 0;
  color: #29382e;
  font-size: 11px;
  font-weight: 700;
}

.stage-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 6px;
  border-radius: 4px;
  background: #e2ede0;
  color: #225c43;
  font: 8px 'DM Mono', monospace;
  font-weight: 700;
  border: 1px solid #ccdccb;
  cursor: pointer;
  transition: all 0.15s ease;
}

.stage-link:hover {
  background: #225c43;
  color: #c9f06b;
}

.insight-body {
  padding: 12px;
}

.context-state {
  display: flex;
  align-items: center;
  gap: 9px;
}

.state-mark {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #e2ece0;
  color: #225c43;
  font: 11px 'DM Mono', monospace;
  font-weight: 800;
}

.context-state div {
  display: grid;
  gap: 2px;
}

small {
  color: #88948a;
  font: 8px 'DM Mono', monospace;
  font-weight: 700;
}

.context-state strong {
  color: #233328;
  font-size: 10px;
  font-weight: 700;
}

p {
  margin: 9px 0 10px;
  color: #637367;
  font-size: 10px;
  line-height: 1.5;
}

.insight-divider {
  height: 1px;
  margin: 8px 0;
  background: #e9ede7;
}

.suggestion {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 0;
}

.suggestion span {
  color: #8b968d;
  font: 8px 'DM Mono', monospace;
}

.suggestion b {
  color: #49594f;
  font: 9px 'DM Mono', monospace;
  text-align: right;
  font-weight: 600;
}

.action-row {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #dbe3d9;
}

.view-strategy-btn {
  width: 100%;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: 1px solid #ccdccb;
  border-radius: 5px;
  background: #eef5ed;
  color: #225c43;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.view-strategy-btn:hover {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}
</style>