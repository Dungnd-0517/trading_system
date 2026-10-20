/**
 * Event Bus cho kiến trúc đồng bộ thời gian thực hai chiều (Dual-Surface Real-time Synchronized Architecture)
 * Đảm bảo phân phối sự kiện decoupled giữa Pinia stores (chatStore, agentStore, orderStore)
 * và các bề mặt hiển thị (GlobalChatWidget, AIChatStudioView, GovernorDialogueConsole).
 */

class EventBus {
  constructor() {
    this.listeners = new Map()
  }

  /**
   * Đăng ký lắng nghe sự kiện
   * @param {string} event Tên sự kiện
   * @param {Function} callback Hàm callback khi nhận sự kiện
   * @returns {Function} Hàm hủy đăng ký (unsubscribe)
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event).add(callback)
    return () => this.off(event, callback)
  }

  /**
   * Lắng nghe sự kiện đúng 1 lần
   * @param {string} event Tên sự kiện
   * @param {Function} callback Hàm callback
   * @returns {Function} Hàm hủy đăng ký
   */
  once(event, callback) {
    const wrapped = (payload) => {
      this.off(event, wrapped)
      callback(payload)
    }
    return this.on(event, wrapped)
  }

  /**
   * Hủy đăng ký lắng nghe sự kiện
   * @param {string} event Tên sự kiện
   * @param {Function} [callback] Hàm callback cần gỡ bỏ (nếu null sẽ gỡ toàn bộ listeners của event)
   */
  off(event, callback) {
    if (!this.listeners.has(event)) return
    if (!callback) {
      this.listeners.delete(event)
    } else {
      this.listeners.get(event).delete(callback)
      if (this.listeners.get(event).size === 0) {
        this.listeners.delete(event)
      }
    }
  }

  /**
   * Phát sự kiện tới toàn bộ listeners đã đăng ký
   * @param {string} event Tên sự kiện
   * @param {*} [payload] Dữ liệu đính kèm
   */
  emit(event, payload) {
    if (!this.listeners.has(event)) return
    for (const callback of this.listeners.get(event)) {
      try {
        callback(payload)
      } catch (err) {
        console.error(`[EventBus] Error in listener for "${event}":`, err)
      }
    }
  }

  /**
   * Xóa toàn bộ listeners
   */
  clear() {
    this.listeners.clear()
  }
}

export const eventBus = new EventBus()
