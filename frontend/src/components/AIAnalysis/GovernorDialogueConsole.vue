<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronRight,
  FileText,
  Lock,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  Terminal,
  User,
  Zap,
} from 'lucide-vue-next'
import { agentStore } from '../../stores/agentStore'

const messagesContainer = ref(null)
const inputMessage = ref('')

const dialogues = computed(() => agentStore.dialogueHistory || [])
const params = computed(() => agentStore.runtimeParams || {
  risk_per_trade_percent: 1.0,
  min_risk_reward_ratio: 1.5,
  atr_sl_multiplier: 1.5,
  trading_allowed: true,
  halt_reason: null,
})
const dailyDrawdown = computed(() => {
  const dd = agentStore.consensus?.current_daily_drawdown_pct
  return typeof dd === 'number' ? dd.toFixed(2) : '0.00'
})

const quickCommands = [
  { label: '🏛️ Báo cáo điều hành', text: 'Báo cáo điều hành' },
  { label: '📉 Hạ rủi ro 0.5%', text: 'Hạ mức rủi ro xuống 0.5%' },
  { label: '⚖️ Đặt rủi ro 1.0%', text: 'Đặt rủi ro 1.0%' },
  { label: '📐 Nới SL 2.0x ATR', text: 'Nới SL lên 2.0x ATR' },
  { label: '⏸️ Tạm dừng giao dịch', text: 'Tạm dừng giao dịch để theo dõi' },
  { label: '▶️ Tiếp tục giao dịch', text: 'Tiếp tục giao dịch' },
  { label: '⚠️ Test vi phạm 5%', text: 'Đặt rủi ro 5.0% gỡ lỗ' },
]

onMounted(() => {
  agentStore.refreshDialogueHistory()
  scrollToBottom()
})

watch(dialogues, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function handleSendMessage() {
  const text = inputMessage.value.trim()
  if (!text || agentStore.sendingDialogue) return
  inputMessage.value = ''
  try {
    await agentStore.sendDialogue(text)
  } catch (err) {
    console.error('Lỗi gửi tin:', err)
  }
}

function handleQuickCommand(text) {
  inputMessage.value = text
  handleSendMessage()
}

async function handleBriefing() {
  try {
    await agentStore.loadExecutiveBriefing()
  } catch (err) {
    console.error('Lỗi briefing:', err)
  }
}

async function handleApproval(dialogueId, action) {
  try {
    await agentStore.respondApproval(dialogueId, action)
  } catch (err) {
    console.error('Lỗi approval:', err)
  }
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('vi-VN', { hour12: false })
  } catch {
    return isoStr
  }
}
</script>

