<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Bot,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clock,
  ExternalLink,
  Maximize2,
  MessageSquare,
  Minus,
  RefreshCw,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  User,
  X,
  Zap,
} from 'lucide-vue-next'
import { chatStore } from '../../stores/chatStore'
import { agentStore } from '../../stores/agentStore'
import { eventBus } from '../../services/eventBus'

const emit = defineEmits(['open-studio'])

const quickInputText = ref('')
const miniMessagesContainer = ref(null)

const quickCommands = [
  { label: '🏛️ Báo cáo điều hành', text: 'Xuất bản bản tin điều hành mới nhất' },
  { label: '📉 Hạ rủi ro 0.5%', text: 'Hạ mức rủi ro xuống 0.5% vốn và nâng SL lên 2.0x ATR' },
  { label: '⏸️ Tạm dừng giao dịch', text: 'Tạm dừng giao dịch để theo dõi tin tức' },
  { label: '▶️ Tiếp tục giao dịch', text: 'Tiếp tục giao dịch' },
]

const governorParams = computed(() => agentStore.runtimeParams || {
  trading_allowed: true,
  risk_per_trade_percent: 1.0,
})

const activeMessages = computed(() => chatStore.activeMessages)

watch(
  () => activeMessages.value.length,
  () => {
    if (chatStore.isWidgetOpen) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  }
)

let unbindScroll = null

onMounted(() => {
  unbindScroll = eventBus.on('chat:scroll-bottom', () => {
    if (chatStore.isWidgetOpen) {
      nextTick(scrollToBottom)
    }
  })
})

onUnmounted(() => {
  if (unbindScroll) unbindScroll()
})

watch(
  () => chatStore.isWidgetOpen,
  (isOpen) => {
    if (isOpen) {
      chatStore.unreadCount = 0
      chatStore.dismissToast()
      nextTick(() => {
        scrollToBottom()
      })
    }
  }
)

function scrollToBottom() {
  if (miniMessagesContainer.value) {
    miniMessagesContainer.value.scrollTop = miniMessagesContainer.value.scrollHeight
  }
}

async function handleSendQuickMessage() {
  const text = quickInputText.value.trim()
  if (!text || chatStore.sendingMessage) return
  quickInputText.value = ''
  try {
    await chatStore.sendMessage(text, {
      attachMarketContext: false,
    })
  } catch (err) {
    console.error('Lỗi gửi tin nhắn pop-up:', err)
  }
}

function handleQuickKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendQuickMessage()
  }
}

function applyQuickCommand(cmd) {
  quickInputText.value = cmd.text
  handleSendQuickMessage()
}

async function handleApproval(dialogueId, action) {
  try {
    await chatStore.respondApproval(dialogueId, action)
  } catch (err) {
    console.error('Lỗi approval pop-up:', err)
  }
}

