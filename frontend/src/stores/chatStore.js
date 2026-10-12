import { reactive } from 'vue'
import {
  createConversation as createConversationApi,
  deleteConversation as deleteConversationApi,
  exportConversation as exportConversationApi,
  fetchAgentPersonas as fetchAgentPersonasApi,
  fetchChatMarketContext as fetchChatMarketContextApi,
  fetchConversationMessages as fetchConversationMessagesApi,
  fetchConversations as fetchConversationsApi,
  respondChatApproval as respondChatApprovalApi,
  sendConversationMessage as sendConversationMessageApi,
  updateConversation as updateConversationApi,
} from '../services/api'

export const chatStore = reactive({
  // Danh sách hội thoại & session hoạt động
  conversations: [],
  activeConversationId: null,
  messagesMap: {}, // conversationId -> Array<Message>
  personas: [],
  currentPersona: 'GOVERNOR',
  marketContext: null,

  // Trạng thái giao diện
  loadingConversations: false,
  loadingMessages: false,
  sendingMessage: false,
  respondingApproval: false,
  chatError: null,
  searchQuery: '',
  showArchived: false,
  unreadCount: 0,
  isWidgetOpen: false,
  latestToast: null,
  _toastTimer: null,

  showToast(payload) {
    if (this._toastTimer) clearTimeout(this._toastTimer)
    this.latestToast = payload
    this._toastTimer = setTimeout(() => {
      this.latestToast = null
    }, 6000)
  },

  dismissToast() {
    if (this._toastTimer) clearTimeout(this._toastTimer)
    this.latestToast = null
  },

  openWidget(conversationId = null) {
    this.isWidgetOpen = true
    this.unreadCount = 0
    this.dismissToast()
    if (conversationId && conversationId !== this.activeConversationId) {
      this.selectConversation(conversationId)
    }
  },

  closeWidget() {
    this.isWidgetOpen = false
  },

  toggleWidget() {
    if (this.isWidgetOpen) {
      this.closeWidget()
    } else {
      this.openWidget()
    }
  },

  // Getters tính toán
  get activeConversation() {
    return this.conversations.find((c) => c.id === this.activeConversationId) || null
  },

  get activeMessages() {
    if (!this.activeConversationId) return []
    return this.messagesMap[this.activeConversationId] || []
  },

  get filteredConversations() {
    let list = this.conversations
    if (!this.showArchived) {
      list = list.filter((c) => !c.is_archived)
    } else {
      list = list.filter((c) => c.is_archived)
    }

    if (this.searchQuery && this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase().trim()
      list = list.filter(
        (c) =>
          c.title?.toLowerCase().includes(q) ||
          c.last_message?.content?.toLowerCase().includes(q)
      )
    }

    // Luôn ưu tiên Ghim lên đầu, tiếp theo là thời gian cập nhật mới nhất
    return [...list].sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) {
        return a.is_pinned ? -1 : 1
      }
      return new Date(b.updated_at || 0) - new Date(a.updated_at || 0)
    })
  },

  // Khởi tạo Store khi nạp ứng dụng
  async init() {
    await Promise.all([
      this.loadPersonas(),
      this.loadMarketContext(),
      this.loadConversations(),
    ])

    // Tự động chọn cuộc trò chuyện đầu tiên nếu có
    if (!this.activeConversationId && this.conversations.length > 0) {
      const firstActive = this.conversations.find((c) => !c.is_archived) || this.conversations[0]
      if (firstActive) {
        await this.selectConversation(firstActive.id)
      }
    }
  },

  async loadPersonas() {
    try {
      const data = await fetchAgentPersonasApi()
      if (Array.isArray(data)) {
        this.personas = data
      }
    } catch (err) {
      console.warn('Could not load agent personas:', err)
    }
  },

  async loadMarketContext() {
    try {
      const data = await fetchChatMarketContextApi()
      this.marketContext = data
    } catch (err) {
      console.warn('Could not load market context snapshot:', err)
    }
  },

  async loadConversations(includeArchived = false) {
    this.loadingConversations = true
    this.chatError = null
    try {
      const data = await fetchConversationsApi(includeArchived, 100, 0)
      if (Array.isArray(data)) {
        this.conversations = data
      }
    } catch (err) {
      this.chatError = err.message || 'Không thể tải danh sách cuộc trò chuyện'
    } finally {
      this.loadingConversations = false
    }
  },

  async selectConversation(conversationId) {
    this.activeConversationId = conversationId
    const conv = this.activeConversation
    if (conv && conv.agent_target) {
      this.currentPersona = conv.agent_target
    }
    await this.loadMessages(conversationId)
  },

  async loadMessages(conversationId) {
    if (!conversationId) return
    this.loadingMessages = true
    this.chatError = null
    try {
      const data = await fetchConversationMessagesApi(conversationId, 200, 0)
      if (Array.isArray(data)) {
        this.messagesMap[conversationId] = data
      }
    } catch (err) {
      this.chatError = err.message || 'Không thể tải tin nhắn cuộc trò chuyện'
    } finally {
      this.loadingMessages = false
    }
  },

  async createNewConversation(title = 'Cuộc trò chuyện mới', agentTarget = null) {
    this.loadingConversations = true
    try {
      const target = agentTarget || this.currentPersona || 'GOVERNOR'
      const newConv = await createConversationApi({
        title,
        agent_target: target,
      })
      // Thêm vào danh sách và chọn ngay
      this.conversations.unshift(newConv)
      this.activeConversationId = newConv.id
      this.currentPersona = target
      this.messagesMap[newConv.id] = []
      return newConv
    } catch (err) {
      this.chatError = err.message || 'Không thể tạo cuộc trò chuyện mới'
      throw err
    } finally {
      this.loadingConversations = false
    }
  },

  async updateConversationTitle(conversationId, title) {
    const clean = (title || '').trim()
    if (!clean) return
    try {
      const updated = await updateConversationApi(conversationId, { title: clean })
      const idx = this.conversations.findIndex((c) => c.id === conversationId)
      if (idx !== -1) {
        this.conversations[idx] = { ...this.conversations[idx], ...updated }
      }
    } catch (err) {
      this.chatError = err.message || 'Không thể cập nhật tiêu đề'
    }
  },

  async togglePin(conversationId) {
    const conv = this.conversations.find((c) => c.id === conversationId)
    if (!conv) return
    const newPinned = !conv.is_pinned
    try {
      const updated = await updateConversationApi(conversationId, { is_pinned: newPinned })
      const idx = this.conversations.findIndex((c) => c.id === conversationId)
      if (idx !== -1) {
        this.conversations[idx] = { ...this.conversations[idx], ...updated }
      }
    } catch (err) {
      this.chatError = err.message || 'Không thể ghim cuộc trò chuyện'
    }
  },

  async toggleArchive(conversationId) {
    const conv = this.conversations.find((c) => c.id === conversationId)
    if (!conv) return
    const newArchived = !conv.is_archived
    try {
      const updated = await updateConversationApi(conversationId, { is_archived: newArchived })
      const idx = this.conversations.findIndex((c) => c.id === conversationId)
      if (idx !== -1) {
        this.conversations[idx] = { ...this.conversations[idx], ...updated }
      }
      // Nếu đang mở conversation này mà bị archive, chuyển sang conversation khác
      if (this.activeConversationId === conversationId && !this.showArchived) {
        const next = this.conversations.find((c) => !c.is_archived && c.id !== conversationId)
        if (next) {
          await this.selectConversation(next.id)
        } else {
          this.activeConversationId = null
        }
      }
    } catch (err) {
      this.chatError = err.message || 'Không thể lưu trữ cuộc trò chuyện'
    }
  },

  async setPersonaForActive(personaId) {
    this.currentPersona = personaId
    if (this.activeConversationId) {
      try {
        const updated = await updateConversationApi(this.activeConversationId, {
          agent_target: personaId,
        })
        const idx = this.conversations.findIndex((c) => c.id === this.activeConversationId)
        if (idx !== -1) {
          this.conversations[idx] = { ...this.conversations[idx], ...updated }
        }
      } catch (err) {
        console.warn('Could not update persona for conversation:', err)
      }
    }
  },

  async deleteConversation(conversationId) {
    try {
      await deleteConversationApi(conversationId)
      delete this.messagesMap[conversationId]
      this.conversations = this.conversations.filter((c) => c.id !== conversationId)

      if (this.activeConversationId === conversationId) {
        const next = this.conversations.find((c) => !c.is_archived) || this.conversations[0]
        if (next) {
          await this.selectConversation(next.id)
        } else {
          this.activeConversationId = null
        }
      }
    } catch (err) {
      this.chatError = err.message || 'Không thể xóa cuộc trò chuyện'
    }
  },

  async sendMessage(messageText, { targetAgent = null, attachMarketContext = false } = {}) {
    const cleanText = (messageText || '').trim()
    if (!cleanText) return

    // 1. Nếu chưa có conversation hoạt động, tạo mới trước
    let convId = this.activeConversationId
    if (!convId) {
      const persona = targetAgent || this.currentPersona || 'GOVERNOR'
      const newConv = await this.createNewConversation('Cuộc trò chuyện mới', persona)
      convId = newConv.id
    }

    const persona = targetAgent || this.currentPersona || 'GOVERNOR'
    const clientMsgId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7)

    // Tạo tin nhắn tạm thời (optimistic update)
    if (!this.messagesMap[convId]) {
      this.messagesMap[convId] = []
    }

    const optimisticMsg = {
      id: 'opt_' + Date.now(),
      client_msg_id: clientMsgId,
      conversation_id: convId,
      sender: 'TRADER',
      target_agent: persona,
      message_type: 'TEXT',
      content: cleanText,
      timestamp: new Date().toISOString(),
      is_optimistic: true,
    }
    this.messagesMap[convId].push(optimisticMsg)
    this.sendingMessage = true
    this.chatError = null

    try {
      const res = await sendConversationMessageApi(convId, {
        message: cleanText,
        target_agent: persona,
        client_msg_id: clientMsgId,
        attach_market_context: attachMarketContext,
      })

      // Thay thế optimistic message bằng bản ghi chính thức từ backend
      const thread = this.messagesMap[convId]
      const optIdx = thread.findIndex((m) => m.client_msg_id === clientMsgId)
      if (optIdx !== -1) {
        thread.splice(optIdx, 1, res.trader_message)
      } else {
        thread.push(res.trader_message)
      }

      // Thêm phản hồi của Agent
      if (res.agent_message) {
        thread.push(res.agent_message)
      }

      // Cập nhật lại thông tin session trong danh sách (tiêu đề tự động, mốc thời gian, last message)
      const convIdx = this.conversations.findIndex((c) => c.id === convId)
      if (convIdx !== -1) {
        this.conversations[convIdx].updated_at = new Date().toISOString()
        this.conversations[convIdx].message_count = thread.length
        this.conversations[convIdx].last_message = res.agent_message || res.trader_message

        // Tự động cập nhật tiêu đề nếu backend đã auto-title
        if (
          this.conversations[convIdx].title === 'Cuộc trò chuyện mới' &&
          cleanText.length > 0
        ) {
          const autoTitle = cleanText.length > 35 ? cleanText.substring(0, 32) + '...' : cleanText
          this.conversations[convIdx].title = autoTitle
        }
      }

      return res
    } catch (err) {
      // Đánh dấu lỗi trên tin nhắn tạm thời
      optimisticMsg.is_error = true
      optimisticMsg.error_text = err.message || 'Lỗi gửi tin nhắn'
      this.chatError = err.message || 'Không thể gửi tin nhắn'
      throw err
    } finally {
      this.sendingMessage = false
    }
  },

  async respondApproval(dialogueId, action) {
    this.respondingApproval = true
    try {
      const res = await respondChatApprovalApi(dialogueId, action)
      // Cập nhật trạng thái hiển thị trong thread hiện tại
      if (this.activeConversationId && this.messagesMap[this.activeConversationId]) {
        const msg = this.messagesMap[this.activeConversationId].find((m) => m.id === dialogueId)
        if (msg) {
          msg.approval_status = res.new_status || (action === 'APPROVE' ? 'APPROVED' : 'REJECTED')
        }
        // Thêm tin nhắn xác nhận của Governor vào thread
        if (res.message) {
          this.messagesMap[this.activeConversationId].push({
            id: res.confirmation_message_id || Date.now(),
            conversation_id: this.activeConversationId,
            sender: 'GOVERNOR',
            target_agent: 'GOVERNOR',
            message_type: 'TEXT',
            content: res.message,
            timestamp: new Date().toISOString(),
          })
        }
      }
      return res
    } catch (err) {
      this.chatError = err.message || 'Lỗi xử lý phản hồi phê duyệt'
      throw err
    } finally {
      this.respondingApproval = false
    }
  },

  async exportConversation(conversationId) {
    const convId = conversationId || this.activeConversationId
    if (!convId) return
    try {
      const res = await exportConversationApi(convId, 'json')
      const mdContent = res.markdown || ''

      // Tải về file markdown trực tiếp trên trình duyệt
      const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `chat_session_${convId}.md`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } catch (err) {
      this.chatError = err.message || 'Lỗi xuất khẩu cuộc trò chuyện'
    }
  },

  // Xử lý sự kiện WebSocket Real-time
  handleIncomingSocketEvent(event) {
    if (!event || !event.type) return

    // 1. Tin nhắn mới được phát sóng
    if (event.type === 'chat.message.new') {
      const convId = event.conversation_id
      if (!convId) return

      // Cập nhật messagesMap nếu cuộc trò chuyện đang được mở
      if (this.messagesMap[convId]) {
        const thread = this.messagesMap[convId]
        if (event.trader_message && !thread.some((m) => m.id === event.trader_message.id)) {
          thread.push(event.trader_message)
        }
        if (event.agent_message && !thread.some((m) => m.id === event.agent_message.id)) {
          thread.push(event.agent_message)
        }
      }

      // Cập nhật preview và unread count
      const convIdx = this.conversations.findIndex((c) => c.id === convId)
      if (convIdx !== -1) {
        this.conversations[convIdx].updated_at = new Date().toISOString()
        this.conversations[convIdx].last_message = event.agent_message || event.trader_message
        this.conversations[convIdx].message_count = (this.conversations[convIdx].message_count || 0) + 1
      }

      // Nếu widget đóng hoặc không đang xem cuộc trò chuyện này, tăng unread count và kích hoạt Toast
      if (!this.isWidgetOpen || this.activeConversationId !== convId) {
        this.unreadCount += 1
        const agentMsg = event.agent_message
        if (agentMsg) {
          const isApproval = agentMsg.message_type === 'APPROVAL_REQUEST'
          this.showToast({
            title: isApproval ? '⚠️ YÊU CẦU PHÊ DUYỆT LỆNH' : `🤖 ${agentMsg.sender || 'AI Agent'} Phản Hồi`,
            content: agentMsg.content ? (agentMsg.content.length > 90 ? agentMsg.content.substring(0, 87) + '...' : agentMsg.content) : '',
            sender: agentMsg.sender || 'GOVERNOR',
            isApproval,
            conversationId: convId,
          })
        }
      }
    }

    // 2. Phản hồi phê duyệt lệnh được cập nhật
    if (event.type === 'governor.approval_response' && event.dialogue_id) {
      if (this.activeConversationId && this.messagesMap[this.activeConversationId]) {
        const msg = this.messagesMap[this.activeConversationId].find((m) => m.id === event.dialogue_id)
        if (msg) {
          msg.approval_status = event.status
        }
      }
    }

    // 3. Phiên trò chuyện được cập nhật
    if (event.type === 'chat.session.updated' && event.conversation) {
      const convIdx = this.conversations.findIndex((c) => c.id === event.conversation.id)
      if (convIdx !== -1) {
        this.conversations[convIdx] = { ...this.conversations[convIdx], ...event.conversation }
      }
    }

    // 3. Phiên trò chuyện được tạo mới
    if (event.type === 'chat.session.created' && event.conversation) {
      if (!this.conversations.some((c) => c.id === event.conversation.id)) {
        this.conversations.unshift(event.conversation)
      }
    }

    // 4. Phiên trò chuyện bị xóa
    if (event.type === 'chat.session.deleted' && event.conversation_id) {
      this.conversations = this.conversations.filter((c) => c.id !== event.conversation_id)
      delete this.messagesMap[event.conversation_id]
      if (this.activeConversationId === event.conversation_id) {
        this.activeConversationId = this.conversations[0]?.id || null
      }
    }
  },
})
