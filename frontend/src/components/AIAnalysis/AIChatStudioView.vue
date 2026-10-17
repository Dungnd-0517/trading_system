<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Archive,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Bot,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock,
  Compass,
  Copy,
  CornerDownLeft,
  Database,
  Download,
  Edit2,
  FileDown,
  FileText,
  Filter,
  Layers,
  Lightbulb,
  Maximize2,
  MessageSquare,
  MoreVertical,
  Newspaper,
  Pin,
  PinOff,
  Plus,
  RefreshCw,
  Search,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  Target,
  Terminal,
  Trash2,
  User,
  X,
  Zap,
} from 'lucide-vue-next'
import { chatStore } from '../../stores/chatStore'
import { agentStore } from '../../stores/agentStore'
import { marketStore } from '../../stores/marketStore'
import { eventBus } from '../../services/eventBus'

const emit = defineEmits(['navigate-cockpit', 'navigate-tab'])

// Quản lý trạng thái nhập liệu & giao diện
const messageInput = ref('')
const attachContext = ref(false)
const messagesContainer = ref(null)
const editingTitleId = ref(null)
const editingTitleText = ref('')
const activeDropdownId = ref(null)
const textareaRef = ref(null)
const copiedMsgId = ref(null)

// Danh sách Persona tham vấn
const personaIcons = {
  GOVERNOR: '👑',
  TECHNICAL: '📐',
  NEWS: '📰',
  REFLEXION: '🧠',
  COUNCIL: '🏛',
}

const personaColors = {
  GOVERNOR: 'badge-gold',
  TECHNICAL: 'badge-blue',
  NEWS: 'badge-purple',
  REFLEXION: 'badge-green',
  COUNCIL: 'badge-amber',
}

// Quick Prompts phong phú
const quickPrompts = [
  {
    icon: '👑',
    title: 'Bản tin điều hành (Arbiter)',
    desc: 'Yêu cầu Arbiter xuất bản Executive Briefing CRO',
    text: 'Xuất bản bản tin điều hành mới nhất từ Chief Risk Officer (Arbiter)',
    persona: 'GOVERNOR',
  },
  {
    icon: '📉',
    title: 'Hạ rủi ro 0.5% (Arbiter)',
    desc: 'Điều chỉnh tham số bảo toàn vốn theo quy tắc D21',
    text: 'Hạ mức rủi ro xuống 0.5% vốn và nâng SL lên 2.0x ATR',
    persona: 'GOVERNOR',
  },
  {
    icon: '📐',
    title: 'Phân tích Wyckoff & SMC (Vector)',
    desc: 'Hợp lưu Spring M15, Liquidity Sweep & Discount POI',
    text: 'Đánh giá cấu trúc M15 hiện tại theo trường phái Wyckoff và SMC Order Block',
    persona: 'TECHNICAL',
  },
  {
    icon: '📰',
    title: 'Bối cảnh Vĩ mô & DXY (Sentinel)',
    desc: 'Đo lường điểm cảm xúc và trạng thái Circuit Breaker',
    text: 'Tóm tắt tình hình tin tức vĩ mô hôm nay, tương quan DXY và trạng thái Circuit Breaker',
    persona: 'NEWS',
  },
  {
    icon: '🧠',
    title: 'Kinh nghiệm & Sai lầm (Scribe)',
    desc: 'Hồi tưởng bài học Post-Mortem và Taxonomy lỗi',
    text: 'Tổng kết tỷ lệ thắng và phân loại các sai lầm lặp lại gần nhất',
    persona: 'REFLEXION',
  },
  {
    icon: '🏛',
    title: 'Hội đồng Đồng thuận (Council)',
    desc: 'Nghị quyết đa agent tổng hợp ý kiến Vector, Sentinel & Scribe',
    text: 'Hội đồng đa agent hãy họp thảo luận và ban hành nghị quyết đồng thuận chiến lược',
    persona: 'COUNCIL',
  },
]

// Phân nhóm thời gian cuộc trò chuyện (Time-Grouping Gemini Style)
const groupedConversations = computed(() => {
  const groups = {
    pinned: [],
    today: [],
    week: [],
    month: [],
    older: [],
  }

  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const sevenDaysAgo = startOfToday - 7 * 86400000
  const thirtyDaysAgo = startOfToday - 30 * 86400000

  for (const conv of chatStore.filteredConversations) {
    if (conv.is_pinned && !chatStore.showArchived) {
      groups.pinned.push(conv)
      continue
    }

    const updated = new Date(conv.updated_at || conv.created_at || now).getTime()
    if (updated >= startOfToday) {
      groups.today.push(conv)
    } else if (updated >= sevenDaysAgo) {
      groups.week.push(conv)
    } else if (updated >= thirtyDaysAgo) {
      groups.month.push(conv)
    } else {
      groups.older.push(conv)
    }
  }

  return groups
})

let unbindScroll = null

onMounted(async () => {
  chatStore.isStudioActive = true
  chatStore.unreadCount = 0
  chatStore.dismissToast()
  if (!chatStore.conversations.length) {
    await chatStore.init()
  }
  scrollToBottom()
  unbindScroll = eventBus.on('chat:scroll-bottom', () => {
    nextTick(scrollToBottom)
  })
  // Tự động đóng dropdown khi click ra ngoài
  window.addEventListener('click', closeAllDropdowns)
})

onUnmounted(() => {
  chatStore.isStudioActive = false
  if (unbindScroll) unbindScroll()
  window.removeEventListener('click', closeAllDropdowns)
})

watch(
  () => chatStore.activeMessages,
  () => {
    nextTick(() => {
      scrollToBottom()
    })
  },
  { deep: true }
)

function closeAllDropdowns() {
  activeDropdownId.value = null
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function autoResizeTextarea() {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
    const newHeight = Math.min(textareaRef.value.scrollHeight, 180)
    textareaRef.value.style.height = newHeight + 'px'
  }
}