function handleOpenFullStudio() {
  chatStore.closeWidget()
  emit('open-studio')
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function renderSimpleMarkdown(content) {
  if (!content) return ''
  return content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="mini-inline-code">$1</code>')
    .replace(/\n\n/g, '<div class="mini-gap"></div>')
    .replace(/\n/g, '<br/>')
}

function handleQuickCommandsWheel(e) {
  if (e.deltaY !== 0) {
    e.currentTarget.scrollLeft += e.deltaY
  }
}
</script>

<template>
  <div class="global-chat-widget-root">
    <!-- ============================================== -->
    <!-- 1. TOAST NOTIFICATION PREVIEW (KHI WIDGET ĐÓNG) -->
    <!-- ============================================== -->
    <transition name="toast-slide">
      <div
        v-if="!chatStore.isWidgetOpen && chatStore.latestToast"
        class="floating-toast-card"
        :class="{ 'toast-approval': chatStore.latestToast.isApproval }"
        @click="chatStore.openWidget(chatStore.latestToast.conversationId)"
      >
        <div class="toast-indicator"></div>
        <div class="toast-body">
          <div class="toast-header-row">
            <span class="toast-title">{{ chatStore.latestToast.title }}</span>
            <button class="toast-close-btn" @click.stop="chatStore.dismissToast">
              <X :size="12" />
            </button>
          </div>
          <p class="toast-snippet">{{ chatStore.latestToast.content }}</p>
          <div class="toast-hint-row">
            <span>Bấm để mở cuộc trò chuyện &rarr;</span>
          </div>
        </div>
      </div>
    </transition>

    <!-- ============================================== -->
    <!-- 2. MINI-POPUP CHAT CONSOLE (KHI WIDGET MỞ)     -->
    <!-- ============================================== -->
    <transition name="popup-scale">
      <div
        v-if="chatStore.isWidgetOpen"
        class="mini-popup-console"
      >
        <!-- Header -->
        <header class="mini-console-header">
          <div class="header-main-info">
            <div class="mini-avatar">
              <Shield :size="16" class="icon-shield" />
              <span class="mini-online-dot"></span>
            </div>
            <div class="mini-titles">
              <div class="title-flex">
                <h4 class="session-heading" :title="chatStore.activeConversation?.title || 'AI Chat Console'">
                  {{ chatStore.activeConversation?.title || 'Strategy Governor' }}
                </h4>
              </div>
              <div class="status-strip">
                <span
                  class="param-badge"
                  :class="governorParams.trading_allowed ? 'status-active' : 'status-halt'"
                >
                  {{ governorParams.trading_allowed ? 'ACTIVE' : 'HALTED' }}
                </span>
                <span class="param-badge neutral">
                  RỦI RO: {{ governorParams.risk_per_trade_percent }}%
                </span>
              </div>
            </div>
          </div>

          <div class="header-controls">
            <!-- Nút Mở Toàn Màn Hình Trong Strategy Studio -->
            <button
              class="control-btn"
              title="Mở Toàn Màn Hình Trong Dedicated Strategy Studio"
              @click="handleOpenFullStudio"
            >
              <Maximize2 :size="13" />
            </button>

            <!-- Nút Thu Nhỏ / Đóng -->
            <button
              class="control-btn"
              title="Thu nhỏ cửa sổ"
              @click="chatStore.closeWidget"
            >
              <Minus :size="14" />
            </button>
          </div>
        </header>

        <!-- Message Stream Body -->
        <div ref="miniMessagesContainer" class="mini-messages-body">
          <div v-if="!activeMessages.length && !chatStore.loadingMessages" class="mini-empty-state">
            <Bot :size="28" class="mini-empty-icon" />
            <p>Sẵn sàng tương tác với Strategy Governor &amp; AI Agents.</p>
            <small>Gửi lệnh ghi đè hoặc bấm phím tắt bên dưới để bắt đầu.</small>
          </div>

          <div v-else class="mini-messages-list">
            <div
              v-for="msg in activeMessages"
              :key="msg.id"
              class="mini-msg-row"
              :class="msg.sender === 'TRADER' ? 'row-trader' : 'row-agent'"
            >
              <!-- Avatar -->
              <div class="mini-msg-avatar">
                <User v-if="msg.sender === 'TRADER'" :size="11" />
                <Bot v-else :size="11" />
              </div>

              <!-- Message Bubble -->
              <div class="mini-msg-bubble">
                <div class="mini-bubble-meta">
                  <span class="meta-sender">
                    {{ msg.sender === 'TRADER' ? 'Trader' : (msg.sender || 'Governor') }}
                  </span>
                  <span class="meta-time">{{ formatTime(msg.timestamp) }}</span>
                </div>

                <!-- Thẻ Phê Duyệt Lệnh Mở (Interactive Approval Card) -->
                <div v-if="msg.message_type === 'APPROVAL_REQUEST'" class="mini-approval-card">
                  <div class="mini-card-head">
                    <ShieldAlert :size="14" class="icon-warn" />
                    <strong>YÊU CẦU PHÊ DUYỆT LỆNH</strong>
                  </div>
                  <div class="mini-card-content" v-html="renderSimpleMarkdown(msg.content)"></div>
                  <div class="mini-card-actions">
                    <button
                      class="mini-approve-btn"
                      :disabled="msg.approval_status !== 'PENDING' || chatStore.respondingApproval"
                      @click="handleApproval(msg.id, 'APPROVE')"
                    >
                      <CheckCircle2 :size="12" />
                      <span>{{ msg.approval_status === 'APPROVED' ? 'Đã duyệt' : 'Phê Duyệt' }}</span>
                    </button>
                    <button
                      class="mini-reject-btn"
                      :disabled="msg.approval_status !== 'PENDING' || chatStore.respondingApproval"
                      @click="handleApproval(msg.id, 'REJECT')"
                    >
                      <AlertCircle :size="12" />
                      <span>{{ msg.approval_status === 'REJECTED' ? 'Đã từ chối' : 'Từ Chối' }}</span>
                    </button>
                    <span v-if="msg.approval_status" class="mini-status-tag" :class="'tag-' + msg.approval_status.toLowerCase()">
                      {{ msg.approval_status }}
                    </span>
                  </div>
                </div>

                <!-- Nội dung thông thường -->
                <div
                  v-else
                  class="mini-bubble-text"
                  v-html="renderSimpleMarkdown(msg.content)"
                ></div>
              </div>
            </div>

            <!-- Thinking Indicator -->
            <div v-if="chatStore.sendingMessage" class="mini-thinking-row">
              <Bot :size="12" class="spinning" />
              <span>Agent đang thẩm định...</span>
            </div>
          </div>
        </div>

        <!-- Quick Commands Strip -->
        <div class="mini-quick-commands" @wheel.passive="handleQuickCommandsWheel">
          <button
            v-for="(cmd, i) in quickCommands"
            :key="i"
            class="mini-cmd-chip"
            @click="applyQuickCommand(cmd)"
          >
            {{ cmd.label }}
          </button>
        </div>

        <!-- Input Footer -->
        <footer class="mini-console-footer">
          <div class="mini-input-wrap">
            <input
              v-model="quickInputText"
              type="text"
              placeholder="Nhập chỉ thị điều hành hoặc câu hỏi... (Enter để gửi)"
              class="mini-text-input"
              @keydown="handleQuickKeyDown"
            />
            <button
              class="mini-send-btn"
              :disabled="!quickInputText.trim() || chatStore.sendingMessage"
              @click="handleSendQuickMessage"
            >
              <Send :size="13" />
            </button>
          </div>

          <!-- Nút Switch Sang Full Studio -->
          <button class="switch-full-studio-btn" @click="handleOpenFullStudio">
            <span>Mở Toàn Màn Hình Trong Strategy Studio</span>
            <ArrowRight :size="12" />
          </button>
        </footer>
      </div>
    </transition>

    <!-- ============================================== -->
    <!-- 3. COLLAPSED FLOATING ACTION PILL (FAB)        -->
    <!-- ============================================== -->
    <button
      class="global-chat-fab"
      :class="{ 'fab-open': chatStore.isWidgetOpen, 'has-unread': chatStore.unreadCount > 0 }"
      title="Mở Trợ lý Trò chuyện & Điều hành AI Real-time"
      @click="chatStore.toggleWidget"
    >
      <div class="fab-glow-ring"></div>
      <div class="fab-inner">
        <div class="fab-icon-wrap">
          <Sparkles v-if="chatStore.unreadCount > 0" :size="16" class="icon-sparkle" />
          <BrainCircuit v-else :size="18" class="icon-brain" />
        </div>
        <span class="fab-label">AI Studio</span>

        <!-- Unread Badge -->
        <span v-if="chatStore.unreadCount > 0" class="fab-unread-badge">
          {{ chatStore.unreadCount > 9 ? '9+' : chatStore.unreadCount }}
        </span>
      </div>
    </button>
  </div>
</template>

<style scoped>
.global-chat-widget-root {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  font-family: inherit;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

/* ==================================================== */
/* 1. TOAST NOTIFICATION PREVIEW                        */
/* ==================================================== */
.floating-toast-card {
  width: 320px;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(56, 139, 253, 0.4);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5), 0 0 16px rgba(56, 139, 253, 0.2);
  cursor: pointer;
  display: flex;
  gap: 10px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.floating-toast-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 139, 253, 0.35);
}

