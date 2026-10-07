<script setup>
import { computed, ref } from 'vue'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  Clock,
  Compass,
  Cpu,
  DollarSign,
  Layers,
  Lightbulb,
  Radio,
  ShieldCheck,
  Sliders,
  Target,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-vue-next'

const props = defineProps({
  candles: { type: Array, default: () => [] },
  lastPrice: { type: Number, default: null },
  timeframe: { type: String, default: 'M1' },
  news: { type: Array, default: () => [] },
  events: { type: Array, default: () => [] },
})

const emit = defineEmits(['navigate-cockpit'])

// Active tab inside Strategy view
const activeSection = ref('pipeline') // 'pipeline' | 'concepts' | 'sessions' | 'risk' | 'macro' | 'checklist'

// Interactive Checklist state for trader self-validation
const checklist = ref([
  { id: 'c1', label: 'Xác định HTF Trend / Bias trên D1 & H4 đồng thuận (D1/H4 Alignment)', done: true },
  { id: 'c2', label: 'Xác định Dealing Range H1 và POI (Order Block / FVG) nằm đúng vùng Discount (cho BUY) hoặc Premium (cho SELL)', done: true },
  { id: 'c3', label: 'Thời điểm hiện tại nằm trong phiên Kill Zone (London: 14:00-17:00 ICT hoặc New York AM: 19:00-22:00 ICT)', done: true },
  { id: 'c4', label: 'Giá trên M15 đã kiểm tra chạm vào vùng POI H1 (Tap POI: nhúng vào OB hoặc FVG)', done: false },
  { id: 'c5', label: 'Xuất hiện tín hiệu đảo chiều cấu trúc M15 CHoCH (Change of Character) tại nến đã đóng', done: false },
  { id: 'c6', label: 'Đặt Stop Loss an toàn ngoài biên POI kèm ATR Buffer, tỷ lệ tiềm năng Risk:Reward ≥ 1:2', done: false },
  { id: 'c7', label: 'Không có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) phát hành trong vòng 15-30 phút', done: true },
])

const completedChecks = computed(() => checklist.value.filter((i) => i.done).length)
const checklistProgress = computed(() => Math.round((completedChecks.value / checklist.value.length) * 100))

function toggleCheck(id) {
  const item = checklist.value.find((i) => i.id === id)
  if (item) item.done = !item.done
}

// Interactive Calculator
const calcBalance = ref(10000)
const calcRiskPct = ref(1.0)
const calcSlPoints = ref(5.0)

const calculatedLotSize = computed(() => {
  const balance = Number(calcBalance.value) || 10000
  const riskPct = Number(calcRiskPct.value) || 1.0
  const slDist = Number(calcSlPoints.value) || 5.0
  if (slDist <= 0 || balance <= 0) return '0.00'
  const riskMoney = (balance * riskPct) / 100
  // XAUUSD: 1 Lot = 100 oz. 1 point ($1.00/oz) = $100/lot.
  const lossPerLot = slDist * 100
  const lots = Math.floor((riskMoney / lossPerLot) * 100) / 100
  return Math.max(0.01, Math.min(100.0, lots)).toFixed(2)
})

const calculatedRiskMoney = computed(() => {
  const balance = Number(calcBalance.value) || 10000
  const riskPct = Number(calcRiskPct.value) || 1.0
  return ((balance * riskPct) / 100).toFixed(2)
})
</script>

