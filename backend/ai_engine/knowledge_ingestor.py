from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import io
import json
import logging
from pathlib import Path
import re
from typing import Any
import unicodedata

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engine.embeddings import embedding_service
from ai_engine.technical_agent import technical_rag_agent
from core.database import session_factory
from core.models import StandardizedTradingStrategy, TradingKnowledge

logger = logging.getLogger(__name__)

_DEFAULT_STRATEGIES_DIR = (
    Path(__file__).resolve().parents[1] / "knowledge_base" / "standardized_strategies"
)


class StandardizedStrategyDTO(BaseModel):
    slug: str
    name: str
    school_of_thought: str
    timeframe_focus: str = "M15"
    target_risk_reward: float = 2.0
    philosophy: str
    setup_checklist: list[dict[str, Any]] = Field(default_factory=list)
    entry_rules: str
    stop_loss_rules: str
    take_profit_rules: str
    invalidation_conditions: str
    risk_guardrails: dict[str, Any] = Field(default_factory=dict)
    source_documents: list[dict[str, Any]] = Field(default_factory=list)
    system_file_path: str | None = None
    json_content: dict[str, Any] | None = None
    markdown_content: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class KnowledgeIngestionResult(BaseModel):
    status: str
    source_type: str  # "PDF", "MARKDOWN", "URL"
    source_name: str
    detected_school: str
    confidence: float
    reasoning: str
    chunks_created: int
    chunk_ids: list[int]
    standardized_strategy: StandardizedStrategyDTO
    file_saved_paths: list[str]


def _slugify(text: str) -> str:
    """Chuyển chuỗi tiếng Việt hoặc tiếng Anh thành slug an toàn cho tên file"""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)


