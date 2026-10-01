<script setup>
import { BrainCircuit } from 'lucide-vue-next'
</script>

<template>
  <section class="insights-panel">
    <header><div><BrainCircuit :size="15" /><h2>Market context</h2></div><span class="stage">ADVISOR</span></header>
    <div class="insight-body">
      <div class="context-state"><span class="state-mark">—</span><div><small>REGIME</small><strong>Insufficient data</strong></div></div>
      <p>Analysis will appear after market candles and news are ingested.</p>
      <div class="insight-divider"></div>
      <div class="suggestion"><span>TRADE PERMISSION</span><b>Not evaluated</b></div>
      <div class="suggestion"><span>RISK PARAMETERS</span><b>Awaiting context</b></div>
    </div>
  </section>
</template>

<style scoped>
.insights-panel { overflow: hidden; border: 1px solid #d5ded6; border-radius: 7px; background: #f8faf6; }
header { min-height: 43px; display: flex; align-items: center; justify-content: space-between; padding: 0 12px; border-bottom: 1px solid #e4e9e3; }
header div { display: flex; align-items: center; gap: 8px; color: #526359; }
h2 { margin: 0; color: #29382e; font-size: 11px; }
.stage { padding: 4px 6px; border-radius: 3px; background: #e8eee5; color: #57725d; font: 8px 'DM Mono', monospace; }
.insight-body { padding: 13px 12px; }
.context-state { display: flex; align-items: center; gap: 9px; }
.state-mark { display: grid; place-items: center; width: 29px; height: 29px; border-radius: 6px; background: #e9ede7; color: #748177; font: 16px 'DM Mono', monospace; }
.context-state div { display: grid; gap: 3px; }
small, .suggestion span { color: #97a198; font: 8px 'DM Mono', monospace; }
.context-state strong { color: #657269; font-size: 10px; }
p { margin: 12px 0; color: #859087; font-size: 10px; line-height: 1.6; }
.insight-divider { height: 1px; margin: 11px 0; background: #e9ede7; }
.suggestion { display: flex; justify-content: space-between; gap: 8px; padding: 5px 0; }
.suggestion b { color: #69766d; font: 9px 'DM Mono', monospace; text-align: right; }
</style>