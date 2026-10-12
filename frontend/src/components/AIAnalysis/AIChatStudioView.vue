<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
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
    title: 'Bản tin điều hành',
    desc: 'Yêu cầu Governor xuất bản Executive Briefing',
    text: 'Xuất bản bản tin điều hành mới nhất từ Chief Risk Officer',
    persona: 'GOVERNOR',
  },
  {
    icon: '📉',
    title: 'Hạ rủi ro 0.5%',
    desc: 'Điều chỉnh tham số bảo toàn vốn theo quy tắc D21',
    text: 'Hạ mức rủi ro xuống 0.5% vốn và nâng SL lên 2.0x ATR',
    persona: 'GOVERNOR',
  },
  {
    icon: '📐',
    title: 'Phân tích Wyckoff & SMC',
    desc: 'Hợp lưu Spring M15, Liquidity Sweep & Discount POI',
    text: 'Đánh giá cấu trúc M15 hiện tại theo trường phái Wyckoff và SMC Order Block',
    persona: 'TECHNICAL',
  },
  {
    icon: '📰',
    title: 'Bối cảnh Vĩ mô & DXY',
    desc: 'Đo lường điểm cảm xúc và trạng thái Circuit Breaker',
    text: 'Tóm tắt tình hình tin tức vĩ mô hôm nay, tương quan DXY và trạng thái Circuit Breaker',
    persona: 'NEWS',
  },
  {
    icon: '🧠',
    title: 'Kinh nghiệm & Sai lầm',
    desc: 'Hồi tưởng bài học Post-Mortem và Taxonomy lỗi',
    text: 'Tổng kết tỷ lệ thắng và phân loại các sai lầm lặp lại gần nhất',
    persona: 'REFLEXION',
  },
  {
    icon: '🏛',
    title: 'Hội đồng Đồng thuận',
    desc: 'Nghị quyết đa agent tổng hợp ý kiến Technical, News & Reflexion',
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

onMounted(async () => {
  if (!chatStore.conversations.length) {
    await chatStore.init()
  }
  scrollToBottom()
  // Tự động đóng dropdown khi click ra ngoài
  window.addEventListener('click', closeAllDropdowns)
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
              <option value="GOVERNOR">👑 Strategy Governor (CRO)</option>
              <option value="TECHNICAL">📐 Technical RAG Specialist (SMC/Wyckoff)</option>
              <option value="NEWS">📰 News &amp; Macro Agent (Circuit Breaker)</option>
              <option value="REFLEXION">🧠 Reflexion Learning Coach</option>
              <option value="COUNCIL">🏛 Multi-Agent Consensus Council</option>
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
              Hệ thống tích hợp 5 AI Agent chuyên biệt: Thẩm định rủi ro đa tầng (CRO), Phân tích kỹ thuật hợp lưu (Wyckoff/ICT/SMC),
              Giám sát tin tức vĩ mô khẩn và Đúc rút kinh nghiệm thực nghiệm.
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
  height: calc(100vh - 160px);
  min-height: 640px;
  background: #090d16;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45);
}

/* ==================================================== */
/* CỘT TRÁI: SIDEBAR GEMINI                             */
/* ==================================================== */
.chat-sidebar {
  width: 300px;
  min-width: 280px;
  max-width: 340px;
  background: #0b0f19;
  border-right: 1px solid rgba(255, 255, 255, 0.07);
  display: flex;
  flex-direction: column;
}

.sidebar-top {
  padding: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 14px;
  background: linear-gradient(135deg, rgba(56, 139, 253, 0.15) 0%, rgba(138, 56, 253, 0.12) 100%);
  border: 1px solid rgba(56, 139, 253, 0.35);
  border-radius: 8px;
  color: #58a6ff;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.new-chat-btn:hover {
  background: linear-gradient(135deg, rgba(56, 139, 253, 0.25) 0%, rgba(138, 56, 253, 0.22) 100%);
  border-color: rgba(56, 139, 253, 0.6);
  box-shadow: 0 0 16px rgba(56, 139, 253, 0.25);
}

.btn-inner {
  display: flex;
  align-items: center;
  gap: 8px;
}

.gemini-pill {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 10px;
  color: #c9d1d9;
}

.search-box {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 6px 10px;
  gap: 8px;
}

.search-icon {
  color: #8b949e;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e6edf3;
  font-size: 12px;
}

.clear-search-btn {
  background: none;
  border: none;
  color: #8b949e;
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
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  color: #8b949e;
  cursor: pointer;
}

.filter-pill.active {
  background: rgba(255, 255, 255, 0.08);
  color: #58a6ff;
  border-color: rgba(56, 139, 253, 0.3);
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
  color: #8b949e;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.empty-icon {
  color: #484f58;
}

.conv-group {
  margin-bottom: 14px;
}

.group-header {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: #6e7681;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.pin-icon {
  color: #d29922;
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
  background: rgba(255, 255, 255, 0.04);
}

.conv-item.active {
  background: rgba(56, 139, 253, 0.12);
  border-left-color: #58a6ff;
}

.conv-persona-icon {
  font-size: 16px;
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
  font-weight: 500;
  color: #c9d1d9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
  width: 100%;
}

.conv-item.active .conv-title {
  color: #58a6ff;
  font-weight: 600;
}

.conv-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.time-label {
  font-size: 10px;
  color: #6e7681;
}

.count-badge {
  font-size: 9px;
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 4px;
  border-radius: 4px;
  color: #8b949e;
}

.conv-actions {
  position: relative;
}

.dots-btn {
  background: none;
  border: none;
  color: #6e7681;
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
  color: #e6edf3;
  background: rgba(255, 255, 255, 0.08);
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 100;
  width: 170px;
  background: #161b22;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
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
  color: #c9d1d9;
  cursor: pointer;
  text-align: left;
}

.dropdown-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.dropdown-item.danger {
  color: #f85149;
}

.dropdown-item.danger:hover {
  background: rgba(248, 81, 73, 0.15);
}

.dropdown-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
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
  background: #1c2128;
  border: 1px solid #58a6ff;
  border-radius: 4px;
  color: #fff;
  padding: 3px 6px;
  outline: none;
}

.save-rename-btn {
  background: #238636;
  border: none;
  border-radius: 4px;
  color: #fff;
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
  background: #090d16;
  position: relative;
  min-width: 0;
}

.canvas-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #0e131f;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
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
  gap: 12px;
}