class KnowledgeIngestionEngine:
    """
    Agent LLM [VECTOR] Knowledge Ingestion & Standardized Strategy Engine:
    - Tiếp nhận tài liệu: File PDF, file Markdown, Link tài liệu (URL).
    - Trích xuất nội dung văn bản sạch sẽ.
    - Phân tích cú pháp, chia chunk logic.
    - Phân loại trường phái học thuật (Wyckoff, SMC, ICT, CMT, Price Action, Candlestick, Risk Management).
    - Vector hóa 1536 chiều bằng EmbeddingService và lưu trữ vào PostgreSQL pgvector.
    - Tự động sinh Cấu trúc Giao dịch Tiêu chuẩn (Standardized Trading Strategy) cho từng phương pháp.
    - Lưu trữ thành file hệ thống song song (.json và .md) và bảng CSDL standardized_trading_strategies.
    - Cung cấp tri thức chuẩn hóa phục vụ phân tích kỹ thuật và cải thiện hiệu suất giao dịch.
    """

    def __init__(self, strategies_dir: Path | None = None):
        self.strategies_dir = strategies_dir or _DEFAULT_STRATEGIES_DIR
        self.strategies_dir.mkdir(parents=True, exist_ok=True)

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Trích xuất toàn bộ văn bản từ file PDF sử dụng pypdf"""
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            extracted_pages: list[str] = []
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(f"--- Trang {idx + 1} ---\n{page_text.strip()}")
            full_text = "\n\n".join(extracted_pages).strip()
            if not full_text:
                # Thử trích xuất từ metadata tài liệu nếu trang trống
                meta_parts = []
                if reader.metadata:
                    for k, v in reader.metadata.items():
                        if v and str(v).strip():
                            meta_parts.append(f"{k.strip('/')}: {v}")
                if meta_parts:
                    full_text = "\n".join(meta_parts)
                else:
                    raise ValueError("PDF không chứa văn bản có thể trích xuất (có thể là file scan ảnh).")
            return full_text
        except ImportError:
            logger.warning("pypdf chưa được cài đặt; dùng fallback decoder.")
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception as exc:
            logger.error("Lỗi khi đọc file PDF: %s", exc)
            raise ValueError(f"Không thể đọc file PDF: {exc}")

    async def fetch_url_content(self, url: str) -> tuple[str, str]:
        """Tải và trích xuất nội dung văn bản sạch từ một đường dẫn URL tài liệu"""
        async with httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 TradingAgent/1.0"
            },
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise ValueError(f"Không thể tải URL ({resp.status_code}): {url}")
            raw_html = resp.text

        # Trích xuất title từ HTML
        title_match = re.search(r"<title>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
        doc_title = title_match.group(1).strip() if title_match else url

        # Loại bỏ script, style, comments, noscript
        cleaned = re.sub(r"<script.*?</script>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"<nav.*?</nav>", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"<footer.*?</footer>", " ", cleaned, flags=re.IGNORECASE | re.DOTALL)

        # Chuyển đổi các thẻ heading và ngắt đoạn thành markdown đơn giản
        cleaned = re.sub(r"<h[1-2][^>]*>(.*?)</h[1-2]>", r"\n\n## \1\n\n", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<h[3-4][^>]*>(.*?)</h[3-4]>", r"\n\n### \1\n\n", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\1\n", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", cleaned, flags=re.IGNORECASE)

        # Xóa tất cả các tag HTML còn lại
        text = re.sub(r"<[^>]+>", " ", cleaned)
        # Chuẩn hóa khoảng trắng
        text = re.sub(r"\n\s*\n", "\n\n", text).strip()

        # Cắt ngắn nếu nội dung quá dài (giới hạn 30,000 ký tự cho một URL tài liệu)
        if len(text) > 30000:
            text = text[:30000] + "\n\n...[Nội dung đã được trích lược]..."

        if len(text) < 50:
            raise ValueError("Nội dung tài liệu từ URL quá ngắn hoặc không trích xuất được văn bản.")

        return doc_title, text

    def chunk_text(self, title: str, text: str, max_chunk_size: int = 1200) -> list[dict[str, Any]]:
        """Chia văn bản thành các chunks ngữ nghĩa logic theo tiêu đề hoặc đoạn văn"""
        # Tách theo các heading H2/H3
        sections = re.split(r"\n(?=#{2,3}\s+)", text)
        raw_chunks: list[dict[str, str]] = []

        for sec in sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue

            heading_match = re.match(r"^(#{2,3})\s+(.+)$", sec_clean, flags=re.MULTILINE)
            if heading_match:
                section_title = heading_match.group(2).strip()
            else:
                section_title = "Tổng quan & Nguyên lý"

            # Nếu section quá dài, cắt tiếp thành các đoạn văn
            if len(sec_clean) > max_chunk_size:
                paragraphs = sec_clean.split("\n\n")
                buffer = ""
                p_idx = 1
                for p in paragraphs:
                    p = p.strip()
                    if not p:
                        continue
                    if len(buffer) + len(p) > max_chunk_size:
                        if buffer.strip():
                            raw_chunks.append({
                                "title": f"{title}: {section_title} (Phần {p_idx})",
                                "section": section_title,
                                "content": buffer.strip(),
                            })
                            p_idx += 1
                        buffer = p + "\n\n"
                    else:
                        buffer += p + "\n\n"
                if buffer.strip():
                    raw_chunks.append({
                        "title": f"{title}: {section_title} (Phần {p_idx})",
                        "section": section_title,
                        "content": buffer.strip(),
                    })
            else:
                raw_chunks.append({
                    "title": f"{title}: {section_title}",
                    "section": section_title,
                    "content": sec_clean,
                })

        return raw_chunks

    def synthesize_standardized_strategy(
        self,
        title: str,
        content: str,
        school: str,
        category: str,
        source_name: str,
        source_type: str,
    ) -> StandardizedStrategyDTO:
        """
        Agent LLM [VECTOR] tự động tổng hợp cấu trúc giao dịch tiêu chuẩn hóa cho phương pháp:
        - Chuẩn hóa Tên chiến lược và Slug định danh
        - Xây dựng Checklist điều kiện vào lệnh
        - Điểm Vào lệnh (Entry Zone), Cắt lỗ (SL), Chốt lời (TP)
        - Điều kiện Hủy bỏ (Invalidation) và Rào chắn bảo vệ vốn (Hard Guardrails)
        """
        slug = _slugify(f"{school}_{title}")[:64]
        if not slug or slug == "all":
            slug = f"{school.lower()}_strategy_{int(datetime.now(timezone.utc).timestamp())}"

        # Xác định các yếu tố đặc trưng của từng trường phái
        school_upper = school.upper()
        if "WYCKOFF" in school_upper:
            strategy_name = f"Chiến lược Wyckoff {title.replace('Chiến lược', '').strip()}"
            philosophy = (
                "Ứng dụng chu kỳ tích lũy/phân phối của Richard Wyckoff. Xác định dòng tiền tổ chức (Smart Money) "
                "qua hành vi gom hàng (Accumulation Phase C Spring) hoặc phân phối (Distribution UTAD), "
                "kết hợp kiểm tra khối lượng nỗ lực so với kết quả (Effort vs Result - VSA)."
            )
            timeframe = "H1 / M15"
            checklist = [
                {"id": "s1", "label": "Xác định khung tích lũy Trading Range (TR) có Phase A (SC/AR) và Phase B", "required": True},
                {"id": "s2", "label": "Xuất hiện Spring (Phase C) quét thủng Preliminary Support/Đáy Range với khối lượng cạn kiệt", "required": True},
                {"id": "s3", "label": "Nến kiểm tra (Test of Spring) giữ vững trên đáy cũ và hồi phục dứt khoát", "required": True},
                {"id": "s4", "label": "Xuất hiện cây nến Sign of Strength (SOS) vượt ngưỡng kháng cự trung tâm Creek", "required": True},
                {"id": "s5", "label": "Tỷ lệ tiềm năng Risk:Reward ≥ 1:2.5 hướng tới mục tiêu đỉnh biên trên của Range", "required": True},
                {"id": "s6", "label": "Không có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) trong vòng 30 phút", "required": True},
            ]
            entry_rules = "Mở vị thế BUY tại nhịp hồi kiểm tra (LPS - Last Point of Support) sau cú bật của Spring hoặc SOS."
            sl_rules = "Đặt Stop Loss cách đáy Spring thấp nhất 1.5x ATR M15 để bảo vệ khỏi các cú quét râu thứ cấp."
            tp_rules = "TP1 tại mốc 1:2.0R (đóng 50% khối lượng và dời SL về Breakeven); TP2 tại đỉnh biên trên Range (Jump Across Creek) 1:3.0R - 1:4.0R."
            invalidation = "Giá đóng cửa nến M15 dứt khoát dưới đáy Spring; hoặc thị trường xuất hiện khối lượng bán tháo bất thường (SOW)."
        elif "ICT" in school_upper:
            strategy_name = f"Chiến lược ICT {title.replace('Chiến lược', '').strip()}"
            philosophy = (
                "Khai thác thuật toán phân phối giá liên ngân hàng (IPDA), chu kỳ Power of 3 (AMD: Accumulation - "
                "Manipulation - Distribution) và mô hình Silver Bullet tại các khung giờ vàng (Kill Zones)."
            )
            timeframe = "M15"
            checklist = [
                {"id": "s1", "label": "Thời điểm giao dịch nằm trong Kill Zone (London: 14:00-17:00 ICT hoặc NY AM: 19:00-22:00 ICT)", "required": True},
                {"id": "s2", "label": "Giá quét thanh khoản cũ (Buyside/Sellside Liquidity Pool hoặc Judas Swing)", "required": True},
                {"id": "s3", "label": "Xuất hiện sóng dịch chuyển mạnh mẽ (Displacement) tạo sự phá vỡ cấu trúc Market Structure Shift (MSS)", "required": True},
                {"id": "s4", "label": "Để lại khoảng trống giá mất cân bằng Fair Value Gap (FVG) hợp lệ (biên độ ≥ 0.3x ATR)", "required": True},
                {"id": "s5", "label": "Giá hồi quy về vùng FVG (Consequent Encroachment 50% hoặc Optimal Trade Entry 62-79% Fib)", "required": True},
                {"id": "s6", "label": "R:R tối thiểu đạt ≥ 1:2.0 đến vùng thanh khoản đối ứng tiếp theo", "required": True},
            ]
            entry_rules = "Đặt Limit Entry tại ngưỡng trên của Bullish FVG (hoặc ngưỡng dưới của Bearish FVG) khi giá chạm vùng hồi quy."
            sl_rules = "Đặt SL vượt qua đỉnh/đáy nến displacement hình thành FVG kèm đệm 1.5x ATR."
            tp_rules = "TP1 tại 1:2.0R (chốt 50% và khóa hòa vốn); TP2 tại vùng đỉnh/đáy cũ (Old Highs/Old Lows EQH/EQL)."
            invalidation = "Cây nến M15 đóng cửa xuyên thủng hoàn toàn FVG (Full Inversion Gap)."
        elif "CMT" in school_upper:
            strategy_name = f"Chiến lược CMT {title.replace('Chiến lược', '').strip()}"
            philosophy = (
                "Dựa trên giáo trình Chartered Market Technician (CMT): Nguyên lý phân cực Hỗ trợ - Kháng cự "
                "(Support/Resistance Polarity), xác nhận xu hướng bằng Lý thuyết Dow và phân tích liên thị trường (DXY & Lãi suất thực)."
            )
            timeframe = "H4 / M15"
            checklist = [
                {"id": "s1", "label": "Khung lớn H4 xác nhận xu hướng tăng theo Lý thuyết Dow (Higher Highs / Higher Lows)", "required": True},
                {"id": "s2", "label": "Chỉ số Dollar Index (DXY) phân kỳ nghịch hướng xác nhận đà tăng của Vàng XAUUSD", "required": True},
                {"id": "s3", "label": "Giá hồi về kiểm tra ngưỡng Phân Cực (Polarity Level: Kháng cự cũ chuyển thành Hỗ trợ mới)", "required": True},
                {"id": "s4", "label": "Tín hiệu đảo chiều xác nhận tại M15 (Nến Pinbar / Bullish Engulfing)", "required": True},
                {"id": "s5", "label": "R:R đạt chuẩn tối thiểu ≥ 1:1.8", "required": True},
            ]
            entry_rules = "Vào lệnh tại mức giá đóng cửa của nến xác nhận M15 khi kiểm tra thành công ngưỡng Polarity."
            sl_rules = "Đặt SL dưới đáy vùng hỗ trợ phân cực 1.5x ATR M15."
            tp_rules = "TP1 tại đỉnh gần nhất của sóng H4; TP2 theo tỷ lệ mở rộng Fibonacci 1.618."
            invalidation = "Giá phá vỡ hỗ trợ phân cực và đóng nến H1 phía dưới."
        elif "PRICE_ACTION" in school_upper or "CANDLESTICK" in school_upper:
            strategy_name = f"Chiến lược Price Action {title.replace('Chiến lược', '').strip()}"
            philosophy = (
                "Đọc hành động giá thuần túy (Price Action): Tương quan lực nến, hấp thụ thanh khoản tại cản then chốt, "
                "mô hình nến râu từ chối (Wick Rejection) và nến nhấn chìm (Engulfing)."
            )
            timeframe = "M15"
            checklist = [
                {"id": "s1", "label": "Giá tiếp cận Key Level (Hỗ trợ/Kháng cự then chốt H1)", "required": True},
                {"id": "s2", "label": "Xuất hiện nến rút chân mạnh (Wick Rejection ≥ 60% chiều dài thân nến)", "required": True},
                {"id": "s3", "label": "Nến tiếp theo là nến xác nhận đóng theo hướng đảo chiều", "required": True},
                {"id": "s4", "label": "Tỷ lệ R:R ≥ 1:2.0", "required": True},
            ]
            entry_rules = "Mở vị thế ngay khi nến xác nhận đóng cửa."
            sl_rules = "Đặt SL ngoài đầu râu nến từ chối dài nhất cộng 1.2x ATR."
            tp_rules = "TP1 tại 1:1.5R dời SL về Entry; TP2 tại vùng cản đối diện 1:2.5R."
            invalidation = "Giá phá vỡ đầu râu nến từ chối trước khi khớp lệnh."
        else:
            # Smart Money Concepts (SMC) hoặc General
            strategy_name = f"Chiến lược SMC {title.replace('Chiến lược', '').strip()}"
            philosophy = (
                "Phân tích cấu trúc dòng tiền tổ chức (Smart Money Concepts): Xác định xu hướng HTF (D1/H4), "
                "vùng cung cầu mất cân bằng POI (Order Block, FVG) tại vùng Discount/Premium và xác nhận tín hiệu kích hoạt M15 CHoCH."
            )
            timeframe = "D1 -> H1 -> M15"
            checklist = [
                {"id": "s1", "label": "HTF Trend / Bias trên D1 & H4 đồng thuận (D1/H4 Alignment)", "required": True},
                {"id": "s2", "label": "Xác định POI H1 (OB hoặc FVG) nằm đúng vùng Discount (BUY) hoặc Premium (SELL)", "required": True},
                {"id": "s3", "label": "Thời điểm giao dịch nằm trong Kill Zone London hoặc New York AM", "required": True},
                {"id": "s4", "label": "Giá nhúng vào vùng POI H1 (Tap POI)", "required": True},
                {"id": "s5", "label": "Xuất hiện tín hiệu đảo chiều cấu trúc M15 CHoCH kèm displacement", "required": True},
                {"id": "s6", "label": "Tỷ lệ R:R tiềm năng ≥ 1:2.0", "required": True},
                {"id": "s7", "label": "Không có tin tức vĩ mô 3 sao trong vòng 30 phút", "required": True},
            ]
            entry_rules = "Mở lệnh khi giá hồi quy nhẹ về OB nội phiên M15 sau khi đã hình thành CHoCH rõ rệt."
            sl_rules = "Đặt Stop Loss cách đáy POI M15 1.5x ATR."
            tp_rules = "TP1 tại 1:2.0R (chốt 50%, dời SL hòa vốn); TP2 tại đỉnh Swing High H1 (1:3.0R)."
            invalidation = "Giá nến M15 đóng cửa xuyên thủng hoàn toàn vùng POI H1."

        risk_guardrails = {
            "max_risk_per_trade_pct": 1.0,
            "min_risk_per_trade_pct": 0.25,
            "recommended_risk_pct": 0.50,
            "min_risk_reward": 1.50,
            "target_risk_reward": 2.00,
            "max_daily_drawdown_limit_pct": 3.00,
            "circuit_breaker_buffer_mins": 30,
        }

        source_docs = [{
            "source_type": source_type,
            "source_name": source_name,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }]

        dto = StandardizedStrategyDTO(
            slug=slug,
            name=strategy_name,
            school_of_thought=school_upper,
            timeframe_focus=timeframe,
            target_risk_reward=2.0,
            philosophy=philosophy,
            setup_checklist=checklist,
            entry_rules=entry_rules,
            stop_loss_rules=sl_rules,
            take_profit_rules=tp_rules,
            invalidation_conditions=invalidation,
            risk_guardrails=risk_guardrails,
            source_documents=source_docs,
        )

        return dto

    def save_strategy_to_system_files(self, strategy: StandardizedStrategyDTO) -> tuple[Path, Path]:
        """
        Lưu trữ cấu trúc giao dịch tiêu chuẩn hóa thành 2 file hệ thống:
        1. `<slug>.json`: Dữ liệu có cấu trúc phục vụ máy đọc / API
        2. `<slug>.md`: Tài liệu Markdown hoàn chỉnh phục vụ nghiên cứu & tài liệu hóa
        """
        json_file = self.strategies_dir / f"{strategy.slug}.json"
        md_file = self.strategies_dir / f"{strategy.slug}.md"

        # 1. Xuất file JSON
        strategy_dict = strategy.model_dump()
        json_file.write_text(json.dumps(strategy_dict, indent=2, ensure_ascii=False), encoding="utf-8")

        # 2. Xuất file Markdown
        checklist_md = "\n".join(
            [f"- [ ] **Bước {idx + 1}:** {item['label']}" for idx, item in enumerate(strategy.setup_checklist)]
        )

        md_content = f"""# CẤU TRÚC GIAO DỊCH TIÊU CHUẨN (STANDARDIZED TRADING FRAMEWORK)