<template>
  <div class="strategy-view-container">
    <!-- Top Hero Header -->
    <header class="strategy-hero">
      <div class="hero-left">
        <div class="hero-badge-strip">
          <span class="hero-tag primary"><BrainCircuit :size="13" /> SMC / ICT MULTI-TIMEFRAME ENGINE</span>
          <span class="hero-tag"><Activity :size="12" /> ASSET: XAUUSD (GOLD)</span>
          <span class="hero-tag green"><ShieldCheck :size="12" /> RULE-BASED · NO-LOOKAHEAD</span>
        </div>
        <h1>Chiến Lược Giao Dịch &amp; Khung Phân Tích Kỹ Thuật</h1>
        <p class="hero-desc">
          Mô hình phân tích hành động giá theo dòng tiền tổ chức (Smart Money Concepts), kết hợp cấu trúc thị trường đa khung thời gian
          <strong>D1/H4 &rarr; H1 &rarr; M15</strong>, xác định vùng mất cân bằng thanh khoản (FVG), khối lệnh (Order Block) và giao dịch trong các phiên thanh khoản cao (Kill Zones).
        </p>
      </div>

      <div class="hero-metrics">
        <div class="metric-card">
          <small>KHUNG THỜI GIAN</small>
          <strong>D1 &middot; H4 &middot; H1 &middot; M15</strong>
          <span>Phân tích Top-Down</span>
        </div>
        <div class="metric-card">
          <small>TỶ LỆ R:R MỤC TIÊU</small>
          <strong class="text-green">&ge; 1 : 2.0 (Target 1:3)</strong>
          <span>Tối ưu Risk/Reward</span>
        </div>
        <div class="metric-card">
          <small>RỦI RO / LỆNH</small>
          <strong class="text-gold">0.5% &ndash; 1.0% Vốn</strong>
          <span>Dynamic Lot Sizing</span>
        </div>
        <div class="metric-card">
          <small>PHIÊN ƯU TIÊN</small>
          <strong>London &amp; NY AM</strong>
          <span>Kill Zone Windows</span>
        </div>
      </div>
    </header>

    <!-- Sub Navigation Tabs -->
    <nav class="strategy-subnav" role="tablist" aria-label="Strategy sections">
      <button
        role="tab"
        :class="['subnav-btn', { active: activeSection === 'pipeline' }]"
        @click="activeSection = 'pipeline'"
      >
        <Layers :size="14" />
        <span>1. Quy trình Đa khung thời gian</span>
      </button>

      <button
        role="tab"
        :class="['subnav-btn', { active: activeSection === 'concepts' }]"
        @click="activeSection = 'concepts'"
      >
        <BookOpen :size="14" />
        <span>2. Thư viện Khái niệm SMC</span>
      </button>

      <button
        role="tab"
        :class="['subnav-btn', { active: activeSection === 'sessions' }]"
        @click="activeSection = 'sessions'"
      >
        <Clock :size="14" />
        <span>3. Khung giờ vàng (Kill Zones)</span>
      </button>

      <button
        role="tab"
        :class="['subnav-btn', { active: activeSection === 'risk' }]"
        @click="activeSection = 'risk'"
      >
        <ShieldCheck :size="14" />
        <span>4. Quản trị Rủi ro &amp; Vốn</span>
      </button>

      <button
        role="tab"
        :class="['subnav-btn', { active: activeSection === 'macro' }]"
        @click="activeSection = 'macro'"
      >
        <Zap :size="14" />
        <span>5. Bộ lọc Tin tức &amp; Bối cảnh</span>
      </button>

      <button
        role="tab"
        :class="['subnav-btn', { active: activeSection === 'checklist' }]"
        @click="activeSection = 'checklist'"
      >
        <Target :size="14" />
        <span>6. Checklist Vào lệnh ({{ completedChecks }}/{{ checklist.length }})</span>
      </button>
    </nav>

    <!-- TAB 1: MULTI-TIMEFRAME PIPELINE -->
    <section v-if="activeSection === 'pipeline'" class="section-pane">
      <div class="pane-header">
        <div>
          <h2>Quy trình Phân tích Top-Down Đa Khung Thời Gian</h2>
          <p>Luồng thực thi tuần tự từ bao quát xu hướng vĩ mô đến điểm kích hoạt vào lệnh chuẩn xác</p>
        </div>
        <button class="action-btn" @click="emit('navigate-cockpit')">
          <span>Mở Trading Cockpit</span>
          <ArrowRight :size="13" />
        </button>
      </div>

      <div class="pipeline-grid">
        <!-- Step 1 -->
        <article class="pipeline-card step-1">
          <div class="card-step-badge">BƯỚC 1 &middot; HTF BIAS</div>
          <div class="card-title-row">
            <span class="tf-pill">D1 &amp; H4</span>
            <h3>Xác định Xu Hướng Vĩ Mô (Higher Timeframe Bias)</h3>
          </div>
          <p class="card-desc">
            Sử dụng thuật toán Fractal Swing (Left=3, Right=3) để xác định đỉnh/đáy then chốt. Nến đóng cửa vượt qua Swing Level sẽ tạo thành BOS hoặc CHoCH.
          </p>
          <ul class="step-features">
            <li>
              <b>Đồng thuận xu hướng (D1/H4 Alignment):</b> Chỉ giao dịch khi cả D1 và H4 cùng cho tín hiệu cùng chiều (cùng Bullish hoặc Bearish).
            </li>
            <li>
              <b>Bộ lọc No-Lookahead:</b> Điểm Swing chỉ được xác nhận sau khi nến thứ 3 bên phải đã đóng, loại bỏ hoàn toàn sai số vẽ lại trong backtest.
            </li>
            <li>
              <b>Trạng thái trung lập:</b> Nếu D1 và H4 xung đột hướng &rarr; Đứng ngoài quan sát, không mở vị thế mới.
            </li>
          </ul>
          <div class="card-footer-tip">
            <Lightbulb :size="13" />
            <span>Mục tiêu: Đảm bảo lệnh luôn bơi thuận chiều với cá mập tổ chức trên khung lớn.</span>
          </div>
        </article>

        <!-- Step 2 -->
        <article class="pipeline-card step-2">
          <div class="card-step-badge">BƯỚC 2 &middot; POI SELECTION</div>
          <div class="card-title-row">
            <span class="tf-pill">H1</span>
            <h3>Định vị Vùng Quan Tâm (Point of Interest &amp; Dealing Range)</h3>
          </div>
          <p class="card-desc">
            Xác định biên độ sóng hiện tại (Dealing Range) và phân đôi thành hai vùng giá trị qua ngưỡng Equilibrium (50%).
          </p>
          <ul class="step-features">
            <li>
              <b>Nguyên lý Premium / Discount:</b> Lệnh BUY chỉ được tìm kiếm ở vùng <em>Discount</em> (dưới 50%); Lệnh SELL chỉ được tìm kiếm ở vùng <em>Premium</em> (trên 50%).
            </li>
            <li>
              <b>Order Block (OB):</b> Nhận diện khối nến tổ chức cuối cùng tại chân sóng displacement gây ra sự phá vỡ cấu trúc BOS.
            </li>
            <li>
              <b>Fair Value Gap (FVG):</b> Nhận diện vùng mất cân bằng thanh khoản 3 nến với biên độ gap &ge; <code>0.3 &times; ATR(14)</code>.
            </li>
            <li>
              <b>Kiểm tra tính hợp lệ:</b> Tự động hủy (Invalidate) các vùng POI nếu giá đã đóng cửa xuyên qua cạnh xa của vùng, hoặc vùng đã quá số lượng nến tối đa.
            </li>
          </ul>
          <div class="card-footer-tip">
            <Lightbulb :size="13" />
            <span>Mục tiêu: Mua rẻ ở Discount, bán đắt ở Premium tại các vùng khối lượng tổ chức chờ sẵn.</span>
          </div>
        </article>

        <!-- Step 3 -->
        <article class="pipeline-card step-3">
          <div class="card-step-badge">BƯỚC 3 &middot; TRIGGER &amp; ENTRY</div>
          <div class="card-title-row">
            <span class="tf-pill">M15</span>
            <h3>Kích Hoạt Khớp Lệnh &amp; Tỷ Lệ R:R (Execution Trigger)</h3>
          </div>
          <p class="card-desc">
            Chờ đợi giá hồi quy về kiểm tra (tap) vùng POI H1 và xuất hiện xác nhận đảo chiều nội tại trên khung M15.
          </p>
          <ul class="step-features">
            <li>
              <b>Kiểm tra Tap POI:</b> Giá quét râu vào trong vùng Order Block hoặc FVG của H1 nhưng không được đóng cửa phá vỡ vùng.
            </li>
            <li>
              <b>M15 CHoCH Trigger:</b> Nến M15 vừa đóng cửa tạo tín hiệu Change of Character cùng hướng với Bias HTF.
            </li>
            <li>
              <b>Lọc theo Kill Zone:</b> Tín hiệu chỉ có hiệu lực khi rơi vào các khung giờ vàng thanh khoản cao (London Kill Zone hoặc NY AM Kill Zone).
            </li>
            <li>
              <b>Tỷ lệ R:R tối thiểu &ge; 1:2:</b> Stop Loss đặt ngoài biên nến M15 + bộ đệm ATR buffer; Take Profit đặt tại các đỉnh/đáy H1 đối diện.
            </li>
          </ul>
          <div class="card-footer-tip">
            <Lightbulb :size="13" />
            <span>Mục tiêu: Tối thiểu hóa rủi ro râu nến và tối đa hóa xác suất thắng lợi trước khi nổ súng.</span>
          </div>
        </article>
      </div>
    </section>

    <!-- TAB 2: SMC MECHANICS LIBRARY -->
    <section v-if="activeSection === 'concepts'" class="section-pane">
      <div class="pane-header">
        <div>
          <h2>Thư Viện Kiến Thức &amp; Cơ Chế Smart Money Concepts (SMC)</h2>
          <p>Chi tiết định nghĩa toán học và quy tắc nhận diện hình thái nến được lập trình trong hệ thống</p>
        </div>
      </div>

      <div class="concepts-grid">
        <!-- Concept 1: BOS -->
        <div class="concept-box">
          <div class="concept-head">
            <span class="concept-icon"><TrendingUp :size="16" /></span>
            <div>
              <h4>BOS &ndash; Break of Structure (Phá vỡ cấu trúc)</h4>
              <small>Tiếp diễn xu hướng dòng tiền</small>
            </div>
          </div>
          <p>
            Xảy ra khi nến <strong>đóng cửa vượt qua</strong> đỉnh Swing High gần nhất (trong xu hướng tăng) hoặc đáy Swing Low gần nhất (trong xu hướng giảm).
          </p>
          <div class="concept-detail">
            <strong>Quy tắc xác nhận:</strong> Không chấp nhận chỉ quét râu (wick). Thân nến bắt buộc phải đóng cửa dứt khoát ra ngoài swing fractal. BOS xác nhận bên mua hoặc bên bán tiếp tục áp đảo thị trường.
          </div>
        </div>

        <!-- Concept 2: CHoCH -->
        <div class="concept-box highlight">
          <div class="concept-head">
            <span class="concept-icon"><Compass :size="16" /></span>
            <div>
              <h4>CHoCH &ndash; Change of Character (Đổi tính chất)</h4>
              <small>Dấu hiệu sớm của sự đảo chiều xu hướng</small>
            </div>
          </div>
          <p>
            Xảy ra khi giá phá vỡ mức swing trái ngược với xu hướng hiện tại. Ví dụ: đang trong cấu trúc giảm (Lower Lows/Lower Highs), giá bất ngờ đóng cửa vượt đỉnh gần nhất.
          </p>
          <div class="concept-detail">
            <strong>Ứng dụng trigger:</strong> Trong chiến lược của hệ thống, M15 CHoCH là điều kiện bắt buộc tại bước cuối để xác nhận rằng lực phản ứng tại vùng POI H1 đã đủ mạnh để đảo chiều sóng nội phiên.
          </div>
        </div>

        <!-- Concept 3: Order Block -->
        <div class="concept-box">
          <div class="concept-head">
            <span class="concept-icon"><Layers :size="16" /></span>
            <div>
              <h4>Order Block &ndash; Khối Lệnh Tổ Chức</h4>
              <small>Vùng hấp thụ thanh khoản của Smart Money</small>
            </div>
          </div>
          <p>
            Là cây nến ngược hướng cuối cùng tại đáy (đối với Bullish OB) hoặc đỉnh (đối với Bearish OB) của đợt sóng displacement tạo ra sự phá vỡ cấu trúc BOS/CHoCH.
          </p>
          <div class="concept-detail">
            <strong>Biên độ vùng:</strong> Top = High của cây nến OB, Bottom = Low của cây nến OB. Vùng giữ nguyên giá trị cho tới khi có nến đóng cửa xuyên qua cạnh đối diện.
          </div>
        </div>

        <!-- Concept 4: Fair Value Gap -->
        <div class="concept-box">
          <div class="concept-head">
            <span class="concept-icon"><Zap :size="16" /></span>
            <div>
              <h4>Fair Value Gap (FVG) &ndash; Mất Cân Bằng Thanh Khoản</h4>
              <small>Vùng Imbalance hình thành từ 3 nến liên tiếp</small>
            </div>
          </div>
          <p>
            Xuất hiện khi có một bước giá dịch chuyển quá nhanh (Imbalance) khiến bên mua hoặc bên bán không kịp khớp lệnh đối ứng:
          </p>
          <div class="concept-detail">
            <strong>Công thức tính:</strong>
            <code>Bullish FVG: Low[nến 3] &gt; High[nến 1] &amp;&amp; (Low[3] - High[1]) &ge; 0.3 &times; ATR</code><br />
            <code>Bearish FVG: High[nến 3] &lt; Low[nến 1] &amp;&amp; (Low[1] - High[3]) &ge; 0.3 &times; ATR</code>
          </div>
        </div>

        <!-- Concept 5: Dealing Range -->
        <div class="concept-box">
          <div class="concept-head">
            <span class="concept-icon"><Sliders :size="16" /></span>
            <div>
              <h4>Premium &amp; Discount &ndash; Vùng Định Giá</h4>
              <small>Nguyên lý định giá sóng giao dịch</small>
            </div>
          </div>
          <p>
            Được xác định dựa trên ngưỡng cân bằng 50% Equilibrium giữa Đỉnh sóng (Swing High) và Đáy sóng (Swing Low) hiện hành.
          </p>
          <div class="concept-detail">
            <strong>Quy tắc hệ thống:</strong> Tuyệt đối không bao giờ mua khi giá nằm trên ngưỡng 50% (Premium); Tuyệt đối không bao giờ bán khống khi giá nằm dưới ngưỡng 50% (Discount).
          </div>
        </div>

        <!-- Concept 6: Liquidity Sweeps -->
        <div class="concept-box">
          <div class="concept-head">
            <span class="concept-icon"><Target :size="16" /></span>
            <div>
              <h4>Liquidity Sweep &ndash; Quét Thanh Khoản Đỉnh/Đáy</h4>
              <small>Bẫy giá (Fakeout / Stop Hunt) của thị trường</small>
            </div>
          </div>
          <p>
            Xảy ra khi giá phóng râu nến (wick) vượt qua mức Swing cũ để kích hoạt lệnh Stop Loss và Buy/Sell Stop của số đông, nhưng <strong>giá đóng cửa lập tức rút ngược trở lại</strong> bên trong.
          </p>
          <div class="concept-detail">
            <strong>Ý nghĩa:</strong> Cung cấp nguồn thanh khoản dồi dào để các quỹ tổ chức hoàn tất việc gom/xả hàng trước khi đổi hướng thị trường.
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 3: KILL ZONES & SESSIONS -->
    <section v-if="activeSection === 'sessions'" class="section-pane">
      <div class="pane-header">
        <div>
          <h2>Khung Giờ Vàng Giao Dịch (ICT Kill Zones)</h2>
          <p>Thời điểm biến động mạnh nhất và dòng tiền tổ chức tham gia thị trường XAUUSD tích cực nhất</p>
        </div>
      </div>

      <div class="sessions-wrapper">
        <div class="sessions-table-container">
          <table class="strategy-table">
            <thead>
              <tr>
                <th>PHIÊN / KILL ZONE</th>
                <th>GIỜ NEW YORK (EST/EDT)</th>
                <th>GIỜ VIỆT NAM (ICT - UTC+7)</th>
                <th>MỨC ĐỘ BIẾN ĐỘNG</th>
                <th>ĐẶC ĐIỂM CHIẾN LƯỢC</th>
              </tr>
            </thead>
            <tbody>
              <tr class="highlight-row">
                <td>
                  <div class="session-name">
                    <span class="dot green"></span>
                    <strong>London Kill Zone</strong>
                  </div>
                </td>
                <td><code>02:00 &ndash; 05:00 NY</code></td>
                <td><b class="text-green">13:00 / 14:00 &ndash; 16:00 / 17:00 ICT</b></td>
                <td><span class="badge high">Cao &middot; &starf;&starf;&starf;</span></td>
                <td>Phiên mở cửa châu Âu. Thường hình thành bẫy giá Judas Swing quét thanh khoản phiên Á trước khi tạo đáy/đỉnh thật của ngày.</td>
              </tr>
              <tr class="highlight-row prime">
                <td>
                  <div class="session-name">
                    <span class="dot gold"></span>
                    <strong>New York AM Kill Zone</strong>
                  </div>
                </td>
                <td><code>07:00 &ndash; 10:00 NY</code></td>
                <td><b class="text-gold">18:00 / 19:00 &ndash; 21:00 / 22:00 ICT</b></td>
                <td><span class="badge prime">Cực Cao &middot; &starf;&starf;&starf;&starf;</span></td>
                <td>Phiên sôi động nhất với Vàng (XAUUSD). Trùng thời điểm công bố tin tức vĩ mô quan trọng của Mỹ (CPI, NFP, Retail Sales, GDP).</td>
              </tr>
              <tr>
                <td>
                  <div class="session-name">
                    <span class="dot blue"></span>
                    <strong>New York PM Kill Zone</strong>
                  </div>
                </td>
                <td><code>13:30 &ndash; 16:00 NY</code></td>
                <td><b>00:30 / 01:30 &ndash; 03:00 / 04:00 ICT</b></td>
                <td><span class="badge medium">Trung Bình &middot; &starf;&starf;</span></td>
                <td>Chốt lời và đóng vị thế phiên Mỹ. Khối lượng giao dịch giảm dần trước khi thị trường bước vào phiên giao dịch châu Á.</td>
              </tr>
              <tr>
                <td>
                  <div class="session-name">
                    <span class="dot purple"></span>
                    <strong>ICT Silver Bullet Windows</strong>
                  </div>
                </td>
                <td><code>03:00-04:00 | 10:00-11:00 | 14:00-15:00</code></td>
                <td><b>14:00-15:00 | 21:00-22:00 | 01:00-02:00 ICT</b></td>
                <td><span class="badge high">Chuẩn Xác &middot; &starf;&starf;&starf;</span></td>
                <td>Khung 60 phút vàng. Giá thường tìm kiếm FVG gần nhất để hoàn tất nhịp di chuyển 10-20 points trong ngày.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="dst-notice">
          <Clock :size="16" />
          <div>
            <strong>Cơ chế tự động xử lý giờ mùa hè (DST - Daylight Saving Time):</strong>
            <p>
              Hệ thống sử dụng thư viện múi giờ chuẩn IANA <code>America/New_York</code> (thông qua module <code>zoneinfo</code>) để tự động căn chỉnh giờ mở phiên chính xác giữa mùa hè (EDT: chênh 11 tiếng so với ICT) và mùa đông (EST: chênh 12 tiếng so với ICT).
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 4: RISK MANAGEMENT MATRIX -->
    <section v-if="activeSection === 'risk'" class="section-pane">
      <div class="pane-header">
        <div>
          <h2>Ma Trận Quản Trị Rủi Ro &amp; Quản Lý Vốn (Risk Management)</h2>
          <p>Nguyên tắc bảo toàn vốn nghiêm ngặt được thực thi tự động qua động cơ Risk Checker</p>
        </div>
      </div>

      <div class="risk-grid">
        <!-- Interactive Position Sizing Calculator -->
        <div class="calculator-card">
          <div class="calc-header">
            <DollarSign :size="16" />
            <h3>Công Cụ Tính Lot Tự Động (Position Sizing)</h3>
          </div>
          <p class="calc-sub">Dựa trên công thức toán học thực tế được tích hợp trong <code>risk_checker.py</code></p>

          <div class="calc-inputs">
            <div class="input-field">
              <label>Số dư tài khoản ($):</label>
              <input v-model.number="calcBalance" type="number" step="500" min="100" />
            </div>

            <div class="input-field">
              <label>Mức rủi ro / lệnh (%):</label>
              <input v-model.number="calcRiskPct" type="number" step="0.1" min="0.1" max="5" />
            </div>

            <div class="input-field">
              <label>Khoảng cách Stop Loss ($ / point):</label>
              <input v-model.number="calcSlPoints" type="number" step="0.5" min="0.5" max="50" />
            </div>
          </div>

          <div class="calc-result-box">
            <div class="result-row">
              <span>Số tiền chấp nhận rủi ro:</span>
              <strong>${{ calculatedRiskMoney }}</strong>
            </div>
            <div class="result-row highlight">
              <span>Khối lượng vào lệnh tối ưu:</span>
              <strong class="lot-val">{{ calculatedLotSize }} LOT</strong>
            </div>
          </div>
        </div>

        <!-- Risk Principles -->
        <div class="risk-rules-box">
          <h3>Các Giới Hạn Bảo Vệ Tài Khoản Cốt Lõi</h3>
          <div class="rule-items">
            <div class="rule-card">
              <span class="rule-num">1</span>
              <div>
                <strong>Giới hạn sụt giảm tối đa trong ngày (Daily Loss Cut-off):</strong>
                <p>Nếu tổng mức thua lỗ trong 1 ngày chạm ngưỡng <b>&ge; 5.0%</b> vốn tài khoản, hệ thống sẽ kích hoạt lệnh ngắt khẩn cấp và từ chối toàn bộ lệnh mới trong ngày hôm đó.</p>
              </div>
            </div>

            <div class="rule-card">
              <span class="rule-num">2</span>
              <div>
                <strong>Bộ đệm Stop Loss Buffer (ATR Protection):</strong>
                <p>Khoảng cách Stop Loss không được đặt quá sát mép Order Block. Hệ thống tự động cộng thêm bộ đệm <code>buf = 0.2 &times; ATR(M15)</code> để phòng chống hiện tượng trượt giá (slippage) và cắn râu bất thường.</p>
              </div>
            </div>

            <div class="rule-card">
              <span class="rule-num">3</span>
              <div>
                <strong>Tỷ lệ Risk : Reward tối thiểu (Min R:R = 1:2):</strong>
                <p>Bất kỳ tín hiệu nào có tiềm năng lợi nhuận so với rủi ro nhỏ hơn 1:2 đều bị loại bỏ ngay từ khâu lọc tín hiệu. Mục tiêu tiêu chuẩn được thiết lập ở mức 1:3 hoặc đỉnh/đáy H1 đối diện.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 5: MACRO NEWS GUARD -->
    <section v-if="activeSection === 'macro'" class="section-pane">
      <div class="pane-header">
        <div>
          <h2>Bộ Lọc Tin Tức Vĩ Mô &amp; Điều Tiết Biến Động (Macro News Guard)</h2>
          <p>Cơ chế phòng thủ bảo vệ tài khoản trước các cú sốc thanh khoản và tin tức đột biến</p>
        </div>
      </div>

      <div class="macro-grid">
        <div class="macro-card">
          <div class="macro-head">
            <AlertTriangle :size="16" />
            <h3>Chế Độ Circuit Breaker (Tạm Dừng Khi Có Tin Đỏ 3 Sao)</h3>
          </div>
          <p>
            Hệ thống tích hợp bộ lọc từ 4 nguồn cấp dữ liệu lịch kinh tế thời gian thực. Khi có sự kiện kinh tế tác động cao (★★★) thuộc đồng USD (như <strong>CPI, Non-Farm Payrolls, Lãi suất FOMC, GDP</strong>):
          </p>
          <ul class="macro-bullets">
            <li>Động cơ tự động gán trạng thái <code>trading_allowed = False</code>.</li>
            <li>Toàn bộ lệnh mở mới bị khóa tạm thời trong vùng thời gian diễn ra sự kiện để tránh trượt giá (slippage) và chênh lệch spread ECN bị giãn nở cực đại.</li>
            <li>Các lệnh đang mở được theo dõi chặt chẽ theo trailing stop hoặc cảnh báo chốt lời từng phần.</li>
          </ul>
        </div>

        <div class="macro-card">
          <div class="macro-head">
            <Sliders :size="16" />
            <h3>Thích Ứng Độ Biến Động ATR (Dynamic Volatility Advisor)</h3>
          </div>
          <p>
            Đo lường tỷ lệ biến động thực tế so với ngưỡng trung bình chuẩn thông qua tỷ lệ <code>Volatility Ratio = ATR / Baseline ATR</code>:
          </p>
          <div class="volatility-tiers">
            <div class="tier-item danger">
              <span class="tier-label">TỶ LỆ &ge; 1.8 (Biến động cực đoan)</span>
              <p>Giảm 50% khối lượng giao dịch (Lot Size halved) và nới rộng khoảng cách Stop Loss 1.5x.</p>
            </div>
            <div class="tier-item warning">
              <span class="tier-label">TỶ LỆ 1.3 &ndash; 1.7 (Biến động trên trung bình)</span>
              <p>Giảm 25% khối lượng giao dịch và nới rộng khoảng cách Stop Loss 1.25x.</p>
            </div>
            <div class="tier-item normal">
              <span class="tier-label">TỶ LỆ &lt; 1.3 (Biến động ổn định)</span>
              <p>Duy trì 100% tham số giao dịch theo quy chuẩn chuẩn hóa.</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 6: INTERACTIVE CHECKLIST -->
    <section v-if="activeSection === 'checklist'" class="section-pane">
      <div class="pane-header">
        <div>
          <h2>Checklist Kiểm Tra Điều Kiện Vào Lệnh Thực Tế</h2>
          <p>Danh sách tiêu chuẩn vàng trước khi thực hiện bất kỳ lệnh mua hoặc bán nào trên cặp XAUUSD</p>
        </div>
        <div class="progress-indicator">
          <span>Tiến độ kiểm tra: <b>{{ checklistProgress }}%</b></span>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${checklistProgress}%` }"></div>
          </div>
        </div>
      </div>

      <div class="checklist-container">
        <div
          v-for="item in checklist"
          :key="item.id"
          :class="['check-item', { checked: item.done }]"
          @click="toggleCheck(item.id)"
        >
          <div class="check-box">
            <CheckCircle2 v-if="item.done" :size="16" />
            <span v-else class="empty-circle"></span>
          </div>
          <span class="check-text">{{ item.label }}</span>
        </div>
      </div>

      <div class="checklist-footer">
        <div v-if="checklistProgress === 100" class="ready-banner success">
          <CheckCircle2 :size="18" />
          <span>ĐỦ ĐIỀU KIỆN! Tất cả tiêu chí chiến lược SMC đã được thỏa mãn đầy đủ. Hệ thống sẵn sàng mở vị thế.</span>
        </div>
        <div v-else class="ready-banner waiting">
          <Clock :size="18" />
          <span>CHƯA ĐỦ ĐIỀU KIỆN. Vui lòng kiên nhẫn chờ đợi thị trường đáp ứng đầy đủ 100% các tiêu chí trên.</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.strategy-view-container {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px 0 32px;
}

/* Hero Header */
.strategy-hero {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
  background: #f8faf6;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  padding: 20px 22px;
}

.hero-badge-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #e9eee7;
  color: #4a5c50;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.hero-tag.primary {
  background: #225c43;
  color: #c9f06b;
}

.hero-tag.green {
  background: #e2ede0;
  color: #276949;
}

h1 {
  margin: 0 0 8px;
  font-size: 19px;
  font-weight: 800;
  color: #1b2a23;
  letter-spacing: -0.01em;
}

.hero-desc {
  margin: 0;
  color: #55675c;
  font-size: 12px;
  line-height: 1.6;
}

.hero-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.metric-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: #ffffff;
  border: 1px solid #e1e7df;
  border-radius: 6px;
  padding: 10px 12px;
}

.metric-card small {
  font: 8px 'DM Mono', monospace;
  color: #839186;
  font-weight: 700;
  text-transform: uppercase;
}

.metric-card strong {
  font: 13px 'DM Mono', monospace;
  color: #223328;
  margin: 3px 0 2px;
}

.metric-card span {
  font-size: 9px;
  color: #6c7c71;
}

.text-green {
  color: #2e7a52 !important;
}

.text-gold {
  color: #9c6c1f !important;
}

/* Sub-Navigation */
.strategy-subnav {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.subnav-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 36px;
  padding: 0 13px;
  border: 1px solid #d4ded3;
  border-radius: 6px;
  background: #f8faf6;
  color: #4a5c50;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.subnav-btn:hover {
  background: #e8efe6;
  color: #1f4733;
}

.subnav-btn.active {
  background: #225c43;
  color: #ffffff;
  border-color: #225c43;
  box-shadow: 0 1px 3px rgba(34, 92, 67, 0.2);
}

/* Section Panes */
.section-pane {
  background: #f8faf6;
  border: 1px solid #d5ded6;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.pane-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e7ede5;
  padding-bottom: 12px;
}

.pane-header h2 {
  margin: 0 0 3px;
  font-size: 15px;
  color: #1b2a23;
  font-weight: 800;
}

.pane-header p {
  margin: 0;
  font-size: 11px;
  color: #6a7c70;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  background: #e7ede5;
  border: 1px solid #c9d6c7;
  border-radius: 5px;
  color: #225c43;
  font: 10px 'DM Mono', monospace;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: #225c43;
  color: #ffffff;
}

/* Pipeline Grid */
.pipeline-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.pipeline-card {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 7px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
}

.card-step-badge {
  font: 8px 'DM Mono', monospace;
  font-weight: 800;
  color: #225c43;
  background: #e3ede1;
  padding: 2px 7px;
  border-radius: 3px;
  width: fit-content;
  letter-spacing: 0.04em;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tf-pill {
  font: 10px 'DM Mono', monospace;
  font-weight: 700;
  background: #225c43;
  color: #c9f06b;
  padding: 2px 6px;
  border-radius: 4px;
}

.card-title-row h3 {
  margin: 0;
  font-size: 12px;
  color: #1b2a23;
  line-height: 1.35;
}

.card-desc {
  margin: 0;
  font-size: 11px;
  color: #58685d;
  line-height: 1.5;
}

.step-features {
  margin: 0;
  padding-left: 16px;
  font-size: 10px;
  color: #4a5c50;
  line-height: 1.6;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.card-footer-tip {
  margin-top: auto;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  background: #f4f8f3;
  border-left: 2px solid #5a996f;
  padding: 7px 9px;
  border-radius: 0 4px 4px 0;
  color: #3b5e47;
  font-size: 10px;
  line-height: 1.4;
}

/* Concepts Grid */
.concepts-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.concept-box {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 6px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.concept-box.highlight {
  border-color: #8bc39b;
  box-shadow: 0 1px 4px rgba(34, 92, 67, 0.08);
}

.concept-head {
  display: flex;
  align-items: center;
  gap: 9px;
}

.concept-icon {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: #eaf1e9;
  color: #225c43;
}

.concept-head h4 {
  margin: 0;
  font-size: 11px;
  font-weight: 700;
  color: #203126;
}

.concept-head small {
  color: #7b8b7f;
  font-size: 9px;
}

.concept-box p {
  margin: 0;
  font-size: 10px;
  color: #536458;
  line-height: 1.55;
}

.concept-detail {
  margin-top: auto;
  background: #f7faf6;
  border-radius: 4px;
  padding: 7px 9px;
  font-size: 9.5px;
  color: #384f40;
  line-height: 1.45;
}

.concept-detail code {
  font: 9px 'DM Mono', monospace;
  color: #1e4f35;
  font-weight: 600;
}

/* Sessions Table */
.strategy-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  background: #ffffff;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #dce4da;
}

.strategy-table th {
  background: #eef3ed;
  text-align: left;
  padding: 10px 12px;
  font: 9px 'DM Mono', monospace;
  color: #55675c;
  font-weight: 700;
  border-bottom: 1px solid #d8e2d6;
}

.strategy-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #edf2ec;
  color: #394a3e;
}

.session-name {
  display: flex;
  align-items: center;
  gap: 7px;
}

.session-name .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.session-name .dot.green { background: #358b5a; }
.session-name .dot.gold { background: #d08c2a; }
.session-name .dot.blue { background: #3d79b8; }
.session-name .dot.purple { background: #8852ab; }

.highlight-row {
  background: #fbfdfb;
}

.highlight-row.prime {
  background: #fffdf8;
}

.badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  font: 9px 'DM Mono', monospace;
  font-weight: 700;
}

.badge.high { background: #e3ede1; color: #2a6f47; }
.badge.prime { background: #faecd6; color: #9c6014; }
.badge.medium { background: #e7eef7; color: #2e5f96; }

.dst-notice {
  margin-top: 12px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: #f5f8f4;
  border: 1px solid #d7e2d5;
  border-radius: 6px;
  padding: 10px 13px;
  color: #43594b;
  font-size: 11px;
}

.dst-notice p {
  margin: 3px 0 0;
  font-size: 10px;
  color: #637769;
}

/* Risk Grid */
.risk-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 18px;
}

.calculator-card {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 7px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.calc-header {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #225c43;
}

.calc-header h3 {
  margin: 0;
  font-size: 12px;
  font-weight: 800;
}

.calc-sub {
  margin: -6px 0 0;
  font-size: 10px;
  color: #798b7e;
}

.calc-inputs {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.input-field label {
  font-size: 10px;
  font-weight: 600;
  color: #495a4f;
}

.input-field input {
  height: 28px;
  padding: 0 8px;
  border: 1px solid #ccd8ca;
  border-radius: 4px;
  font: 11px 'DM Mono', monospace;
  background: #fbfdfa;
}

.calc-result-box {
  margin-top: auto;
  background: #f2f7f1;
  border: 1px solid #cfdecd;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  color: #54685a;
}

.result-row strong {
  font: 11px 'DM Mono', monospace;
  color: #203126;
}

.result-row.highlight {
  border-top: 1px dashed #c0d3be;
  padding-top: 6px;
  margin-top: 2px;
}

.lot-val {
  font-size: 14px !important;
  color: #225c43 !important;
  font-weight: 800;
}

.risk-rules-box {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 7px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-rules-box h3 {
  margin: 0;
  font-size: 13px;
  color: #1b2a23;
  font-weight: 800;
}

.rule-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rule-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  background: #f9fbf8;
  border-radius: 6px;
  border: 1px solid #e7efe5;
}

.rule-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #225c43;
  color: #c9f06b;
  display: grid;
  place-items: center;
  font: 10px 'DM Mono', monospace;
  font-weight: 800;
  flex-shrink: 0;
}

.rule-card strong {
  display: block;
  font-size: 11px;
  color: #23362a;
  margin-bottom: 2px;
}

.rule-card p {
  margin: 0;
  font-size: 10.5px;
  color: #5b6f62;
  line-height: 1.5;
}

/* Macro Grid */
.macro-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.macro-card {
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 7px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.macro-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9c6014;
}

.macro-head h3 {
  margin: 0;
  font-size: 12px;
  color: #213227;
  font-weight: 800;
}

.macro-card p {
  margin: 0;
  font-size: 11px;
  color: #55675c;
  line-height: 1.55;
}

.macro-bullets {
  margin: 0;
  padding-left: 16px;
  font-size: 10px;
  color: #4a5c50;
  display: flex;
  flex-direction: column;
  gap: 6px;
  line-height: 1.5;
}

.volatility-tiers {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.tier-item {
  padding: 8px 10px;
  border-radius: 5px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tier-item.danger {
  background: #fcf1ef;
  border-left: 3px solid #d4513b;
}

.tier-item.warning {
  background: #fdf5ea;
  border-left: 3px solid #d48f2b;
}

.tier-item.normal {
  background: #f2f7f1;
  border-left: 3px solid #4a8f60;
}

.tier-label {
  font: 9px 'DM Mono', monospace;
  font-weight: 800;
  color: #24352a;
}

.tier-item p {
  font-size: 9.5px;
  margin: 0;
}

/* Checklist Section */
.checklist-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #ffffff;
  border: 1px solid #dce4da;
  border-radius: 6px;
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.check-item:hover {
  background: #f4f8f3;
  border-color: #bad3bc;
}

.check-item.checked {
  background: #f3f9f2;
  border-color: #9fc9a4;
}

.check-box {
  color: #2a734a;
  display: grid;
  place-items: center;
}

.empty-circle {
  width: 15px;
  height: 15px;
  border: 2px solid #b7c7b5;
  border-radius: 50%;
}

.check-text {
  font-size: 11.5px;
  color: #34473b;
  font-weight: 600;
}

.check-item.checked .check-text {
  color: #1a422d;
}

.progress-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: #55675c;
}

.progress-bar {
  width: 120px;
  height: 8px;
  background: #e2eae0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #225c43;
  transition: width 0.3s ease;
}

.checklist-footer {
  margin-top: 4px;
}

.ready-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
}

.ready-banner.success {
  background: #e1f2df;
  border: 1px solid #8fc98d;
  color: #194a28;
}

.ready-banner.waiting {
  background: #fef4e5;
  border: 1px solid #f0cd95;
  color: #7d490c;
}

@media (max-width: 1024px) {
  .strategy-hero {
    grid-template-columns: 1fr;
  }
  .pipeline-grid, .concepts-grid {
    grid-template-columns: 1fr;
  }
  .risk-grid, .macro-grid {
    grid-template-columns: 1fr;
  }
}
</style>