.agent-avatar-badge {
  font-size: 24px;
  line-height: 1;
}

.canvas-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #e6edf3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.canvas-sub {
  color: #8b949e;
  font-size: 11px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.persona-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-label {
  font-size: 11px;
  color: #8b949e;
}

.persona-select {
  background: #161b22;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  color: #e6edf3;
  font-size: 12px;
  padding: 6px 10px;
  outline: none;
  cursor: pointer;
}

.header-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 6px;
  color: #c9d1d9;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.header-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.header-btn.active {
  background: rgba(210, 153, 34, 0.15);
  border-color: #d29922;
  color: #f1e05a;
}

.live-status-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: rgba(46, 160, 67, 0.12);
  border: 1px solid rgba(46, 160, 67, 0.3);
  border-radius: 12px;
  font-size: 10px;
  font-weight: 700;
  color: #3fb950;
  letter-spacing: 0.5px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3fb950;
  box-shadow: 0 0 6px #3fb950;
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
  padding: 24px;
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
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(56, 139, 253, 0.2) 0%, rgba(210, 153, 34, 0.2) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(56, 139, 253, 0.4);
  box-shadow: 0 0 24px rgba(56, 139, 253, 0.25);
}

.sparkle-icon {
  color: #58a6ff;
}

.welcome-hero h2 {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff 0%, #8b949e 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}

.welcome-desc {
  font-size: 13px;
  color: #8b949e;
  line-height: 1.6;
  max-width: 640px;
  margin: 0 auto 28px;
}

.quick-prompts-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  text-align: left;
}

