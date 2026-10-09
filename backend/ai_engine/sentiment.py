import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SentimentResult:
    score: float
    impact: Literal["LOW", "MEDIUM", "HIGH_RISK_HALT"]
    summary: str


def validate_sentiment(score: float, impact: str, summary: str) -> SentimentResult:
    if not -1.0 <= score <= 1.0:
        raise ValueError("sentiment score must be between -1 and 1")
    if impact not in {"LOW", "MEDIUM", "HIGH_RISK_HALT"}:
        raise ValueError("unsupported impact level")
    return SentimentResult(round(score, 2), impact, summary.strip())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Lexicons for XAUUSD (Gold) and Global Macroeconomic Sentiment
# ---------------------------------------------------------------------------

# Direct Bullish triggers for Gold
_GOLD_BULLISH_PATTERNS = [
    (re.compile(r"\b(gold|bullion|xau|precious metals?)\b.*?\b(rall(y|ies)|soar|surge|jump|rebound|gain|climb|skyrocket|advance|breakout|ath|all-time high|record high)\b", re.I), 0.45),
    (re.compile(r"\b(rall(y|ies)|soar|surge|jump|rebound|gain|climb)\b.*?\b(gold|bullion|xau)\b", re.I), 0.40),
    (re.compile(r"\b(bullish momentum|short covering|buying spree|haven demand|safe-haven|flight to safety)\b", re.I), 0.35),
    (re.compile(r"\b(rate cuts?|fed easing|dovish|policy easing|rate reduction)\b", re.I), 0.35),
    (re.compile(r"\b(dollar|usd|greenback|yields?|treasury yields?)\b.*?\b(fall|falls|drop|drops|slide|slides|ease|eases|retreat|retreats|tumble|plunge|slump|weaken|weak)\b", re.I), 0.40),
    (re.compile(r"\b(geopolitical (tensions?|risks?)|war|invasion|conflict|middle east|escalat(e|ion)|crisis|default risks?)\b", re.I), 0.40),
    (re.compile(r"\b(inflation expectations? rise|stagflation|hedge against inflation)\b", re.I), 0.30),
    (re.compile(r"\b(consumer sentiment falls|preliminary consumer sentiment falls|jobless claims rise|pmi contraction|recession fears)\b", re.I), 0.30),
    (re.compile(r"\b(central bank (gold )?buying|pboc buys gold|gold reserves)\b", re.I), 0.35),
    (re.compile(r"\b(gold|xau).*?\b(target \$\d+|forecast \$\d+|upside potential|break above)\b", re.I), 0.25),
]

# Direct Bearish triggers for Gold
_GOLD_BEARISH_PATTERNS = [
    (re.compile(r"\b(gold|bullion|xau|precious metals?)\b.*?\b(tumble|tumbl(es|ing)|slump|slumps|plunge|plunges|drop|drops|fall|falls|slide|slides|sink|sinks|selloff|retreat|decline|retreats)\b", re.I), -0.45),
    (re.compile(r"\b(tumble|slump|plunge|drop|fall|slide|sink|selloff|decline)\b.*?\b(gold|bullion|xau)\b", re.I), -0.40),
    (re.compile(r"\b(bearish momentum|profit taking|selling pressure|bears dominate|downside risk)\b", re.I), -0.35),
    (re.compile(r"\b(rate hikes?|fed tightens|hawkish|higher for longer|rate pause|keep hike option open)\b", re.I), -0.35),
    (re.compile(r"\b(dollar|usd|greenback|yields?|treasury yields?)\b.*?\b(rally|rallies|surge|surges|jump|jumps|rise|rises|advance|strengthen|strong|gain|gains)\b", re.I), -0.40),
    (re.compile(r"\b(strong (jobs|labor|nfp|payrolls|economic growth)|gdp beats|retail sales surge|inflation drops sharply)\b", re.I), -0.30),
    (re.compile(r"\b(risk-on|stocks rally|risk appetite recovers)\b", re.I), -0.25),
    (re.compile(r"\b(gold|xau).*?\b(break below|support break|downside target)\b", re.I), -0.25),
]

# Single keywords with weights
_KEYWORD_WEIGHTS = {
    "bullish": 0.20,
    "rally": 0.20,
    "rebound": 0.15,
    "breakout": 0.15,
    "soars": 0.20,
    "surges": 0.20,
    "gains": 0.15,
    "safe-haven": 0.25,
    "haven": 0.20,
    "bearish": -0.20,
    "tumbles": -0.20,
    "slumps": -0.20,
    "plunges": -0.20,
    "drops": -0.15,
    "falls": -0.15,
    "selloff": -0.20,
    "pressure": -0.10,
    "retreats": -0.15,
}

_NEGATION_RE = re.compile(r"\b(not|no|never|unlikely to|fails to|failed to|struggles to|unable to|reverses)\b", re.I)
_HIGH_VOLATILITY_RE = re.compile(r"\b(cpi|nfp|nonfarm|fomc|fed meeting|war|emergency|rate decision|powell)\b", re.I)