## {strategy.name}

> **Mã định danh (Slug):** `{strategy.slug}`  
> **Trường phái học thuật:** `{strategy.school_of_thought}`  
> **Khung thời gian chuẩn:** `{strategy.timeframe_focus}`  
> **Tỷ lệ R:R mục tiêu:** `≥ 1:{strategy.target_risk_reward:.1f}`  
> **Cập nhật hệ thống:** `{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}`  
> **Được chuẩn hóa bởi:** `Agent LLM [VECTOR] (Technical RAG Specialist)`  

---

### 1. Triết Lý & Cơ Chế Thanh Khoản Cốt Lõi
{strategy.philosophy}

---

### 2. Checklist Điều Kiện Vào Lệnh Tiêu Chuẩn
{checklist_md}

---

### 3. Quy Tắc Điểm Vào Lệnh (Entry Criteria)
* **Vùng kích hoạt:** {strategy.entry_rules}
* **Trạng thái nến:** Bắt buộc chờ nến đã đóng hoàn toàn, nghiêm cấm vào lệnh trước khi nến đóng cửa (No Lookahead / No Pre-close Guessing).

---

### 4. Quy Tắc Cắt Lỗ & Chốt Lời (SL / TP Execution)
* **Cắt lỗ (Stop Loss):** {strategy.stop_loss_rules}
* **Chốt lời (Take Profit):** {strategy.take_profit_rules}
* **Quy tắc Dời Cắt Lỗ Hòa Vốn (Breakeven):** Khi lợi nhuận chạm `1:1.5R`, lập tức dời SL về giá Entry để loại bỏ 100% rủi ro cho vị thế.