.prompt-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  position: relative;
}

.prompt-card:hover {
  background: rgba(56, 139, 253, 0.08);
  border-color: rgba(56, 139, 253, 0.35);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
}

.card-icon-top {
  font-size: 20px;
  margin-bottom: 6px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #e6edf3;
  margin-bottom: 4px;
}

.card-desc {
  font-size: 11px;
  color: #8b949e;
  line-height: 1.4;
  margin-bottom: 8px;
}

.card-arrow {
  margin-top: auto;
  color: #58a6ff;
  opacity: 0;
  transition: opacity 0.2s;
}

.prompt-card:hover .card-arrow {
  opacity: 1;
}

/* Danh sách tin nhắn */
.message-stream-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
}

.message-bubble-row {
  display: flex;
  gap: 14px;
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
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.avatar-trader {
  background: #1f6feb;
  color: #fff;
}

.avatar-agent {
  background: #161b22;
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.bubble-main {
  max-width: 82%;
  display: flex;
  flex-direction: column;
}

.bubble-header-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  font-size: 11px;
}

.row-trader .bubble-header-meta {
  justify-content: flex-end;
}

.sender-tag {
  font-weight: 600;
  color: #c9d1d9;
}

.persona-role-badge {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 8px;
  text-transform: uppercase;
}

.badge-gold { background: rgba(210, 153, 34, 0.2); color: #f1e05a; border: 1px solid rgba(210, 153, 34, 0.4); }
.badge-blue { background: rgba(56, 139, 253, 0.2); color: #58a6ff; border: 1px solid rgba(56, 139, 253, 0.4); }
.badge-purple { background: rgba(163, 113, 247, 0.2); color: #bc8cff; border: 1px solid rgba(163, 113, 247, 0.4); }
.badge-green { background: rgba(46, 160, 67, 0.2); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.4); }
.badge-amber { background: rgba(219, 109, 40, 0.2); color: #f0883e; border: 1px solid rgba(219, 109, 40, 0.4); }

.bubble-time {
  color: #6e7681;
}

.copy-btn {
  background: none;
  border: none;
  color: #6e7681;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}

.copy-btn:hover {
  color: #c9d1d9;
  background: rgba(255, 255, 255, 0.08);
}

.bubble-rendered-content {
  padding: 14px 18px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #e6edf3;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.row-trader .bubble-rendered-content {
  background: #193256;
  border: 1px solid rgba(56, 139, 253, 0.3);
  border-top-right-radius: 2px;
}

.row-agent .bubble-rendered-content {
  background: #121826;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-top-left-radius: 2px;
}

/* Interactive Approval Card */
.interactive-approval-card {
  background: #151a28;
  border: 1px solid #d29922;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 0 20px rgba(210, 153, 34, 0.15);
}

.card-top-alert {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: #f1e05a;
  margin-bottom: 12px;
}

.card-top-alert strong {
  font-size: 13px;
  display: block;
}

.card-top-alert p {
  font-size: 11px;
  color: #8b949e;
  margin: 2px 0 0;
}

.approval-details {
  font-size: 12px;
  line-height: 1.5;
  color: #e6edf3;
  background: rgba(0, 0, 0, 0.25);
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 14px;
}

.approval-action-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
}

.approve-action-btn,
.reject-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.approve-action-btn {
  background: #238636;
  border: 1px solid #2ea043;
  color: #fff;
}

.approve-action-btn:hover:not(:disabled) {
  background: #2ea043;
  box-shadow: 0 0 12px rgba(46, 160, 67, 0.4);
}

.reject-action-btn {
  background: #da3633;
  border: 1px solid #f85149;
  color: #fff;
}

.reject-action-btn:hover:not(:disabled) {
  background: #f85149;
  box-shadow: 0 0 12px rgba(248, 81, 73, 0.4);
}

.approve-action-btn:disabled,
.reject-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.status-pill {
  margin-left: auto;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.status-approved { background: rgba(46, 160, 67, 0.2); color: #3fb950; border: 1px solid #3fb950; }
.status-rejected { background: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid #f85149; }
.status-pending { background: rgba(210, 153, 34, 0.2); color: #d29922; border: 1px solid #d29922; }

.guardrail-warning-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 11px;
  color: #f85149;
  background: rgba(248, 81, 73, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid rgba(248, 81, 73, 0.3);
}

/* Thinking Indicator */
.thinking-row {
  display: flex;
  gap: 14px;
  align-items: center;
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #121826;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 10px 16px;
  border-radius: 12px;
}

.thinking-text {
  font-size: 12px;
  color: #8b949e;
  font-style: italic;
}

.pulsing-dots {
  display: flex;
  gap: 4px;
}

.pulsing-dots span {
  width: 6px;
  height: 6px;
  background: #58a6ff;
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
  padding: 14px 24px 20px;
  background: #090d16;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.composer-pills-bar {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.pill-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  font-size: 11px;
  color: #c9d1d9;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.pill-chip:hover {
  background: rgba(56, 139, 253, 0.12);
  border-color: rgba(56, 139, 253, 0.35);
  color: #58a6ff;
}

.composer-box {
  background: #111624;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  padding: 12px 14px 10px;
  display: flex;
  flex-direction: column;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.composer-box:focus-within {
  border-color: #58a6ff;
  box-shadow: 0 0 16px rgba(56, 139, 253, 0.18);
}

.composer-textarea {
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  color: #e6edf3;
  font-size: 13px;
  line-height: 1.5;
  resize: none;
  font-family: inherit;
  max-height: 180px;
}

.composer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.context-toggle-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: #8b949e;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.context-toggle-btn:hover {
  color: #e6edf3;
}

.context-toggle-btn.active {
  background: rgba(210, 153, 34, 0.2);
  border-color: #d29922;
  color: #f1e05a;
}

.active-persona-indicator {
  font-size: 11px;
  color: #8b949e;
}

.active-persona-indicator b {
  color: #58a6ff;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.keyboard-tip {
  font-size: 10px;
  color: #6e7681;
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #1f6feb 0%, #388bfd 100%);
  border: none;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 0 12px rgba(56, 139, 253, 0.5);
}

.send-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* ==================================================== */
/* MARKDOWN FORMATTING UTILITIES                        */
/* ==================================================== */
:deep(.md-h2) { font-size: 16px; font-weight: 700; color: #58a6ff; margin: 8px 0 4px; }
:deep(.md-h3) { font-size: 14px; font-weight: 700; color: #f0883e; margin: 6px 0 3px; }
:deep(.md-h4) { font-size: 13px; font-weight: 600; color: #bc8cff; margin: 4px 0 2px; }
:deep(.md-quote) { border-left: 3px solid #58a6ff; padding-left: 10px; color: #8b949e; margin: 6px 0; font-style: italic; }
:deep(.md-inline-code) { background: rgba(110, 118, 129, 0.3); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; color: #f0883e; }
:deep(.md-code-block) { background: #0b0f19; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; margin: 10px 0; overflow: hidden; }
:deep(.md-code-header) { font-size: 10px; font-weight: 700; text-transform: uppercase; background: rgba(255, 255, 255, 0.05); padding: 4px 10px; color: #8b949e; letter-spacing: 0.5px; }
:deep(.md-code-block pre) { margin: 0; padding: 10px; font-size: 12px; font-family: monospace; color: #388bfd; overflow-x: auto; }
:deep(.md-ul) { margin: 6px 0; padding-left: 18px; }
:deep(.md-li) { margin-bottom: 4px; }
:deep(.md-gap) { height: 10px; }
:deep(strong) { color: #fff; font-weight: 600; }
</style>
