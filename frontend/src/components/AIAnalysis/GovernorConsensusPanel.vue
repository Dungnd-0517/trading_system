<script setup>
import { computed, ref } from 'vue'
import {
  Activity,
  AlertTriangle,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  Lock,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Unlock,
  Zap,
} from 'lucide-vue-next'
import { agentStore } from '../../stores/agentStore'

const emit = defineEmits(['open-knowledge', 'open-strategy'])

const showOverrideModal = ref(false)
const overrideForm = ref({
  risk_per_trade_percent: 1.0,
  atr_sl_multiplier: 1.5,
  min_risk_reward_ratio: 1.5,
  trading_allowed: true,
})
const overrideError = ref('')
const overrideSuccess = ref(false)

const consensus = computed(() => agentStore.consensus)
const params = computed(() => agentStore.runtimeParams || consensus.value?.active_params || {
  risk_per_trade_percent: 1.0,
  min_risk_reward_ratio: 1.5,
  atr_sl_multiplier: 1.5,
  trading_allowed: true,
  halt_reason: null,
  updated_by_agent: 'SYSTEM_INIT',
})

const regimeBadge = computed(() => {
  const r = consensus.value?.market_regime || 'COMPRESSION_CHOP'
  if (r === 'TRENDING_EXPANSION') {
    return { label: 'TRENDING EXPANSION', cls: 'regime-trending', desc: 'Thị trường có xu hướng mạnh' }
  }
  if (r === 'HIGH_VOLATILITY_EXPANSION') {
    return { label: 'HIGH VOLATILITY', cls: 'regime-volatile', desc: 'Biến động cao, thận trọng rủi ro' }
  }
  return { label: 'COMPRESSION / CHOP', cls: 'regime-chop', desc: 'Biên độ nén, sideway tích lũy' }
})

const biasBadge = computed(() => {
  const b = consensus.value?.suggested_bias || 'NEUTRAL'
  if (b === 'BULLISH') return { label: 'BULLISH', cls: 'bias-bullish', icon: TrendingUp }
  if (b === 'BEARISH') return { label: 'BEARISH', cls: 'bias-bearish', icon: TrendingDown }
  return { label: 'NEUTRAL', cls: 'bias-neutral', icon: Activity }
})

const confidencePercent = computed(() => {
  const score = consensus.value?.confidence_score
  return typeof score === 'number' ? Math.round(score * 100) : 80
})

const dailyDrawdownPercent = computed(() => {
  const dd = consensus.value?.current_daily_drawdown_pct
  return typeof dd === 'number' ? dd.toFixed(2) : '0.00'
})

const isReflexionAdjusted = computed(() => {
  return Number(params.value?.atr_sl_multiplier || 1.5) > 1.6
})

async function triggerEvaluate() {
  try {
    await agentStore.evaluateConsensus()
  } catch (err) {
    console.error('Evaluate failed:', err)
  }
}

function openOverride() {
  overrideForm.value = {
    risk_per_trade_percent: Number(params.value.risk_per_trade_percent) || 1.0,
    atr_sl_multiplier: Number(params.value.atr_sl_multiplier) || 1.5,
    min_risk_reward_ratio: Number(params.value.min_risk_reward_ratio) || 1.5,
    trading_allowed: params.value.trading_allowed ?? true,
  }
  overrideError.value = ''
  overrideSuccess.value = false
  showOverrideModal.value = true
}

async function submitOverride() {
  overrideError.value = ''
  overrideSuccess.value = false
  try {
    await agentStore.overrideParams({
      risk_per_trade_percent: Number(overrideForm.value.risk_per_trade_percent),
      atr_sl_multiplier: Number(overrideForm.value.atr_sl_multiplier),
      min_risk_reward_ratio: Number(overrideForm.value.min_risk_reward_ratio),
      trading_allowed: Boolean(overrideForm.value.trading_allowed),
    })
    overrideSuccess.value = true
    setTimeout(() => {
      showOverrideModal.value = false
      overrideSuccess.value = false
    }, 900)
  } catch (err) {
    overrideError.value = err.message || 'Lỗi khi lưu can thiệp thủ công'
  }
}
</script>