async function handleSendMessage() {
  const text = messageInput.value.trim()
  if (!text || chatStore.sendingMessage) return

  messageInput.value = ''
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }

  try {
    await chatStore.sendMessage(text, {
      attachMarketContext: attachContext.value,
    })
  } catch (err) {
    console.error('Lỗi gửi tin nhắn:', err)
  }
}

function handleKeyDown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSendMessage()
  }
}

function applyQuickPrompt(prompt) {
  if (prompt.persona) {
    chatStore.setPersonaForActive(prompt.persona)
  }
  messageInput.value = prompt.text
  handleSendMessage()
}

async function handleCreateNewChat() {
  try {
    await chatStore.createNewConversation('Cuộc trò chuyện mới', chatStore.currentPersona)
    nextTick(() => {
      textareaRef.value?.focus()
    })
  } catch (err) {
    console.error('Lỗi tạo cuộc trò chuyện:', err)
  }
}

function startRename(conv, event) {
  event?.stopPropagation()
  editingTitleId.value = conv.id
  editingTitleText.value = conv.title
  activeDropdownId.value = null
  nextTick(() => {
    const el = document.getElementById(`rename-input-${conv.id}`)
    el?.focus()
    el?.select()
  })
}

async function saveRename(convId) {
  if (!editingTitleId.value) return
  const newTitle = editingTitleText.value.trim()
  editingTitleId.value = null
  if (newTitle) {
    await chatStore.updateConversationTitle(convId, newTitle)
  }
}

function cancelRename() {
  editingTitleId.value = null
}

function toggleDropdown(convId, event) {
  event?.stopPropagation()
  if (activeDropdownId.value === convId) {
    activeDropdownId.value = null
  } else {
    activeDropdownId.value = convId
  }
}

async function handleDeleteConversation(convId, event) {
  event?.stopPropagation()
  activeDropdownId.value = null
  if (confirm('Bạn có chắc chắn muốn xóa cuộc trò chuyện này và toàn bộ tin nhắn liên quan?')) {
    await chatStore.deleteConversation(convId)
  }
}

async function handleApproval(dialogueId, action) {
  try {
    await chatStore.respondApproval(dialogueId, action)
  } catch (err) {
    console.error('Lỗi approval:', err)
  }
}

function copyMessageContent(msg) {
  if (!msg?.content) return
  navigator.clipboard.writeText(msg.content)
  copiedMsgId.value = msg.id
  setTimeout(() => {
    if (copiedMsgId.value === msg.id) {
      copiedMsgId.value = null
    }
  }, 2000)
}

function formatRelativeTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    const now = new Date()
    const diffSec = Math.floor((now - d) / 1000)
    if (diffSec < 60) return 'Vừa xong'
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} phút trước`
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} giờ trước`
    return d.toLocaleDateString('vi-VN', { month: 'numeric', day: 'numeric' })
  } catch {
    return ''
  }
}

function formatDetailTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoStr
  }
}