.toast-approval {
  border-color: #d29922;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5), 0 0 16px rgba(210, 153, 34, 0.3);
}

.toast-indicator {
  width: 4px;
  border-radius: 2px;
  background: #388bfd;
  flex-shrink: 0;
}

.toast-approval .toast-indicator {
  background: #d29922;
}

.toast-body {
  flex: 1;
  min-width: 0;
}

.toast-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.toast-title {
  font-size: 11px;
  font-weight: 700;
  color: #58a6ff;
  letter-spacing: 0.3px;
}

.toast-approval .toast-title {
  color: #f1e05a;
}

.toast-close-btn {
  background: none;
  border: none;
  color: #8b949e;
  cursor: pointer;
  padding: 2px;
}

.toast-snippet {
  margin: 0 0 6px;
  font-size: 11px;
  color: #e6edf3;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toast-hint-row {
  font-size: 10px;
  color: #8b949e;
  font-weight: 500;
}

/* ==================================================== */
/* 2. MINI-POPUP CHAT CONSOLE                           */
/* ==================================================== */
.mini-popup-console {
  width: 400px;
  height: 550px;
  max-height: calc(100vh - 100px);
  background: rgba(13, 17, 26, 0.96);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  margin-bottom: 14px;
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.65), 0 0 24px rgba(56, 139, 253, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.mini-console-header {
  padding: 12px 16px;
  background: #0f1523;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-main-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.mini-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(56, 139, 253, 0.2) 0%, rgba(31, 111, 235, 0.3) 100%);
  border: 1px solid rgba(56, 139, 253, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #58a6ff;
  position: relative;
  flex-shrink: 0;
}

.mini-online-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3fb950;
  border: 1px solid #0f1523;
}

.mini-titles {
  min-width: 0;
}

.session-heading {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #e6edf3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.status-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.param-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  letter-spacing: 0.3px;
}

.param-badge.status-active {
  background: rgba(46, 160, 67, 0.2);
  color: #3fb950;
}

.param-badge.status-halt {
  background: rgba(248, 81, 73, 0.2);
  color: #f85149;
}

.param-badge.neutral {
  background: rgba(255, 255, 255, 0.08);
  color: #8b949e;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #8b949e;
  border-radius: 6px;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

/* Messages Body */
.mini-messages-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.18) transparent;
}