<template>
  <section class="governor-panel">
    <!-- Header -->
    <header class="panel-header">
      <div class="header-title">
        <span class="brain-icon"><BrainCircuit :size="16" /></span>
        <div>
          <h2>Strategy Governor</h2>
          <small>AI Hard Guardrails &middot; Consensus</small>
        </div>
      </div>
      <div class="header-actions">
        <button
          class="action-btn"
          title="Mở Thư viện Tri thức RAG"
          @click="emit('open-knowledge')"
        >
          <BookOpen :size="12" />
          <span>RAG</span>
        </button>
        <button
          class="action-btn"
          title="Tùy chỉnh thông số trong giới hạn an toàn"
          @click="openOverride"
        >
          <Sliders :size="12" />
        </button>
        <button
          class="action-btn primary"
          :disabled="agentStore.evaluating"
          title="Đánh giá lại đồng thuận tức thì"
          @click="triggerEvaluate"
        >
          <RefreshCw :size="12" :class="{ spinning: agentStore.evaluating }" />
        </button>
      </div>
    </header>

    <div class="panel-body">
      <!-- Market Regime & Bias Banner -->
      <div class="regime-banner" :class="regimeBadge.cls">
        <div class="regime-meta">
          <span class="regime-tag">{{ regimeBadge.label }}</span>
          <span class="bias-tag" :class="biasBadge.cls">
            <component :is="biasBadge.icon" :size="11" />
            {{ biasBadge.label }}
          </span>
        </div>
        <div class="confidence-box">
          <div class="confidence-header">
            <span>Độ tin cậy</span>
            <strong>{{ confidencePercent }}%</strong>
          </div>
          <div class="confidence-bar">
            <div class="confidence-fill" :style="{ width: `${confidencePercent}%` }"></div>
          </div>
        </div>
      </div>

      <!-- Rationale Snippet -->
      <div v-if="consensus?.rationale" class="rationale-box">
        <Sparkles :size="12" class="sparkle-icon" />
        <span>{{ consensus.rationale }}</span>
      </div>

      <!-- Parameters Guardrails Matrix -->
      <div class="param-grid">
        <div class="param-card">
          <div class="param-label">
            <span>RỦI RO / LỆNH</span>
            <small class="guard-pill">[0.25 - 1.5%]</small>
          </div>
          <div class="param-val">
            <strong>{{ Number(params.risk_per_trade_percent).toFixed(2) }}%</strong>
          </div>
        </div>

        <div class="param-card" :class="{ 'reflexion-glow': isReflexionAdjusted }">
          <div class="param-label">
            <span>SL MULTIPLIER</span>
            <span v-if="isReflexionAdjusted" class="reflexion-chip" title="Reflexion tự động mở rộng SL do lỗi SL_TOO_TIGHT">+ADAPTED</span>
          </div>
          <div class="param-val">
            <strong>{{ Number(params.atr_sl_multiplier).toFixed(2) }}x ATR</strong>
          </div>
        </div>

        <div class="param-card">
          <div class="param-label">
            <span>MIN R:R</span>
            <small class="guard-pill">&ge; 1.20</small>
          </div>
          <div class="param-val">
            <strong>1 : {{ Number(params.min_risk_reward_ratio).toFixed(1) }}</strong>
          </div>
        </div>

        <div class="param-card" :class="{ 'drawdown-warn': Number(dailyDrawdownPercent) > 1.5 }">
          <div class="param-label">
            <span>LỖ TRONG NGÀY</span>
            <small class="guard-pill">MAX 3.0%</small>
          </div>
          <div class="param-val">
            <strong>{{ dailyDrawdownPercent }}%</strong>
          </div>
        </div>
      </div>

      <!-- Trading Status / Circuit Breaker State -->
      <div
        class="status-strip-state"
        :class="params.trading_allowed ? 'status-allowed' : 'status-halted'"
      >
        <template v-if="params.trading_allowed">
          <ShieldCheck :size="14" class="status-icon" />
          <div class="status-info">
            <strong>CHO PHÉP GIAO DỊCH</strong>
            <small>Hard Guardrails đang giám sát 24/7</small>
          </div>
        </template>
        <template v-else>
          <ShieldAlert :size="14" class="status-icon pulse-red" />
          <div class="status-info">
            <strong class="text-danger">NGẮT MẠCH: DỪNG VÀO LỆNH</strong>
            <small class="halt-reason">{{ params.halt_reason || 'Bảo vệ rủi ro kích hoạt' }}</small>
          </div>
        </template>
      </div>
    </div>

    <!-- Modal Override thủ công -->
    <div v-if="showOverrideModal" class="modal-backdrop" @click.self="showOverrideModal = false">
      <div class="modal-dialog">
        <header class="modal-header">
          <div>
            <h3>Can Thiệp Tham Số An Toàn</h3>
            <small>Hard Guardrails sẽ tự động kẹp biên độ nếu vượt ngưỡng</small>
          </div>
          <button class="close-btn" @click="showOverrideModal = false">&times;</button>
        </header>

        <form class="modal-form" @submit.prevent="submitOverride">
          <div class="form-group">
            <label>
              <span>Rủi ro mỗi lệnh (%)</span>
              <small>Giới hạn: 0.25% &rarr; 1.50%</small>
            </label>
            <div class="input-range-wrap">
              <input
                v-model.number="overrideForm.risk_per_trade_percent"
                type="range"
                min="0.25"
                max="1.50"
                step="0.05"
              />
              <span class="range-val">{{ Number(overrideForm.risk_per_trade_percent).toFixed(2) }}%</span>
            </div>
          </div>

          <div class="form-group">
            <label>
              <span>ATR SL Multiplier</span>
              <small>Giới hạn: 1.00 &rarr; 3.00</small>
            </label>
            <div class="input-range-wrap">
              <input
                v-model.number="overrideForm.atr_sl_multiplier"
                type="range"
                min="1.00"
                max="3.00"
                step="0.10"
              />
              <span class="range-val">{{ Number(overrideForm.atr_sl_multiplier).toFixed(2) }}x</span>
            </div>
          </div>

          <div class="form-group">
            <label>
              <span>Min Risk:Reward Ratio</span>
              <small>Giới hạn: 1.20 &rarr; 3.00</small>
            </label>
            <div class="input-range-wrap">
              <input
                v-model.number="overrideForm.min_risk_reward_ratio"
                type="range"
                min="1.20"
                max="3.00"
                step="0.10"
              />
              <span class="range-val">1 : {{ Number(overrideForm.min_risk_reward_ratio).toFixed(1) }}</span>
            </div>
          </div>

          <div class="form-group toggle-group">
            <label>
              <span>Quyền Mở Lệnh Tự Động</span>
              <small>Tắt để dừng tức thời mọi tín hiệu</small>
            </label>
            <button
              type="button"
              class="toggle-btn"
              :class="{ active: overrideForm.trading_allowed }"
              @click="overrideForm.trading_allowed = !overrideForm.trading_allowed"
            >
              <component :is="overrideForm.trading_allowed ? Unlock : Lock" :size="12" />
              <span>{{ overrideForm.trading_allowed ? 'BẬT' : 'KHÓA' }}</span>
            </button>
          </div>

          <div v-if="overrideError" class="form-alert error">
            <AlertTriangle :size="13" />
            <span>{{ overrideError }}</span>
          </div>

          <div v-if="overrideSuccess" class="form-alert success">
            <CheckCircle2 :size="13" />
            <span>Đã đồng bộ tham số vào PostgreSQL &amp; Redis!</span>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-cancel" @click="showOverrideModal = false">Đóng</button>
            <button type="submit" class="btn-submit" :disabled="agentStore.overriding">
              <Zap :size="13" />
              <span>Lưu Áp Dụng</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.governor-panel {
  overflow: hidden;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  background: #f8faf6;
  font-family: inherit;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.04);
}