// Bộ phân giải Markdown gọn gàng & an toàn
function renderMarkdown(content) {
  if (!content) return ''
  let html = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Code blocks: ```lang ... ```
  html = html.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<div class="md-code-block"><div class="md-code-header">${lang || 'MÃ LỆNH'}</div><pre><code>${code.trim()}</code></pre></div>`
  })

  // Inline code: `code`
  html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>')

  // Headers: ### Header
  html = html.replace(/^### (.*$)/gim, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.*$)/gim, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.*$)/gim, '<h2 class="md-h2">$1</h2>')

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

  // Bullet lists
  html = html.replace(/^\s*•\s+(.*$)/gim, '<li class="md-li">$1</li>')
  html = html.replace(/^\s*-\s+(.*$)/gim, '<li class="md-li">$1</li>')
  html = html.replace(/(<li.*<\/li>)/s, '<ul class="md-ul">$1</ul>')

  // Blockquotes: > Quote
  html = html.replace(/^>\s+(.*$)/gim, '<blockquote class="md-quote">$1</blockquote>')

  // Line breaks
  html = html.replace(/\n\n/g, '<div class="md-gap"></div>')
  html = html.replace(/\n/g, '<br/>')

  return html
}
</script>

<template>
  <div class="chat-studio-container">
    <!-- ============================================== -->
    <!-- CỘT TRÁI: SIDEBAR QUẢN LÝ ĐA HỘI THOẠI (GEMINI) -->
    <!-- ============================================== -->
    <aside class="chat-sidebar">
      <!-- Top Action: Nút Tạo New Chat -->
      <div class="sidebar-top">
        <button class="new-chat-btn" @click="handleCreateNewChat">
          <div class="btn-inner">
            <Plus :size="16" class="icon-plus" />
            <span class="btn-label">Cuộc trò chuyện mới</span>
          </div>
          <span class="gemini-pill">Gemini</span>
        </button>

        <!-- Search Bar -->
        <div class="search-box">
          <Search :size="13" class="search-icon" />
          <input
            v-model="chatStore.searchQuery"
            type="text"
            placeholder="Tìm kiếm cuộc trò chuyện..."
            class="search-input"
          />
          <button
            v-if="chatStore.searchQuery"
            class="clear-search-btn"
            @click="chatStore.searchQuery = ''"
          >
            <X :size="12" />
          </button>
        </div>

        <!-- Filter Archived Toggle -->
        <div class="archive-toggle-row">
          <button
            class="filter-pill"
            :class="{ active: !chatStore.showArchived }"
            @click="chatStore.showArchived = false"
          >
            Đang hoạt động ({{ chatStore.conversations.filter(c => !c.is_archived).length }})
          </button>
          <button
            class="filter-pill"
            :class="{ active: chatStore.showArchived }"
            @click="chatStore.showArchived = true"
          >
            <Archive :size="11" />
            <span>Lưu trữ ({{ chatStore.conversations.filter(c => c.is_archived).length }})</span>
          </button>
        </div>
      </div>

      <!-- Danh Sách Cuộc Trò Chuyện (Phân Nhóm Thời Gian) -->
      <div class="conversations-scrollable">
        <div v-if="chatStore.loadingConversations && !chatStore.conversations.length" class="sidebar-loading">
          <RefreshCw :size="16" class="spinning" />
          <span>Đang tải các phiên hội thoại...</span>
        </div>

        <div v-else-if="!chatStore.filteredConversations.length" class="sidebar-empty">
          <MessageSquare :size="24" class="empty-icon" />
          <p>{{ chatStore.showArchived ? 'Không có cuộc trò chuyện lưu trữ' : 'Chưa có cuộc trò chuyện nào' }}</p>
          <small>Bấm "Cuộc trò chuyện mới" để bắt đầu thảo luận với AI Agents.</small>
        </div>

        <div v-else class="groups-wrapper">
          <!-- NHÓM: ĐÃ GHIM (PINNED) -->
          <div v-if="groupedConversations.pinned.length" class="conv-group">
            <div class="group-header">
              <Pin :size="11" class="pin-icon" />
              <span>ĐÃ GHIM (PINNED)</span>
            </div>
            <div
              v-for="conv in groupedConversations.pinned"
              :key="conv.id"
              class="conv-item"
              :class="{ active: chatStore.activeConversationId === conv.id }"
              @click="chatStore.selectConversation(conv.id)"
            >
              <div class="conv-persona-icon">{{ personaIcons[conv.agent_target] || '🤖' }}</div>
              <div class="conv-info">
                <div v-if="editingTitleId === conv.id" class="inline-rename-box" @click.stop>
                  <input
                    :id="`rename-input-${conv.id}`"
                    v-model="editingTitleText"
                    type="text"
                    class="rename-input"
                    @keydown.enter="saveRename(conv.id)"
                    @keydown.esc="cancelRename"
                  />
                  <button class="save-rename-btn" @click="saveRename(conv.id)"><Check :size="12" /></button>
                </div>
                <div v-else class="conv-title-row">
                  <span class="conv-title" :title="conv.title">{{ conv.title }}</span>
                </div>
                <div class="conv-meta">
                  <span class="time-label">{{ formatRelativeTime(conv.updated_at) }}</span>
                  <span v-if="conv.message_count" class="count-badge">{{ conv.message_count }} tin</span>
                </div>
              </div>

              <!-- Nút Thao Tác Menu 3 Chấm -->
              <div class="conv-actions" @click.stop>
                <button class="dots-btn" @click="toggleDropdown(conv.id, $event)">
                  <MoreVertical :size="13" />
                </button>
                <div v-if="activeDropdownId === conv.id" class="dropdown-menu">
                  <button class="dropdown-item" @click="chatStore.togglePin(conv.id)">
                    <PinOff :size="12" /> Bỏ ghim
                  </button>
                  <button class="dropdown-item" @click="startRename(conv, $event)">
                    <Edit2 :size="12" /> Đổi tên
                  </button>
                  <button class="dropdown-item" @click="chatStore.exportConversation(conv.id)">
                    <FileDown :size="12" /> Tải Markdown
                  </button>
                  <button class="dropdown-item" @click="chatStore.toggleArchive(conv.id)">
                    <Archive :size="12" /> {{ conv.is_archived ? 'Bỏ lưu trữ' : 'Lưu trữ' }}
                  </button>
                  <div class="dropdown-divider"></div>
                  <button class="dropdown-item danger" @click="handleDeleteConversation(conv.id, $event)">
                    <Trash2 :size="12" /> Xóa cuộc trò chuyện
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- NHÓM: HÔM NAY (TODAY) -->
          <div v-if="groupedConversations.today.length" class="conv-group">
            <div class="group-header"><span>HÔM NAY (TODAY)</span></div>
            <div
              v-for="conv in groupedConversations.today"
              :key="conv.id"
              class="conv-item"
              :class="{ active: chatStore.activeConversationId === conv.id }"
              @click="chatStore.selectConversation(conv.id)"
            >
              <div class="conv-persona-icon">{{ personaIcons[conv.agent_target] || '🤖' }}</div>
              <div class="conv-info">
                <div v-if="editingTitleId === conv.id" class="inline-rename-box" @click.stop>
                  <input
                    :id="`rename-input-${conv.id}`"
                    v-model="editingTitleText"
                    type="text"
                    class="rename-input"
                    @keydown.enter="saveRename(conv.id)"
                    @keydown.esc="cancelRename"
                  />
                  <button class="save-rename-btn" @click="saveRename(conv.id)"><Check :size="12" /></button>
                </div>
                <div v-else class="conv-title-row">
                  <span class="conv-title" :title="conv.title">{{ conv.title }}</span>
                </div>
                <div class="conv-meta">
                  <span class="time-label">{{ formatRelativeTime(conv.updated_at) }}</span>
                  <span v-if="conv.message_count" class="count-badge">{{ conv.message_count }} tin</span>
                </div>
              </div>

              <div class="conv-actions" @click.stop>
                <button class="dots-btn" @click="toggleDropdown(conv.id, $event)">
                  <MoreVertical :size="13" />
                </button>
                <div v-if="activeDropdownId === conv.id" class="dropdown-menu">
                  <button class="dropdown-item" @click="chatStore.togglePin(conv.id)">
                    <Pin :size="12" /> Ghim lên đầu
                  </button>
                  <button class="dropdown-item" @click="startRename(conv, $event)">
                    <Edit2 :size="12" /> Đổi tên
                  </button>
                  <button class="dropdown-item" @click="chatStore.exportConversation(conv.id)">
                    <FileDown :size="12" /> Tải Markdown
                  </button>
                  <button class="dropdown-item" @click="chatStore.toggleArchive(conv.id)">
                    <Archive :size="12" /> {{ conv.is_archived ? 'Bỏ lưu trữ' : 'Lưu trữ' }}
                  </button>
                  <div class="dropdown-divider"></div>
                  <button class="dropdown-item danger" @click="handleDeleteConversation(conv.id, $event)">
                    <Trash2 :size="12" /> Xóa
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- NHÓM: 7 NGÀY TRƯỚC (PREVIOUS 7 DAYS) -->
          <div v-if="groupedConversations.week.length" class="conv-group">
            <div class="group-header"><span>7 NGÀY TRƯỚC</span></div>
            <div
              v-for="conv in groupedConversations.week"
              :key="conv.id"
              class="conv-item"
              :class="{ active: chatStore.activeConversationId === conv.id }"
              @click="chatStore.selectConversation(conv.id)"
            >
              <div class="conv-persona-icon">{{ personaIcons[conv.agent_target] || '🤖' }}</div>
              <div class="conv-info">
                <div class="conv-title-row">
                  <span class="conv-title" :title="conv.title">{{ conv.title }}</span>
                </div>
                <div class="conv-meta">
                  <span class="time-label">{{ formatRelativeTime(conv.updated_at) }}</span>
                  <span v-if="conv.message_count" class="count-badge">{{ conv.message_count }} tin</span>
                </div>
              </div>

              <div class="conv-actions" @click.stop>
                <button class="dots-btn" @click="toggleDropdown(conv.id, $event)">
                  <MoreVertical :size="13" />
                </button>
                <div v-if="activeDropdownId === conv.id" class="dropdown-menu">
                  <button class="dropdown-item" @click="chatStore.togglePin(conv.id)"><Pin :size="12" /> Ghim</button>
                  <button class="dropdown-item" @click="startRename(conv, $event)"><Edit2 :size="12" /> Đổi tên</button>
                  <button class="dropdown-item" @click="chatStore.exportConversation(conv.id)"><FileDown :size="12" /> Tải Markdown</button>
                  <button class="dropdown-item" @click="chatStore.toggleArchive(conv.id)"><Archive :size="12" /> Lưu trữ</button>
                  <div class="dropdown-divider"></div>
                  <button class="dropdown-item danger" @click="handleDeleteConversation(conv.id, $event)"><Trash2 :size="12" /> Xóa</button>
                </div>
              </div>
            </div>
          </div>

          <!-- NHÓM: CŨ HƠN (OLDER) -->
          <div v-if="groupedConversations.month.length || groupedConversations.older.length" class="conv-group">
            <div class="group-header"><span>CŨ HƠN (OLDER)</span></div>
            <div
              v-for="conv in [...groupedConversations.month, ...groupedConversations.older]"
              :key="conv.id"
              class="conv-item"
              :class="{ active: chatStore.activeConversationId === conv.id }"
              @click="chatStore.selectConversation(conv.id)"
            >
              <div class="conv-persona-icon">{{ personaIcons[conv.agent_target] || '🤖' }}</div>
              <div class="conv-info">
                <span class="conv-title" :title="conv.title">{{ conv.title }}</span>
                <div class="conv-meta">
                  <span class="time-label">{{ formatRelativeTime(conv.updated_at) }}</span>
                </div>
              </div>

              <div class="conv-actions" @click.stop>
                <button class="dots-btn" @click="toggleDropdown(conv.id, $event)"><MoreVertical :size="13" /></button>
                <div v-if="activeDropdownId === conv.id" class="dropdown-menu">
                  <button class="dropdown-item" @click="chatStore.togglePin(conv.id)"><Pin :size="12" /> Ghim</button>
                  <button class="dropdown-item" @click="chatStore.exportConversation(conv.id)"><FileDown :size="12" /> Tải Markdown</button>
                  <button class="dropdown-item danger" @click="handleDeleteConversation(conv.id, $event)"><Trash2 :size="12" /> Xóa</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- ============================================== -->
    <!-- CỘT PHẢI: KHÔNG GIAN HỘI THOẠI CHÍNH (CANVAS) -->
    <!-- ============================================== -->
    <main class="chat-canvas">
      <!-- Header Hội Thoại -->
      <header class="canvas-header">
        <div class="header-left">
          <div class="conv-title-heading">
            <span class="agent-avatar-badge">{{ personaIcons[chatStore.currentPersona] || '👑' }}</span>
            <div class="title-wrap">
              <h3 class="canvas-title">
                {{ chatStore.activeConversation ? chatStore.activeConversation.title : 'Phiên Hội Thoại Mới' }}
              </h3>
              <small class="canvas-sub">
                Đồng bộ real-time hai chiều với Strategy Governor &middot; Hỗ trợ Human-In-The-Loop
              </small>
            </div>
          </div>
        </div>

        <div class="header-right">
          <!-- Persona Selector Dropdown -->
          <div class="persona-selector">
            <span class="selector-label">Persona Tham Vấn:</span>
            <select
              :value="chatStore.currentPersona"
              class="persona-select"
              @change="chatStore.setPersonaForActive($event.target.value)"
            >
              <option value="GOVERNOR">👑 Arbiter &middot; Strategy Governor (CRO)</option>
              <option value="TECHNICAL">📐 Vector &middot; Technical RAG Specialist</option>
              <option value="NEWS">📰 Sentinel &middot; News &amp; Macro Watchdog</option>
              <option value="REFLEXION">🧠 Scribe &middot; Reflexion Learning Coach</option>
              <option value="COUNCIL">🏛 Council &middot; Multi-Agent Consensus</option>
            </select>
          </div>

          <!-- Quick Action Buttons -->
          <button
            class="header-btn"
            :class="{ active: attachContext }"
            title="Tự động tiêm snapshot nến M15, rủi ro và cảm xúc vĩ mô vào câu trả lời"
            @click="attachContext = !attachContext"
          >
            <Zap :size="13" />
            <span>{{ attachContext ? 'Đã ghim Ngữ Cảnh M15' : 'Ghim Ngữ Cảnh M15' }}</span>
          </button>

          <button
            class="header-btn"
            title="Xuất bản toàn bộ cuộc trò chuyện dưới dạng file Markdown"
            @click="chatStore.exportConversation()"
          >
            <Download :size="13" />
            <span>Xuất Markdown</span>
          </button>

          <!-- Live Indicator -->
          <div class="live-status-pill">
            <span class="pulse-dot"></span>
            <span>LIVE CHAT</span>
          </div>
        </div>
      </header>

      <!-- Message Stream -->
      <div ref="messagesContainer" class="messages-viewport">
        <!-- Trạng thái trống (Welcome Screen kiểu Gemini) -->
        <div v-if="!chatStore.activeMessages.length && !chatStore.loadingMessages" class="gemini-welcome-canvas">
          <div class="welcome-hero">
            <div class="sparkle-circle">
              <Sparkles :size="28" class="sparkle-icon" />
            </div>
            <h2>Xin chào Trader, tôi là Hội đồng Trợ lý Giao dịch AI</h2>
            <p class="welcome-desc">
              Hệ thống tích hợp 4 AI Agent chuyên biệt: Arbiter (CRO &amp; Rủi ro), Vector (Kỹ thuật hợp lưu),
              Sentinel (Vĩ mô &amp; Circuit Breaker), Scribe (Sử ký &amp; Bài học) cùng Council (Hội đồng đồng thuận).
            </p>
          </div>

          <!-- Quick Prompts Cards -->
          <div class="quick-prompts-grid">
            <button
              v-for="(p, idx) in quickPrompts"
              :key="idx"
              class="prompt-card"
              @click="applyQuickPrompt(p)"
            >
              <div class="card-icon-top">{{ p.icon }}</div>
              <div class="card-title">{{ p.title }}</div>
              <div class="card-desc">{{ p.desc }}</div>
              <div class="card-arrow"><ArrowRight :size="12" /></div>
            </button>
          </div>
        </div>

        <!-- Danh sách tin nhắn đang có -->
        <div v-else class="message-stream-list">
          <div
            v-for="msg in chatStore.activeMessages"
            :key="msg.id"
            class="message-bubble-row"
            :class="msg.sender === 'TRADER' ? 'row-trader' : 'row-agent'"
          >
            <!-- Avatar -->
            <div class="bubble-avatar">
              <div v-if="msg.sender === 'TRADER'" class="avatar-trader">
                <User :size="14" />
              </div>
              <div v-else class="avatar-agent">
                <span>{{ personaIcons[msg.sender] || personaIcons[msg.target_agent] || '🤖' }}</span>
              </div>
            </div>

            <!-- Bubble Main -->
            <div class="bubble-main">
              <!-- Meta Row -->
              <div class="bubble-header-meta">
                <span class="sender-tag">
                  {{ msg.sender === 'TRADER' ? 'Chủ Thể (Trader)' : (msg.sender || 'AI Agent') }}
                </span>
                <span v-if="msg.sender !== 'TRADER'" class="persona-role-badge" :class="personaColors[msg.sender] || 'badge-gold'">
                  {{ msg.sender === 'GOVERNOR' ? 'CRO CONTROLLER' : msg.sender }}
                </span>
                <span class="bubble-time">{{ formatDetailTime(msg.timestamp) }}</span>
                <button
                  class="copy-btn"
                  title="Sao chép nội dung"
                  @click="copyMessageContent(msg)"
                >
                  <Check v-if="copiedMsgId === msg.id" :size="11" class="text-green" />
                  <Copy v-else :size="11" />
                </button>
              </div>

              <!-- Thẻ Tương Tác Đặc Biệt: Phê Duyệt Lệnh Mở (Approval Request) -->
              <div v-if="msg.message_type === 'APPROVAL_REQUEST'" class="interactive-approval-card">
                <div class="card-top-alert">
                  <ShieldAlert :size="16" class="alert-icon" />
                  <div>
                    <strong>YÊU CẦU PHÊ DUYỆT LỆNH MỞ (HUMAN-IN-THE-LOOP)</strong>
                    <p>Strategy Governor yêu cầu xác nhận trước khi đưa lệnh vào Auto Execution Engine.</p>
                  </div>
                </div>

                <div class="approval-details" v-html="renderMarkdown(msg.content)"></div>

                <div class="approval-action-buttons">
                  <button
                    class="approve-action-btn"
                    :disabled="msg.approval_status !== 'PENDING' || chatStore.respondingApproval"
                    @click="handleApproval(msg.id, 'APPROVE')"
                  >
                    <CheckCircle2 :size="15" />
                    <span>{{ msg.approval_status === 'APPROVED' ? 'Đã Phê Duyệt (Approved)' : 'Phê Duyệt Lệnh' }}</span>
                  </button>
                  <button
                    class="reject-action-btn"
                    :disabled="msg.approval_status !== 'PENDING' || chatStore.respondingApproval"
                    @click="handleApproval(msg.id, 'REJECT')"
                  >
                    <AlertCircle :size="15" />
                    <span>{{ msg.approval_status === 'REJECTED' ? 'Đã Từ Chối (Rejected)' : 'Từ Chối Lệnh' }}</span>
                  </button>
                  <span
                    v-if="msg.approval_status"
                    class="status-pill"
                    :class="'status-' + msg.approval_status.toLowerCase()"
                  >
                    {{ msg.approval_status }}
                  </span>
                </div>
              </div>

              <!-- Nội Dung Tin Nhắn Markdown -->
              <div
                v-else
                class="bubble-rendered-content"
                v-html="renderMarkdown(msg.content)"
              ></div>

              <!-- Metadata Badge Footer -->
              <div v-if="msg.metadata && msg.metadata.guardrail_passed === false" class="guardrail-warning-badge">
                <ShieldAlert :size="12" />
                <span>Đã ngăn chặn bởi Hard Guardrails (Quy tắc bảo vệ vốn tối cao D21/D24)</span>
              </div>
            </div>
          </div>

          <!-- AI Thinking Indicator -->
          <div v-if="chatStore.sendingMessage" class="thinking-row">
            <div class="avatar-agent">
              <span>{{ personaIcons[chatStore.currentPersona] || '🤖' }}</span>
            </div>
            <div class="thinking-bubble">
              <span class="thinking-text">{{ chatStore.currentPersona }} đang phân tích &amp; tổng hợp...</span>
              <div class="pulsing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Khung Soạn Thảo Tin Nhắn (Composer Area) -->
      <footer class="canvas-composer">
        <!-- Quick Prompts Pills -->
        <div class="composer-pills-bar">
          <button
            v-for="(p, i) in quickPrompts.slice(0, 5)"
            :key="i"
            class="pill-chip"
            @click="applyQuickPrompt(p)"
          >
            <span>{{ p.icon }}</span>
            <span>{{ p.title }}</span>
          </button>
        </div>

        <!-- Input Box Container -->
        <div class="composer-box" :class="{ focused: true }">
          <textarea
            ref="textareaRef"
            v-model="messageInput"
            placeholder="Hỏi AI Agent hoặc nhập chỉ thị điều hành rủi ro... (Enter để gửi, Shift+Enter xuống dòng)"
            class="composer-textarea"
            rows="1"
            @input="autoResizeTextarea"
            @keydown="handleKeyDown"
          ></textarea>

          <div class="composer-toolbar">
            <div class="toolbar-left">
              <button
                class="context-toggle-btn"
                :class="{ active: attachContext }"
                title="Bật/Tắt tự động chụp snapshot nến M15 và tham số"
                @click="attachContext = !attachContext"
              >
                <Zap :size="12" />
                <span>{{ attachContext ? 'Context: BẬT' : 'Context: TẮT' }}</span>
              </button>

              <span class="active-persona-indicator">
                Gửi tới: <b>{{ chatStore.currentPersona }}</b>
              </span>
            </div>

            <div class="toolbar-right">
              <span class="keyboard-tip">Enter để gửi</span>
              <button
                class="send-btn"
                :disabled="!messageInput.trim() || chatStore.sendingMessage"
                title="Gửi tin nhắn"
                @click="handleSendMessage"
              >
                <Send :size="14" />
              </button>
            </div>
          </div>
        </div>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.chat-studio-container {
  display: flex;
  width: 100%;
  height: calc(100vh - 210px);
  min-height: 620px;
  background: #ffffff;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.05);
}

/* ==================================================== */
/* CỘT TRÁI: SIDEBAR GEMINI                             */
/* ==================================================== */
.chat-sidebar {
  width: 300px;
  min-width: 280px;
  max-width: 340px;
  background: #f8faf6;
  border-right: 1px solid #dce4da;
  display: flex;
  flex-direction: column;
}

.sidebar-top {
  padding: 14px;
  border-bottom: 1px solid #e2e8df;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 9px 12px;
  background: #225c43;
  border: 1px solid #174230;
  border-radius: 6px;
  color: #c9f06b;
  font-weight: 700;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.new-chat-btn:hover {
  background: #174230;
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(34, 92, 67, 0.2);
}

.btn-inner {
  display: flex;
  align-items: center;
  gap: 8px;
}

.gemini-pill {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: rgba(201, 240, 107, 0.25);
  padding: 2px 6px;
  border-radius: 10px;
  color: #c9f06b;
  font-weight: 800;
}

.search-box {
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 1px solid #cfd9ce;
  border-radius: 6px;
  padding: 6px 10px;
  gap: 8px;
}

.search-icon {
  color: #77847c;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #1b2a23;
  font-size: 12px;
}

.clear-search-btn {
  background: none;
  border: none;
  color: #77847c;
  cursor: pointer;
  padding: 2px;
}

.archive-toggle-row {
  display: flex;
  gap: 6px;
}

.filter-pill {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 5px;
  font-size: 11px;
  background: transparent;
  border: 1px solid #d4ded3;
  border-radius: 6px;
  color: #58695f;
  cursor: pointer;
}

.filter-pill:hover {
  background: #eef3ec;
  color: #225c43;
}

.filter-pill.active {
  background: #ffffff;
  color: #225c43;
  font-weight: 700;
  border-color: #bad3bc;
  box-shadow: 0 1px 2px rgba(27, 42, 35, 0.05);
}

.conversations-scrollable {
  flex: 1;
  overflow-y: auto;
  padding: 10px 8px;
}

.sidebar-loading,
.sidebar-empty {
  padding: 30px 16px;
  text-align: center;
  color: #77847c;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.empty-icon {
  color: #9aa89d;
}

.conv-group {
  margin-bottom: 14px;
}

.group-header {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: #77847c;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.pin-icon {
  color: #c68133;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  transition: all 0.15s ease;
  margin-bottom: 2px;
  border-left: 2px solid transparent;
}

.conv-item:hover {
  background: #eef3ec;
}

.conv-item.active {
  background: #ffffff;
  border-left-color: #225c43;
  box-shadow: 0 1px 3px rgba(34, 92, 67, 0.06);
}

.conv-persona-icon {
  font-size: 15px;
  line-height: 1;
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-title-row {
  display: flex;
  align-items: center;
}

.conv-title {
  font-size: 12px;
  font-weight: 600;
  color: #1b2a23;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  width: 100%;
}

.conv-item.active .conv-title {
  color: #225c43;
  font-weight: 700;
}

.conv-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.time-label {
  font-size: 10px;
  color: #77847c;
}

.count-badge {
  font-size: 9px;
  background: #e2ece0;
  padding: 1px 5px;
  border-radius: 4px;
  color: #225c43;
  font-weight: 700;
}

.conv-actions {
  position: relative;
}

.dots-btn {
  background: none;
  border: none;
  color: #77847c;
  padding: 4px;
  border-radius: 4px;
  cursor: pointer;
  opacity: 0.4;
  transition: opacity 0.2s;
}

.conv-item:hover .dots-btn {
  opacity: 1;
}

.dots-btn:hover {
  color: #1b2a23;
  background: #dce4da;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 100;
  width: 170px;
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 6px;
  padding: 4px;
  box-shadow: 0 4px 12px rgba(27, 42, 35, 0.12);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 7px 10px;
  background: transparent;
  border: none;
  border-radius: 4px;
  font-size: 11px;
  color: #3b4e41;
  cursor: pointer;
  text-align: left;
}

.dropdown-item:hover {
  background: #edf1ec;
  color: #225c43;
}

.dropdown-item.danger {
  color: #c65345;
}

.dropdown-item.danger:hover {
  background: #fcf1ef;
}

.dropdown-divider {
  height: 1px;
  background: #e8ede7;
  margin: 4px 0;
}

.inline-rename-box {
  display: flex;
  align-items: center;
  gap: 4px;
}

.rename-input {
  flex: 1;
  font-size: 11px;
  background: #ffffff;
  border: 1px solid #225c43;
  border-radius: 4px;
  color: #1b2a23;
  padding: 2px 5px;
  outline: none;
}

.save-rename-btn {
  background: #225c43;
  border: none;
  border-radius: 4px;
  color: #c9f06b;
  padding: 3px 6px;
  cursor: pointer;
}

/* ==================================================== */
/* CỘT PHẢI: CANVAS KHÔNG GIAN HỘI THOẠI                */
/* ==================================================== */
.chat-canvas {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fdfefd;
  position: relative;
  min-width: 0;
}

.canvas-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  background: #f8faf6;
  border-bottom: 1px solid #dce4da;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  min-width: 0;
}

.conv-title-heading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-avatar-badge {
  font-size: 20px;
  line-height: 1;
}

.canvas-title {
  margin: 0;
  font-size: 13px;
  font-weight: 800;
  color: #1b2a23;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.canvas-sub {
  color: #77847c;
  font-size: 10px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.persona-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.selector-label {
  font-size: 10px;
  color: #77847c;
  font-weight: 600;
}

.persona-select {
  background: #ffffff;
  border: 1px solid #cfd9ce;
  border-radius: 5px;
  color: #1b2a23;
  font-size: 11px;
  padding: 5px 8px;
  outline: none;
  cursor: pointer;
}

.header-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  background: #edf1ec;
  border: 1px solid #d4ded3;
  border-radius: 5px;
  color: #4a5c50;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.header-btn:hover {
  background: #e2ebe0;
  color: #1b2a23;
}

.header-btn.active {
  background: #fef5e6;
  border-color: #ecc68a;
  color: #9c6014;
}

.live-status-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 7px;
  background: #e8efe6;
  border: 1px solid #bad3bc;
  border-radius: 12px;
  font-size: 9px;
  font-weight: 800;
  color: #225c43;
  letter-spacing: 0.5px;
}

.pulse-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #54a267;
  box-shadow: 0 0 6px #54a267;
  animation: pulse 1.8s infinite;
}

@keyframes pulse {
  0% { opacity: 0.4; }
  50% { opacity: 1; }
  100% { opacity: 0.4; }
}

/* ==================================================== */
/* VIEWPORT TIN NHẮN                                   */
/* ==================================================== */
.messages-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

/* Welcome Hero (Gemini) */
.gemini-welcome-canvas {
  margin: auto;
  max-width: 820px;
  text-align: center;
  padding: 20px;
}

.sparkle-circle {
  width: 48px;
  height: 48px;
  margin: 0 auto 14px;
  border-radius: 50%;
  background: #eaf1e9;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #c8d9c5;
}

.sparkle-icon {
  color: #225c43;
}

.welcome-hero h2 {
  font-size: 20px;
  font-weight: 800;
  color: #1b2a23;
  margin-bottom: 6px;
}

.welcome-desc {
  font-size: 12px;
  color: #637569;
  line-height: 1.55;
  max-width: 640px;
  margin: 0 auto 24px;
}

.quick-prompts-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  text-align: left;
}

.prompt-card {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 8px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.03);
}

.prompt-card:hover {
  background: #f4f8f3;
  border-color: #9fc9a4;
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(34, 92, 67, 0.08);
}

.card-icon-top {
  font-size: 18px;
  margin-bottom: 4px;
}

.card-title {
  font-size: 12px;
  font-weight: 700;
  color: #1b2a23;
  margin-bottom: 3px;
}

.card-desc {
  font-size: 10px;
  color: #77847c;
  line-height: 1.4;
  margin-bottom: 6px;
}

.card-arrow {
  margin-top: auto;
  color: #225c43;
  opacity: 0;
  transition: opacity 0.15s;
}

.prompt-card:hover .card-arrow {
  opacity: 1;
}

/* Danh sách tin nhắn */
.message-stream-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
}

.message-bubble-row {
  display: flex;
  gap: 12px;
  width: 100%;
}

.row-trader {
  flex-direction: row-reverse;
}

.bubble-avatar {
  flex-shrink: 0;
  margin-top: 2px;
}

.avatar-trader,
.avatar-agent {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.avatar-trader {
  background: #225c43;
  color: #c9f06b;
  font-weight: 800;
}

.avatar-agent {
  background: #edf1ec;
  border: 1px solid #d4ded3;
}

.bubble-main {
  max-width: 82%;
  display: flex;
  flex-direction: column;
}

.bubble-header-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 10px;
}

.row-trader .bubble-header-meta {
  justify-content: flex-end;
}

.sender-tag {
  font-weight: 700;
  color: #1b2a23;
}

.persona-role-badge {
  font-size: 8.5px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 4px;
  text-transform: uppercase;
}

.badge-gold { background: #fef5e6; color: #9c6014; border: 1px solid #edd4ad; }
.badge-blue { background: #eaf1e9; color: #225c43; border: 1px solid #c8d9c5; }
.badge-purple { background: #f3eef8; color: #723b9c; border: 1px solid #d9c7ea; }
.badge-green { background: #e3ede1; color: #1e5939; border: 1px solid #b5d2be; }
.badge-amber { background: #fcf0e8; color: #b3521b; border: 1px solid #f2cdb8; }

.bubble-time {
  color: #77847c;
}

.copy-btn {
  background: none;
  border: none;
  color: #77847c;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}

.copy-btn:hover {
  color: #1b2a23;
  background: #edf1ec;
}

.bubble-rendered-content {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.55;
  color: #1b2a23;
  box-shadow: 0 1px 3px rgba(27, 42, 35, 0.04);
}

.row-trader .bubble-rendered-content {
  background: #e8efe6;
  border: 1px solid #c4d7c2;
  border-top-right-radius: 2px;
}

.row-agent .bubble-rendered-content {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-top-left-radius: 2px;
}

/* Interactive Approval Card */
.interactive-approval-card {
  background: #fefaf3;
  border: 1px solid #ecc68a;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(198, 129, 51, 0.08);
}

.card-top-alert {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #9c6014;
  margin-bottom: 10px;
}

.card-top-alert strong {
  font-size: 12px;
  display: block;
}

.card-top-alert p {
  font-size: 10px;
  color: #77847c;
  margin: 2px 0 0;
}

.approval-details {
  font-size: 11px;
  line-height: 1.5;
  color: #3b4e41;
}

.proposal-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 8px;
  margin: 10px 0;
}

.p-item {
  background: #ffffff;
  border: 1px solid #edd4ad;
  border-radius: 6px;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.p-item small {
  font-size: 9px;
  color: #77847c;
  font-weight: 700;
}

.p-item strong {
  font-size: 11px;
  color: #1b2a23;
}

.approval-btn-bar {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.appr-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
}

.appr-btn.approve {
  background: #225c43;
  color: #c9f06b;
  border-color: #174230;
}

.appr-btn.approve:hover {
  background: #174230;
  color: #ffffff;
}

.appr-btn.reject {
  background: #ffffff;
  border-color: #dce4da;
  color: #58695f;
}

.appr-btn.reject:hover {
  background: #fcf1ef;
  color: #c65345;
  border-color: #f2b9b1;
}

/* Typing Indicator */
.typing-indicator-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 6px;
  width: fit-content;
  color: #77847c;
  font-size: 11px;
  font-style: italic;
}

.pulsing-dots {
  display: flex;
  gap: 4px;
}

.pulsing-dots span {
  width: 5px;
  height: 5px;
  background: #225c43;
  border-radius: 50%;
  animation: dotBlink 1.4s infinite ease-in-out both;
}

.pulsing-dots span:nth-child(1) { animation-delay: -0.32s; }
.pulsing-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes dotBlink {
  0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

/* ==================================================== */
/* KHUNG SOẠN THẢO (COMPOSER AREA)                      */
/* ==================================================== */
.canvas-composer {
  padding: 12px 20px 16px;
  background: #f8faf6;
  border-top: 1px solid #dce4da;
}

.composer-pills-bar {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 8px;
  scrollbar-width: none !important;
}

.composer-pills-bar::-webkit-scrollbar {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
}

.pill-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: #ffffff;
  border: 1px solid #d4ded3;
  border-radius: 12px;
  font-size: 10px;
  color: #4a5c50;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.pill-chip:hover {
  background: #eef3ec;
  border-color: #bad3bc;
  color: #225c43;
}

.composer-box {
  background: #ffffff;
  border: 1px solid #cfd9ce;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.composer-box:focus-within {
  border-color: #225c43;
  box-shadow: 0 0 0 2px rgba(34, 92, 67, 0.12);
}

.composer-textarea {
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  color: #1b2a23;
  font-size: 12px;
  line-height: 1.5;
  resize: none;
  font-family: inherit;
  max-height: 180px;
}

.composer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid #eef3ec;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.context-toggle-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 7px;
  background: #edf1ec;
  border: 1px solid #d4ded3;
  border-radius: 4px;
  color: #58695f;
  font-size: 10px;
  cursor: pointer;
  transition: all 0.15s;
}

.context-toggle-btn:hover {
  color: #1b2a23;
}

.context-toggle-btn.active {
  background: #fef5e6;
  border-color: #ecc68a;
  color: #9c6014;
}

.active-persona-indicator {
  font-size: 10px;
  color: #77847c;
}

.active-persona-indicator b {
  color: #225c43;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.keyboard-tip {
  font-size: 9px;
  color: #77847c;
}

.send-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: #225c43;
  border: none;
  color: #c9f06b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
}

.send-btn:hover:not(:disabled) {
  background: #174230;
  color: #ffffff;
}

.send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* ==================================================== */
/* MARKDOWN FORMATTING UTILITIES                        */
/* ==================================================== */
:deep(.md-h2) { font-size: 14px; font-weight: 800; color: #1b2a23; margin: 8px 0 4px; }
:deep(.md-h3) { font-size: 12.5px; font-weight: 800; color: #225c43; margin: 6px 0 3px; }
:deep(.md-h4) { font-size: 11.5px; font-weight: 700; color: #723b9c; margin: 4px 0 2px; }
:deep(.md-quote) { border-left: 3px solid #225c43; padding-left: 10px; color: #55675c; margin: 6px 0; font-style: italic; }
:deep(.md-inline-code) { background: #edf1ec; padding: 1px 5px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #9c6014; }
:deep(.md-code-block) { background: #17241e; border: 1px solid #225c43; border-radius: 6px; margin: 8px 0; overflow: hidden; }
:deep(.md-code-header) { font-size: 9px; font-weight: 700; text-transform: uppercase; background: rgba(255, 255, 255, 0.05); padding: 4px 8px; color: #c9f06b; letter-spacing: 0.5px; }
:deep(.md-code-block pre) { margin: 0; padding: 10px; font-size: 11px; font-family: monospace; color: #c9f06b; overflow-x: auto; }
:deep(.md-ul) { margin: 6px 0; padding-left: 18px; }
:deep(.md-li) { margin-bottom: 4px; }
:deep(.md-gap) { height: 10px; }
:deep(strong) { color: #1b2a23; font-weight: 700; }
</style>