<template>
  <div class="governor-dialogue-console">
    <!-- Header Strip -->
    <header class="console-header">
      <div class="header-main">
        <div class="agent-avatar">
          <Shield :size="18" class="shield-icon" />
          <span class="online-indicator"></span>
        </div>
        <div>
          <div class="title-row">
            <h4>STRATEGY GOVERNOR</h4>
            <span class="cro-badge">CRO &middot; HUMAN-IN-THE-LOOP</span>
          </div>
          <small class="console-sub">Đối thoại 2 chiều Trader &ndash; Governor &middot; Thẩm định Hard Guardrails D21/D24</small>
        </div>
      </div>

      <div class="header-badges">
        <div class="param-tag" :class="params.trading_allowed ? 'tag-active' : 'tag-halt'">
          <span class="dot"></span>
          <span>{{ params.trading_allowed ? 'TRADING ACTIVE' : 'SYSTEM HALTED' }}</span>
        </div>
        <div class="param-tag tag-metric">
          <span>RISK: <b>{{ params.risk_per_trade_percent }}%</b></span>
        </div>
        <div class="param-tag tag-metric">
          <span>ATR SL: <b>{{ params.atr_sl_multiplier }}x</b></span>
        </div>
        <div class="param-tag tag-drawdown">
          <span>DD: <b>{{ dailyDrawdown }}%</b> / 3.0%</span>
        </div>

        <button
          class="briefing-action-btn"
          :disabled="agentStore.loadingBriefing"
          title="Xuất bản bản tin điều hành tóm tắt vĩ mô, kỹ thuật và rủi ro"
          @click="handleBriefing"
        >
          <FileText :size="13" />
          <span>{{ agentStore.loadingBriefing ? 'Đang soạn...' : 'Executive Briefing' }}</span>
        </button>

        <button
          class="icon-refresh-btn"
          :disabled="agentStore.loadingDialogue"
          title="Làm mới lịch sử"
          @click="agentStore.refreshDialogueHistory"
        >
          <RefreshCw :size="13" :class="{ spinning: agentStore.loadingDialogue }" />
        </button>
      </div>
    </header>

    <!-- Message Stream -->
    <div ref="messagesContainer" class="messages-stream">
      <div v-if="!dialogues.length && !agentStore.loadingDialogue" class="empty-stream">
        <Bot :size="32" class="empty-icon" />
        <p>Chưa có thông điệp trong phiên đối thoại.</p>
        <small>Hãy nhập câu lệnh hoặc bấm phím tắt bên dưới để bắt đầu tương tác với Strategy Governor.</small>
      </div>

      <div
        v-for="msg in dialogues"
        :key="msg.id"
        class="message-row"
        :class="msg.sender === 'TRADER' ? 'row-trader' : 'row-governor'"
      >
        <!-- Governor Avatar -->
        <div v-if="msg.sender === 'GOVERNOR'" class="msg-avatar gov-avatar">
          <Bot :size="14" />
        </div>

        <!-- Bubble Container -->
        <div
          class="message-bubble"
          :class="{
            'bubble-trader': msg.sender === 'TRADER',
            'bubble-governor': msg.sender === 'GOVERNOR',
            'bubble-briefing': msg.message_type === 'BRIEFING',
            'bubble-override': msg.message_type === 'OVERRIDE_CONFIRM',
            'bubble-approval': msg.message_type === 'APPROVAL_REQUEST',
          }"
        >
          <!-- Bubble Header -->
          <div class="bubble-meta">
            <span class="sender-name">
              {{ msg.sender === 'TRADER' ? 'CHỦ THỂ (TRADER)' : 'STRATEGY GOVERNOR (CRO)' }}
            </span>
            <span class="msg-time">{{ formatTime(msg.timestamp) }}</span>
          </div>

          <!-- Special: Approval Request Card -->
          <div v-if="msg.message_type === 'APPROVAL_REQUEST'" class="approval-card">
            <div class="approval-title">
              <ShieldAlert :size="16" class="warn-icon" />
              <strong>YÊU CẦU PHÊ DUYỆT LỆNH MỞ (APPROVAL REQUIRED)</strong>
            </div>
            <div class="approval-body">
              {{ msg.content }}
            </div>
            <div class="approval-actions">
              <button
                class="approve-btn"
                :disabled="msg.approval_status !== 'PENDING'"
                @click="handleApproval(msg.id, 'APPROVE')"
              >
                <CheckCircle2 :size="14" />
                <span>{{ msg.approval_status === 'APPROVED' ? 'Đã duyệt' : 'Phê Duyệt (Approve)' }}</span>
              </button>
              <button
                class="reject-btn"
                :disabled="msg.approval_status !== 'PENDING'"
                @click="handleApproval(msg.id, 'REJECT')"
              >
                <AlertCircle :size="14" />
                <span>{{ msg.approval_status === 'REJECTED' ? 'Đã từ chối' : 'Hủy Bỏ (Reject)' }}</span>
              </button>
              <span v-if="msg.approval_status" class="approval-status-tag" :class="'tag-' + msg.approval_status.toLowerCase()">
                {{ msg.approval_status }}
              </span>
            </div>
          </div>

          <!-- Normal / Markdown Content -->
          <div v-else class="bubble-content" style="white-space: pre-wrap;">
            {{ msg.content }}
          </div>

          <!-- Guardrail Breached Warning Badge in bubble footer -->
          <div
            v-if="msg.metadata && msg.metadata.guardrail_passed === false"
            class="guardrail-refusal-badge"
          >
            <ShieldAlert :size="12" />
            <span>Đã ngăn chặn bởi Hard Guardrails (Bảo toàn vốn tuyệt đối)</span>
          </div>
          <div
            v-else-if="msg.metadata && msg.metadata.guardrail_passed === true && msg.message_type === 'OVERRIDE_CONFIRM'"
            class="guardrail-approved-badge"
          >
            <ShieldCheck :size="12" />
            <span>Thẩm định hợp lệ &middot; Đã cập nhật PostgreSQL &amp; Redis Cache</span>
          </div>
        </div>

        <!-- Trader Avatar -->
        <div v-if="msg.sender === 'TRADER'" class="msg-avatar trader-avatar">
          <User :size="14" />
        </div>
      </div>
    </div>

    <!-- Quick Commands Bar -->
    <div class="quick-commands-bar">
      <span class="quick-label"><Terminal :size="12" /> Lệnh nhanh:</span>
      <div class="pills-scroll">
        <button
          v-for="cmd in quickCommands"
          :key="cmd.text"
          class="command-pill"
          :disabled="agentStore.sendingDialogue"
          @click="handleQuickCommand(cmd.text)"
        >
          {{ cmd.label }}
        </button>
      </div>
    </div>

    <!-- Input Bar -->
    <form class="console-input-bar" @submit.prevent="handleSendMessage">
      <input
        v-model="inputMessage"
        type="text"
        placeholder="Nhập chỉ thị cho Governor (VD: 'Hạ rủi ro xuống 0.5%', 'Nới SL lên 2.0x', 'Tạm dừng giao dịch')..."
        :disabled="agentStore.sendingDialogue"
      />
      <button
        type="submit"
        class="send-btn"
        :disabled="!inputMessage.trim() || agentStore.sendingDialogue"
      >
        <Send :size="14" />
        <span>{{ agentStore.sendingDialogue ? 'Đang gửi...' : 'Gửi chỉ thị' }}</span>
      </button>
    </form>
  </div>
</template>