.panel-header {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #e4e9e3;
  background: #ffffff;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brain-icon {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: #225c43;
  color: #c9f06b;
}

.header-title h2 {
  margin: 0;
  font-size: 11px;
  font-weight: 800;
  color: #1b2a23;
  letter-spacing: -0.01em;
}

.header-title small {
  display: block;
  font: 8px 'DM Mono', monospace;
  color: #718277;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn {
  height: 25px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 7px;
  border: 1px solid #d0ded0;
  border-radius: 5px;
  background: #f2f6f1;
  color: #435449;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: #e1ebe0;
  color: #225c43;
}

.action-btn.primary {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}

.action-btn.primary:hover {
  background: #1b4d37;
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.panel-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Regime Banner */
.regime-banner {
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px solid transparent;
}

.regime-trending {
  background: #e6f7ec;
  border-color: #bbf0cc;
  color: #135e38;
}

.regime-chop {
  background: #fef7e7;
  border-color: #fce2a6;
  color: #8c5b05;
}

.regime-volatile {
  background: #fdeeee;
  border-color: #facdcd;
  color: #9c2727;
}

.regime-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.regime-tag {
  font: 9px 'DM Mono', monospace;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.bias-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font: 9px 'DM Mono', monospace;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 4px;
}

.bias-bullish {
  background: #15803d;
  color: #ffffff;
}

.bias-bearish {
  background: #b91c1c;
  color: #ffffff;
}

.bias-neutral {
  background: #64748b;
  color: #ffffff;
}

.confidence-box {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.confidence-header {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  font-family: 'DM Mono', monospace;
  color: inherit;
  opacity: 0.85;
}

.confidence-bar {
  height: 4px;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 2px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: currentColor;
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* Rationale */
.rationale-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 8px;
  background: #ffffff;
  border: 1px dashed #cedcce;
  border-radius: 5px;
  font-size: 10px;
  line-height: 1.35;
  color: #495a4f;
}

.sparkle-icon {
  color: #059669;
  flex-shrink: 0;
  margin-top: 1px;
}

/* Parameters Matrix */
.param-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.param-card {
  background: #ffffff;
  border: 1px solid #dce4dc;
  border-radius: 6px;
  padding: 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: all 0.15s ease;
}

.param-card:hover {
  border-color: #b8cfb8;
}

.param-card.reflexion-glow {
  background: #f0fdf4;
  border-color: #86efac;
}

.param-card.drawdown-warn {
  background: #fff1f2;
  border-color: #fecdd3;
}

.param-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font: 8px 'DM Mono', monospace;
  font-weight: 700;
  color: #6d7f73;
}

.guard-pill {
  font-size: 7px;
  color: #94a397;
}

.reflexion-chip {
  font: 7px 'DM Mono', monospace;
  font-weight: 800;
  padding: 1px 4px;
  border-radius: 3px;
  background: #16a34a;
  color: #ffffff;
  letter-spacing: 0.02em;
}

.param-val strong {
  font: 12px 'DM Mono', monospace;
  font-weight: 800;
  color: #1b2a23;
}

/* Status Strip */
.status-strip-state {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  border: 1px solid transparent;
}

.status-allowed {
  background: #eef7ee;
  border-color: #cce4cc;
  color: #1c6b3e;
}

.status-halted {
  background: #fdf0f0;
  border-color: #f7cece;
  color: #b91c1c;
}

.status-icon {
  flex-shrink: 0;
}

.pulse-red {
  animation: pulseRed 1.4s infinite;
}

@keyframes pulseRed {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.15); }
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.status-info strong {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.status-info small {
  font-size: 9px;
  color: #617367;
}

.halt-reason {
  color: #dc2626 !important;
  font-weight: 600;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 20, 0.6);
  backdrop-filter: blur(2px);
  display: grid;
  place-items: center;
  z-index: 9999;
  padding: 16px;
}