.mini-messages-body::-webkit-scrollbar {
  width: 5px;
}

.mini-messages-body::-webkit-scrollbar-track {
  background: transparent;
}

.mini-messages-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.16);
  border-radius: 999px;
}

.mini-messages-body::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.32);
}

.mini-messages-body::-webkit-scrollbar-button {
  display: none !important;
}

.mini-empty-state {
  text-align: center;
  padding: 40px 16px;
  color: #8b949e;
}

.mini-empty-icon {
  color: #484f58;
  margin-bottom: 10px;
}

.mini-empty-state p {
  font-size: 12px;
  margin: 0 0 4px;
  color: #c9d1d9;
}

.mini-empty-state small {
  font-size: 10px;
}

.mini-messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mini-msg-row {
  display: flex;
  gap: 8px;
}

.row-trader {
  flex-direction: row-reverse;
}

.mini-msg-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  flex-shrink: 0;
  margin-top: 2px;
}

.row-trader .mini-msg-avatar {
  background: #1f6feb;
  color: #fff;
}

.row-agent .mini-msg-avatar {
  background: #21262d;
  color: #58a6ff;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.mini-msg-bubble {
  max-width: 84%;
  display: flex;
  flex-direction: column;
}

.mini-bubble-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: #6e7681;
  margin-bottom: 2px;
}

.row-trader .mini-bubble-meta {
  justify-content: flex-end;
}

.meta-sender {
  font-weight: 600;
  color: #8b949e;
}

.mini-bubble-text {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 11.5px;
  line-height: 1.5;
  color: #e6edf3;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.row-trader .mini-bubble-text {
  background: #193256;
  border: 1px solid rgba(56, 139, 253, 0.3);
  border-top-right-radius: 2px;
}

.row-agent .mini-bubble-text {
  background: #161b24;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-top-left-radius: 2px;
}

/* Mini Approval Card */
.mini-approval-card {
  background: #181d2a;
  border: 1px solid #d29922;
  border-radius: 8px;
  padding: 10px 12px;
}

.mini-card-head {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f1e05a;
  font-size: 11px;
  margin-bottom: 6px;
}

.mini-card-content {
  font-size: 11px;
  line-height: 1.45;
  color: #c9d1d9;
  background: rgba(0, 0, 0, 0.25);
  padding: 8px;
  border-radius: 4px;
  margin-bottom: 10px;
}

.mini-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-approve-btn,
.mini-reject-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.mini-approve-btn {
  background: #238636;
  border: 1px solid #2ea043;
  color: #fff;
}

.mini-reject-btn {
  background: #da3633;
  border: 1px solid #f85149;
  color: #fff;
}

.mini-approve-btn:disabled,
.mini-reject-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mini-status-tag {
  margin-left: auto;
  font-size: 9px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  text-transform: uppercase;
}

