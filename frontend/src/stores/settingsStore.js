import { reactive } from 'vue'

const SETTINGS_KEY = 'fieldnote_user_settings'

export const settingsStore = reactive({
  // Trading Parameters
  defaultLotSize: 0.1,
  defaultStopLossOffset: 5.0,
  defaultTakeProfitOffset: 10.0,
  maxSlippagePoints: 1.0,
  confirmBeforeOrder: true,
  soundAlerts: true,

  // Display Preferences
  defaultTimeframe: 'M1',
  displayTimezone: 'ICT',
  showVolumeDefault: true,

  // Technical Indicators: EMA
  showEma: true,
  emaPeriod: 20,
  emaColor: '#eab308',

  load() {
    try {
      const raw = localStorage.getItem(SETTINGS_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed.defaultLotSize !== undefined) this.defaultLotSize = Number(parsed.defaultLotSize) || 0.1
        if (parsed.defaultStopLossOffset !== undefined) this.defaultStopLossOffset = Number(parsed.defaultStopLossOffset) || 5.0
        if (parsed.defaultTakeProfitOffset !== undefined) this.defaultTakeProfitOffset = Number(parsed.defaultTakeProfitOffset) || 10.0
        if (parsed.maxSlippagePoints !== undefined) this.maxSlippagePoints = Number(parsed.maxSlippagePoints) || 1.0
        if (parsed.confirmBeforeOrder !== undefined) this.confirmBeforeOrder = Boolean(parsed.confirmBeforeOrder)
        if (parsed.soundAlerts !== undefined) this.soundAlerts = Boolean(parsed.soundAlerts)
        if (parsed.defaultTimeframe !== undefined) this.defaultTimeframe = parsed.defaultTimeframe
        if (parsed.displayTimezone !== undefined) this.displayTimezone = parsed.displayTimezone
        if (parsed.showVolumeDefault !== undefined) this.showVolumeDefault = Boolean(parsed.showVolumeDefault)
        if (parsed.showEma !== undefined) this.showEma = Boolean(parsed.showEma)
        if (parsed.emaPeriod !== undefined) this.emaPeriod = Math.max(2, Math.min(500, parseInt(parsed.emaPeriod, 10) || 20))
        if (parsed.emaColor !== undefined) this.emaColor = parsed.emaColor
      }
    } catch (e) {
      console.warn('Failed to load settings from localStorage', e)
    }
  },

  save(data = {}) {
    Object.assign(this, data)
    try {
      const payload = {
        defaultLotSize: this.defaultLotSize,
        defaultStopLossOffset: this.defaultStopLossOffset,
        defaultTakeProfitOffset: this.defaultTakeProfitOffset,
        maxSlippagePoints: this.maxSlippagePoints,
        confirmBeforeOrder: this.confirmBeforeOrder,
        soundAlerts: this.soundAlerts,
        defaultTimeframe: this.defaultTimeframe,
        displayTimezone: this.displayTimezone,
        showVolumeDefault: this.showVolumeDefault,
        showEma: this.showEma,
        emaPeriod: this.emaPeriod,
        emaColor: this.emaColor,
      }
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(payload))
    } catch (e) {
      console.warn('Failed to save settings to localStorage', e)
    }
  },
})

// Auto-load settings on initialization
settingsStore.load()