<style scoped>
.governor-dialogue-console {
  display: flex;
  flex-direction: column;
  height: 520px;
  background: #0f131a;
  border: 1px solid #1f2735;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.console-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px 16px;
  background: #141a24;
  border-bottom: 1px solid #1f2735;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-avatar {
  position: relative;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2b3950, #182230);
  border: 1px solid #3d4f6a;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #38bdf8;
}

.online-indicator {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 9px;
  height: 9px;
  background: #10b981;
  border: 2px solid #141a24;
  border-radius: 50%;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-row h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #f1f5f9;
}

.cro-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(56, 189, 248, 0.12);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
  letter-spacing: 0.04em;
}

.console-sub {
  color: #64748b;
  font-size: 11px;
}

.header-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.param-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #192231;
  border: 1px solid #283548;
  color: #cbd5e1;
}

.param-tag.tag-active {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.3);
  color: #10b981;
}

.param-tag.tag-active .dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
}

.param-tag.tag-halt {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.param-tag.tag-halt .dot {
  width: 6px;
  height: 6px;
  background: #ef4444;
  border-radius: 50%;
}

.param-tag.tag-drawdown b {
  color: #f59e0b;
}

.briefing-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  font-size: 11px;
  font-weight: 600;
  background: linear-gradient(135deg, #1e3a5f, #152943);
  color: #38bdf8;
  border: 1px solid #2d5483;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s;
}

.briefing-action-btn:hover:not(:disabled) {
  background: #254974;
  border-color: #38bdf8;
}

.icon-refresh-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #192231;
  border: 1px solid #283548;
  border-radius: 4px;
  color: #94a3b8;
  cursor: pointer;
}

.icon-refresh-btn:hover:not(:disabled) {
  color: #f1f5f9;
  border-color: #475569;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% {
    transform: rotate(360deg);
  }
}

.messages-stream {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #0a0d14;
}

.empty-stream {
  margin: auto;
  text-align: center;
  color: #64748b;
}

.empty-icon {
  margin: 0 auto 10px;
  color: #334155;
}

.message-row {
  display: flex;
  gap: 10px;
  max-width: 88%;
}

.row-trader {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.row-governor {
  align-self: flex-start;
}

.msg-avatar {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 12px;
}

.gov-avatar {
  background: #1e293b;
  border: 1px solid #334155;
  color: #38bdf8;
}

.trader-avatar {
  background: #064e3b;
  border: 1px solid #059669;
  color: #34d399;
}

.message-bubble {
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12.5px;
  line-height: 1.55;
  word-break: break-word;
}

.bubble-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.sender-name {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  opacity: 0.85;
}

.msg-time {
  font-size: 10px;
  color: #64748b;
}

.bubble-trader {
  background: #042f2e;
  border: 1px solid #115e59;
  color: #ccfbf1;
}

.bubble-trader .sender-name {
  color: #2dd4bf;
}

.bubble-governor {
  background: #141c29;
  border: 1px solid #253347;
  color: #e2e8f0;
}

.bubble-governor .sender-name {
  color: #38bdf8;
}

.bubble-briefing {
  background: #0f1f33;
  border: 1px solid #1e3a60;
  box-shadow: inset 0 0 16px rgba(56, 189, 248, 0.05);
}

.bubble-override {
  background: #0f2420;
  border: 1px solid #10b981;
}

.bubble-approval {
  background: #251c0a;
  border: 1px solid #f59e0b;
}

.approval-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.approval-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f59e0b;
  font-size: 12px;
}

.approval-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.approve-btn,
.reject-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.approve-btn {
  background: #059669;
  border: 1px solid #10b981;
  color: white;
}

.approve-btn:hover:not(:disabled) {
  background: #047857;
}

.reject-btn {
  background: #991b1b;
  border: 1px solid #ef4444;
  color: white;
}

.reject-btn:hover:not(:disabled) {
  background: #7f1d1d;
}

.approval-status-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 3px 6px;
  border-radius: 3px;
  margin-left: auto;
}

.approval-status-tag.tag-approved {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.approval-status-tag.tag-rejected {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.guardrail-refusal-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
  font-size: 11px;
  font-weight: 600;
}

.guardrail-approved-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #10b981;
  font-size: 11px;
  font-weight: 600;
}

.quick-commands-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: #111621;
  border-top: 1px solid #1c2432;
  border-bottom: 1px solid #1c2432;
}

.quick-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  white-space: nowrap;
}

.pills-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}

.command-pill {
  font-size: 11px;
  padding: 4px 9px;
  background: #1a2230;
  border: 1px solid #2b394e;
  color: #94a3b8;
  border-radius: 12px;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.15s;
}

.command-pill:hover:not(:disabled) {
  background: #253347;
  color: #f1f5f9;
  border-color: #38bdf8;
}

.console-input-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #141a24;
}

.console-input-bar input {
  flex: 1;
  background: #0b0e14;
  border: 1px solid #253142;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12.5px;
  color: #f1f5f9;
  outline: none;
  transition: border-color 0.2s;
}

.console-input-bar input:focus {
  border-color: #38bdf8;
}

.send-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #0284c7;
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #0369a1;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