.tag-approved { background: rgba(46, 160, 67, 0.2); color: #3fb950; }
.tag-rejected { background: rgba(248, 81, 73, 0.2); color: #f85149; }
.tag-pending { background: rgba(210, 153, 34, 0.2); color: #d29922; }

/* Thinking Row */
.mini-thinking-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
  color: #8b949e;
  font-style: italic;
  padding: 4px 8px;
}

/* Quick Commands */
.mini-quick-commands {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 8px 14px;
  background: #0b0f19;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  scrollbar-width: none !important;
  -ms-overflow-style: none !important;
}

.mini-quick-commands::-webkit-scrollbar {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
}

.mini-cmd-chip {
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  color: #c9d1d9;
  font-size: 10px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.mini-cmd-chip:hover {
  background: rgba(56, 139, 253, 0.12);
  border-color: rgba(56, 139, 253, 0.3);
  color: #58a6ff;
}

/* Footer */
.mini-console-footer {
  padding: 10px 14px 12px;
  background: #0f1523;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mini-input-wrap {
  display: flex;
  align-items: center;
  background: #161b24;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 4px 6px 4px 10px;
  transition: border-color 0.2s;
}

.mini-input-wrap:focus-within {
  border-color: #58a6ff;
}

.mini-text-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e6edf3;
  font-size: 11.5px;
}

.mini-send-btn {
  background: #1f6feb;
  border: none;
  color: #fff;
  border-radius: 6px;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: opacity 0.2s;
}

.mini-send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.switch-full-studio-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 6px;
  background: transparent;
  border: 1px dashed rgba(56, 139, 253, 0.3);
  border-radius: 6px;
  color: #58a6ff;
  font-size: 10.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.switch-full-studio-btn:hover {
  background: rgba(56, 139, 253, 0.1);
  border-color: #58a6ff;
}

/* ==================================================== */
/* 3. COLLAPSED FLOATING ACTION PILL (FAB)              */
/* ==================================================== */
.global-chat-fab {
  position: relative;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.98) 100%);
  border: 1px solid rgba(56, 139, 253, 0.45);
  border-radius: 28px;
  padding: 9px 18px 9px 14px;
  color: #e6edf3;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45), 0 0 16px rgba(56, 139, 253, 0.25);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.global-chat-fab:hover {
  transform: translateY(-2px);
  border-color: rgba(56, 139, 253, 0.7);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.55), 0 0 24px rgba(56, 139, 253, 0.4);
}

.fab-open {
  background: rgba(30, 41, 59, 0.98);
  border-color: #388bfd;
}

.fab-glow-ring {
  position: absolute;
  inset: -2px;
  border-radius: 30px;
  background: radial-gradient(circle, rgba(56, 139, 253, 0.4) 0%, transparent 70%);
  opacity: 0.5;
  pointer-events: none;
  animation: glowPulse 2.5s infinite ease-in-out;
}

@keyframes glowPulse {
  0%, 100% { opacity: 0.2; transform: scale(0.98); }
  50% { opacity: 0.6; transform: scale(1.02); }
}

.fab-inner {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 1;
}

.fab-icon-wrap {
  color: #58a6ff;
  display: flex;
  align-items: center;
}

.icon-sparkle {
  color: #f1e05a;
  animation: spinSlow 4s linear infinite;
}

@keyframes spinSlow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.fab-label {
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: #e6edf3;
}

.fab-unread-badge {
  background: #f85149;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  border-radius: 10px;
  padding: 1px 6px;
  min-width: 18px;
  text-align: center;
  box-shadow: 0 0 8px rgba(248, 81, 73, 0.6);
  animation: badgeBounce 0.8s ease-in-out;
}

@keyframes badgeBounce {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.2); }
}

/* Transitions */
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-slide-enter-from,
.toast-slide-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.95);
}

.popup-scale-enter-active,
.popup-scale-leave-active {
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.popup-scale-enter-from,
.popup-scale-leave-to {
  opacity: 0;
  transform: translateY(16px) scale(0.96);
}

/* Utility Markdown Classes */
:deep(.mini-inline-code) {
  background: rgba(255, 255, 255, 0.08);
  color: #f0883e;
  padding: 1px 4px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 10.5px;
}
:deep(.mini-gap) { height: 6px; }
:deep(strong) { color: #fff; font-weight: 600; }
</style>