.modal-dialog {
  width: 100%;
  max-width: 420px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #ccdccb;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f4f8f3;
  border-bottom: 1px solid #e1e9df;
}

.modal-header h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 800;
  color: #1b2a23;
}

.modal-header small {
  color: #6b7d72;
  font-size: 10px;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 18px;
  color: #6d7f73;
  cursor: pointer;
  line-height: 1;
}

.close-btn:hover {
  color: #1b2a23;
}

.modal-form {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 700;
  color: #27372d;
}

.form-group label small {
  font: 9px 'DM Mono', monospace;
  color: #718377;
}

.input-range-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.input-range-wrap input[type='range'] {
  flex: 1;
  accent-color: #225c43;
}

.range-val {
  font: 11px 'DM Mono', monospace;
  font-weight: 800;
  color: #225c43;
  min-width: 55px;
  text-align: right;
}

.toggle-group {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding-top: 4px;
}

.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 5px;
  border: 1px solid #ccdccb;
  background: #f0f4ef;
  color: #55665b;
  font: 10px 'DM Mono', monospace;
  font-weight: 800;
  cursor: pointer;
}

.toggle-btn.active {
  background: #225c43;
  color: #c9f06b;
  border-color: #225c43;
}

.form-alert {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 5px;
  font-size: 11px;
}

.form-alert.error {
  background: #fee2e2;
  color: #dc2626;
  border: 1px solid #fca5a5;
}

.form-alert.success {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 6px;
  border-top: 1px solid #edf2ec;
}

.btn-cancel {
  padding: 6px 12px;
  border: 1px solid #d5ded6;
  border-radius: 5px;
  background: #f8faf6;
  color: #5a6d61;
  font-size: 11px;
  font-weight: 700;
}

.btn-submit {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border: none;
  border-radius: 5px;
  background: #225c43;
  color: #c9f06b;
  font-size: 11px;
  font-weight: 800;
  cursor: pointer;
}

.btn-submit:hover {
  background: #184632;
}

.btn-submit:disabled {
  opacity: 0.6;
}
</style>
