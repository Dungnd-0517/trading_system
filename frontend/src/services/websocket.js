export function connectMarketStream(onMessage, onStatus = () => {}) {
  const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${scheme}//${window.location.host}/api/v1/ws/market`)
  socket.addEventListener('open', () => onStatus(true))
  socket.addEventListener('close', () => onStatus(false))
  socket.addEventListener('error', () => onStatus(false))
  socket.addEventListener('message', (event) => {
    try {
      onMessage(JSON.parse(event.data))
    } catch {
      onStatus(false)
    }
  })
  return socket
}