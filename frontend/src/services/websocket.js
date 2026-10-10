export function connectMarketStream(onMessage, onStatus = () => {}) {
  let socket = null
  let reconnectTimer = null
  let isClosed = false

  function connect() {
    if (isClosed) return
    const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    socket = new WebSocket(`${scheme}//${window.location.host}/api/v1/ws/market`)

    socket.addEventListener('open', () => {
      onStatus(true)
    })

    socket.addEventListener('close', () => {
      onStatus(false)
      if (!isClosed) {
        clearTimeout(reconnectTimer)
        reconnectTimer = setTimeout(connect, 2000)
      }
    })

    socket.addEventListener('error', () => {
      onStatus(false)
      try {
        socket?.close()
      } catch {}
    })

    socket.addEventListener('message', (event) => {
      try {
        onMessage(JSON.parse(event.data))
      } catch {
        onStatus(false)
      }
    })
  }

  connect()

  return {
    close() {
      isClosed = true
      clearTimeout(reconnectTimer)
      try {
        socket?.close()
      } catch {}
    },
    get rawSocket() {
      return socket
    },
  }
}