def analyze_sentiment(
    title: str,
    content: str = "",
    impact_stars: int | None = None,
) -> SentimentResult:
    """
    Phân tích điểm cảm xúc thị trường (Sentiment Score) và tác động đối với XAUUSD (Vàng).
    Trả về điểm từ -1.0 (Rất tiêu cực / Bearish) đến +1.0 (Rất tích cực / Bullish).
    """
    text = f"{title}. {content}".strip()
    score = 0.0
    matched_pos: list[str] = []
    matched_neg: list[str] = []

    # 1. Quét cụm regex mẫu (Pattern matching)
    for pattern, weight in _GOLD_BULLISH_PATTERNS:
        match = pattern.search(text)
        if match:
            # Kiểm tra xem có từ phủ định trước hoặc trong cụm hay không
            start = max(0, match.start() - 25)
            prefix = text[start:match.start()]
            matched_text = match.group(0)
            if _NEGATION_RE.search(prefix) or _NEGATION_RE.search(matched_text):
                score -= weight * 0.8
                matched_neg.append(matched_text[:30])
            else:
                score += weight
                matched_pos.append(matched_text[:30])

    for pattern, weight in _GOLD_BEARISH_PATTERNS:
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - 25)
            prefix = text[start:match.start()]
            matched_text = match.group(0)
            if _NEGATION_RE.search(prefix) or _NEGATION_RE.search(matched_text):
                score -= weight * 0.8
                matched_pos.append(matched_text[:30])
            else:
                score += weight
                matched_neg.append(matched_text[:30])

    # 2. Quét từ khóa bổ trợ nếu chưa có điểm mẫu rõ ràng
    if len(matched_pos) == 0 and len(matched_neg) == 0:
        words = re.findall(r"\b[a-zA-Z-]+\b", text.lower())
        for word in words:
            if word in _KEYWORD_WEIGHTS:
                w_val = _KEYWORD_WEIGHTS[word]
                score += w_val
                if w_val > 0:
                    matched_pos.append(word)
                else:
                    matched_neg.append(word)

    # 3. Điều chỉnh tỷ lệ theo số sao tác động
    if impact_stars == 3:
        score *= 1.2
    elif impact_stars == 1:
        score *= 0.8

    # Giới hạn trong [-1.0, 1.0]
    score = max(-1.0, min(1.0, score))
    final_score = round(score, 2)

    # 4. Xác định mức độ ảnh hưởng (Impact Classification)
    is_high_vol = bool(_HIGH_VOLATILITY_RE.search(text))
    if impact_stars == 3 or (is_high_vol and abs(final_score) >= 0.4) or abs(final_score) >= 0.7:
        impact: Literal["LOW", "MEDIUM", "HIGH_RISK_HALT"] = "HIGH_RISK_HALT"
    elif impact_stars == 2 or abs(final_score) >= 0.25:
        impact = "MEDIUM"
    else:
        impact = "LOW"

    # 5. Sinh tóm tắt phân tích AI (ai_analysis_summary)
    summary = _build_summary(title, final_score, impact, impact_stars, is_high_vol)

    return validate_sentiment(final_score, impact, summary)


def _build_summary(
    title: str,
    score: float,
    impact: str,
    impact_stars: int | None,
    is_high_vol: bool,
) -> str:
    """Tạo bản tóm tắt phân tích AI súc tích giải thích tác động tới giá Vàng"""
    stars_str = f" ({impact_stars}★)" if impact_stars else ""
    
    if score >= 0.15:
        bias_vn = "TÍCH CỰC (BULLISH)"
        desc = (
            "Dòng tiền trú ẩn an toàn hoặc áp lực suy yếu từ USD/lợi suất trái phiếu hỗ trợ đà tăng cho Vàng (XAUUSD). "
            "Ưu tiên theo dõi các cấu trúc Buy SMC tại vùng Discount."
        )
    elif score <= -0.15:
        bias_vn = "TIÊU CỰC (BEARISH)"
        desc = (
            "Sức mạnh từ USD, lợi suất tăng hoặc tâm lý chốt lời gia tăng áp lực điều chỉnh lên giá Vàng (XAUUSD). "
            "Cẩn trọng rủi ro bắt đáy, ưu tiên quản trị vị thế bán."
        )
    else:
        bias_vn = "TRUNG LẬP (NEUTRAL)"
        desc = (
            "Thông tin thị trường mang tính giằng co hoặc chưa tạo động lượng bứt phá đơn chiều. "
            "Giá Vàng có xu hướng đi ngang hoặc dao động trong biên độ tích lũy."
        )

    halt_note = " [CẢNH BÁO BIẾN ĐỘNG CAO]" if impact == "HIGH_RISK_HALT" else ""
    return f"AI Insight [{bias_vn} {score:+.2f}]{stars_str}{halt_note}: {desc}"


# ---------------------------------------------------------------------------
# Database Backfill & Batch Analysis
# ---------------------------------------------------------------------------

async def backfill_news_sentiment(
    session: AsyncSession,
    batch_size: int = 100,
) -> int:
    """
    Quét và tự động chấm điểm cho các tin tức chưa có sentiment_score trong DB.
    Trả về số lượng bản ghi đã được cập nhật.
    """
    from core.models import FinancialNews

    stmt = (
        select(FinancialNews)
        .where(FinancialNews.sentiment_score.is_(None))
        .order_by(FinancialNews.published_at.desc())
        .limit(batch_size)
    )
    rows = (await session.scalars(stmt)).all()
    if not rows:
        return 0

    count = 0
    for row in rows:
        res = analyze_sentiment(
            title=row.title,
            content=row.content or "",
            impact_stars=row.impact_stars,
        )
        row.sentiment_score = Decimal(str(res.score))
        row.ai_analysis_summary = res.summary
        count += 1

    await session.commit()
    logger.info("Backfilled sentiment for %d financial news items", count)
    return count