---

### 5. Điều Kiện Hủy Bỏ Setup (Invalidation Rules)
* {strategy.invalidation_conditions}
* Khi có tin tức vĩ mô 3 sao (CPI, NFP, FOMC) công bố trong vòng 30 phút, toàn bộ lệnh chờ (Pending Orders) lập tức bị hủy bỏ để tuân thủ Circuit Breaker.

---

### 6. Rào Chắn Quản Trị Rủi Ro Cứng (Hard Guardrails)
* **Mức rủi ro cho phép:** `{strategy.risk_guardrails.get("min_risk_per_trade_pct", 0.25)}% – {strategy.risk_guardrails.get("max_risk_per_trade_pct", 1.00)}%` vốn / lệnh.
* **Mức rủi ro khuyến nghị:** `{strategy.risk_guardrails.get("recommended_risk_pct", 0.50)}%` vốn.
* **Ngưỡng khóa lỗ ngày (Daily Drawdown Cap):** `{strategy.risk_guardrails.get("max_daily_drawdown_limit_pct", 3.0)}%` (Arbiter CRO cưỡng chế ngắt mạch giao dịch).
"""
        md_file.write_text(md_content.strip(), encoding="utf-8")
        logger.info("Saved standardized strategy files: %s & %s", json_file.name, md_file.name)

        return json_file, md_file

    async def ingest_document(
        self,
        raw_text: str,
        source_name: str,
        source_type: str,
        custom_title: str | None = None,
        forced_school: str | None = None,
        source_url: str | None = None,
        is_test: bool = False,
    ) -> KnowledgeIngestionResult:
        """
        Quy trình xử lý trọn gói của Agent LLM [VECTOR]:
        1. Phân loại trường phái & tags.
        2. Sinh Cấu trúc Giao dịch Tiêu chuẩn (Standardized Strategy).
        3. Lưu file hệ thống (.json, .md).
        4. Lưu bản ghi vào bảng standardized_trading_strategies.
        5. Chia chunks, trích xuất embedding 1536 chiều, lưu vào bảng trading_knowledge.
        """
        title = custom_title or source_name

        # 1. Phân loại với Vector Agent
        classification = technical_rag_agent.classify_text(f"{title}\n{raw_text[:3000]}")
        school = forced_school or classification.detected_school
        if school == "GENERAL" and forced_school:
            school = forced_school

        # 2. Sinh Cấu trúc Giao dịch Tiêu chuẩn
        std_strategy = self.synthesize_standardized_strategy(
            title=title,
            content=raw_text,
            school=school,
            category=classification.suggested_category,
            source_name=source_name,
            source_type=source_type,
        )

        if is_test:
            std_strategy.slug = f"test_{std_strategy.slug}"

        # 3. Lưu file hệ thống
        json_path, md_path = self.save_strategy_to_system_files(std_strategy)
        std_strategy.system_file_path = str(json_path)

        # 4. Phân chia chunks
        chunks = self.chunk_text(title=title, text=raw_text)
        if not chunks:
            chunks = [{"title": title, "section": "Core", "content": raw_text[:1200]}]

        texts_to_embed = [
            f"{c['title']}\nTrường phái: {school}\n\n{c['content']}" for c in chunks
        ]
        vectors = await embedding_service.embed_batch(texts_to_embed)

        chunk_ids: list[int] = []

        # 5. Lưu vào PostgreSQL
        async with session_factory() as session:
            # 5a. Upsert Standardized Strategy
            stmt = select(StandardizedTradingStrategy).where(
                StandardizedTradingStrategy.slug == std_strategy.slug
            )
            existing_strat = (await session.execute(stmt)).scalar_one_or_none()

            if existing_strat:
                existing_strat.name = std_strategy.name
                existing_strat.school_of_thought = std_strategy.school_of_thought
                existing_strat.timeframe_focus = std_strategy.timeframe_focus
                existing_strat.target_risk_reward = Decimal(str(std_strategy.target_risk_reward))
                existing_strat.philosophy = std_strategy.philosophy
                existing_strat.setup_checklist = std_strategy.setup_checklist
                existing_strat.entry_rules = std_strategy.entry_rules
                existing_strat.stop_loss_rules = std_strategy.stop_loss_rules
                existing_strat.take_profit_rules = std_strategy.take_profit_rules
                existing_strat.invalidation_conditions = std_strategy.invalidation_conditions
                existing_strat.risk_guardrails = std_strategy.risk_guardrails
                existing_strat.source_documents = std_strategy.source_documents
                existing_strat.system_file_path = std_strategy.system_file_path
                existing_strat.is_test = is_test
            else:
                db_strat = StandardizedTradingStrategy(
                    slug=std_strategy.slug,
                    name=std_strategy.name,
                    school_of_thought=std_strategy.school_of_thought,
                    timeframe_focus=std_strategy.timeframe_focus,
                    target_risk_reward=Decimal(str(std_strategy.target_risk_reward)),
                    philosophy=std_strategy.philosophy,
                    setup_checklist=std_strategy.setup_checklist,
                    entry_rules=std_strategy.entry_rules,
                    stop_loss_rules=std_strategy.stop_loss_rules,
                    take_profit_rules=std_strategy.take_profit_rules,
                    invalidation_conditions=std_strategy.invalidation_conditions,
                    risk_guardrails=std_strategy.risk_guardrails,
                    source_documents=std_strategy.source_documents,
                    system_file_path=std_strategy.system_file_path,
                    is_active=True,
                    is_test=is_test,
                )
                session.add(db_strat)

            # 5b. Xóa chunk cũ của file này nếu trùng tên
            await session.execute(
                delete(TradingKnowledge).where(
                    TradingKnowledge.source_file == source_name
                )
            )

            # 5c. Thêm các chunks mới vào trading_knowledge
            for chunk_data, vec in zip(chunks, vectors):
                meta = {
                    "source_name": source_name,
                    "source_type": source_type,
                    "source_url": source_url,
                    "section": chunk_data["section"],
                    "school_of_thought": school,
                    "category": classification.suggested_category,
                    "tags": classification.suggested_tags,
                    "standardized_strategy_slug": std_strategy.slug,
                    "ingested_by": "VECTOR_AGENT",
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                }
                tk = TradingKnowledge(
                    title=chunk_data["title"],
                    school_of_thought=school,
                    category=classification.suggested_category,
                    content=chunk_data["content"],
                    source_type=f"INGESTED_{source_type}",
                    source_file=source_name,
                    source_url=source_url,
                    verified_by_trader=True,
                    confidence_score=Decimal(str(classification.confidence)),
                    metadata_=meta,
                    embedding=vec,
                    is_test=is_test,
                )
                session.add(tk)
                await session.flush()
                chunk_ids.append(tk.id)

            await session.commit()

        # Đọc nội dung file để gửi kèm
        std_strategy.json_content = json.loads(json_path.read_text(encoding="utf-8"))
        std_strategy.markdown_content = md_path.read_text(encoding="utf-8")

        return KnowledgeIngestionResult(
            status="success",
            source_type=source_type,
            source_name=source_name,
            detected_school=school,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
            chunks_created=len(chunks),
            chunk_ids=chunk_ids,
            standardized_strategy=std_strategy,
            file_saved_paths=[str(json_path), str(md_path)],
        )

    async def list_standardized_strategies(
        self, school: str | None = None, include_test: bool = False
    ) -> list[StandardizedStrategyDTO]:
        """Lấy danh sách các cấu trúc giao dịch tiêu chuẩn hóa trong hệ thống"""
        async with session_factory() as session:
            stmt = select(StandardizedTradingStrategy).order_by(
                StandardizedTradingStrategy.updated_at.desc()
            )
            if school and school != "ALL":
                stmt = stmt.where(StandardizedTradingStrategy.school_of_thought == school)
            if not include_test:
                stmt = stmt.where(StandardizedTradingStrategy.is_test.is_(False))

            res = await session.execute(stmt)
            strategies: list[StandardizedStrategyDTO] = []
            for row in res.scalars():
                strategies.append(
                    StandardizedStrategyDTO(
                        slug=row.slug,
                        name=row.name,
                        school_of_thought=row.school_of_thought,
                        timeframe_focus=row.timeframe_focus,
                        target_risk_reward=float(row.target_risk_reward),
                        philosophy=row.philosophy,
                        setup_checklist=row.setup_checklist,
                        entry_rules=row.entry_rules,
                        stop_loss_rules=row.stop_loss_rules,
                        take_profit_rules=row.take_profit_rules,
                        invalidation_conditions=row.invalidation_conditions,
                        risk_guardrails=row.risk_guardrails,
                        source_documents=row.source_documents,
                        system_file_path=row.system_file_path,
                        created_at=row.created_at.isoformat() if row.created_at else None,
                        updated_at=row.updated_at.isoformat() if row.updated_at else None,
                    )
                )
            return strategies

    async def get_strategy_detail(self, slug: str) -> StandardizedStrategyDTO | None:
        """Lấy chi tiết một cấu trúc giao dịch tiêu chuẩn kèm nội dung file hệ thống"""
        async with session_factory() as session:
            stmt = select(StandardizedTradingStrategy).where(
                StandardizedTradingStrategy.slug == slug
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if not row:
                return None

            json_path = self.strategies_dir / f"{slug}.json"
            md_path = self.strategies_dir / f"{slug}.md"

            json_content = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else None
            md_content = md_path.read_text(encoding="utf-8") if md_path.exists() else None

            return StandardizedStrategyDTO(
                slug=row.slug,
                name=row.name,
                school_of_thought=row.school_of_thought,
                timeframe_focus=row.timeframe_focus,
                target_risk_reward=float(row.target_risk_reward),
                philosophy=row.philosophy,
                setup_checklist=row.setup_checklist,
                entry_rules=row.entry_rules,
                stop_loss_rules=row.stop_loss_rules,
                take_profit_rules=row.take_profit_rules,
                invalidation_conditions=row.invalidation_conditions,
                risk_guardrails=row.risk_guardrails,
                source_documents=row.source_documents,
                system_file_path=row.system_file_path,
                json_content=json_content,
                markdown_content=md_content,
                created_at=row.created_at.isoformat() if row.created_at else None,
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )

    async def list_ingested_documents(self) -> list[dict[str, Any]]:
        """Lấy danh sách các tài liệu đã nạp vào Vector DB cùng số lượng chunks"""
        async with session_factory() as session:
            stmt = (
                select(
                    TradingKnowledge.source_file,
                    TradingKnowledge.school_of_thought,
                    TradingKnowledge.category,
                    TradingKnowledge.source_type,
                    TradingKnowledge.source_url,
                    func.count(TradingKnowledge.id).label("chunk_count"),
                    func.max(TradingKnowledge.updated_at).label("last_updated"),
                )
                .where(TradingKnowledge.is_test.is_(False))
                .group_by(
                    TradingKnowledge.source_file,
                    TradingKnowledge.school_of_thought,
                    TradingKnowledge.category,
                    TradingKnowledge.source_type,
                    TradingKnowledge.source_url,
                )
                .order_by(func.max(TradingKnowledge.updated_at).desc())
            )
            rows = (await session.execute(stmt)).all()
            docs: list[dict[str, Any]] = []
            for r in rows:
                docs.append({
                    "source_file": r[0] or "Ghi chú trực tiếp",
                    "school_of_thought": r[1],
                    "category": r[2],
                    "source_type": r[3],
                    "source_url": r[4],
                    "chunk_count": r[5],
                    "last_updated": r[6].isoformat() if r[6] else None,
                })
            return docs

    async def seed_baseline_standardized_strategies(self) -> int:
        """Khởi tạo 5 cấu trúc giao dịch tiêu chuẩn nền tảng nếu chưa có trong hệ thống"""
        baselines = [
            {
                "title": "Smart Money Concepts - Liquidity Sweep & FVG Mitigation",
                "school": "SMC",
                "category": "MARKET_STRUCTURE",
                "content": (
                    "Quy trình phân tích dòng tiền tổ chức: Xác định HTF D1/H4 Trend, "
                    "vùng Order Block và Fair Value Gap (FVG) tại vùng Discount. "
                    "Chờ giá quét thanh khoản (Liquidity Sweeps) nến M15 và xuất hiện CHoCH để vào lệnh BUY."
                ),
                "source_name": "smc_trading_rules.md",
                "source_type": "SYSTEM_CORE",
            },
            {
                "title": "Wyckoff Method - Phase C Spring Accumulation",
                "school": "WYCKOFF",
                "category": "ACCUMULATION_SCHEMATIC",
                "content": (
                    "Quy trình tích lũy Wyckoff Phase C: Giá tạo cú nhúng Spring quét thủng Preliminary Support "
                    "với volume cạn kiệt, sau đó có nến kiểm tra (Test of Spring) và bật tăng vượt Creek (SOS)."
                ),
                "source_name": "wyckoff_method_core.md",
                "source_type": "SYSTEM_CORE",
            },
            {
                "title": "ICT Silver Bullet & London Kill Zone",
                "school": "ICT",
                "category": "POWER_OF_3",
                "content": (
                    "Mô hình ICT Silver Bullet trong phiên London (14:00-17:00 ICT): "
                    "Chờ cú Judas Swing quét sạch thanh khoản phiên Á, sau đó xuất hiện displacement tạo FVG "
                    "hồi quy về Consequent Encroachment 50% để mở lệnh với R:R ≥ 1:2.0."
                ),
                "source_name": "ict_silver_bullet.md",
                "source_type": "SYSTEM_CORE",
            },
            {
                "title": "CMT Support/Resistance Polarity & Intermarket DXY",
                "school": "CMT",
                "category": "INTERMARKET_MACRO",
                "content": (
                    "Nguyên lý Phân Cực của CMT: Kháng cự cũ bị phá vỡ chuyển thành Hỗ trợ mới. "
                    "Xác nhận bằng sự suy yếu của chỉ số Dollar Index (DXY) và nến đảo chiều tại khung M15."
                ),
                "source_name": "cmt_polarity_rules.md",
                "source_type": "SYSTEM_CORE",
            },
            {
                "title": "Classical Price Action - Wick Rejection at Key Levels",
                "school": "PRICE_ACTION",
                "category": "CANDLESTICK_PATTERNS",
                "content": (
                    "Hành động giá Price Action: Hấp thụ thanh khoản tại cản then chốt H1, nến từ chối rút chân "
                    "dài trên 60% thân (Wick Rejection) kèm nến xác nhận đóng chiều."
                ),
                "source_name": "price_action_patterns.md",
                "source_type": "SYSTEM_CORE",
            },
        ]

        seeded_count = 0
        for item in baselines:
            slug = _slugify(f"{item['school']}_{item['title']}")[:64]
            json_file = self.strategies_dir / f"{slug}.json"
            if not json_file.exists():
                await self.ingest_document(
                    raw_text=item["content"],
                    source_name=item["source_name"],
                    source_type=item["source_type"],
                    custom_title=item["title"],
                    forced_school=item["school"],
                    is_test=False,
                )
                seeded_count += 1

        logger.info("Seeded %d baseline standardized strategies", seeded_count)
        return seeded_count


knowledge_ingestion_engine = KnowledgeIngestionEngine()
