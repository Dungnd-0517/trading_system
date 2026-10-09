from datetime import date, datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "open_time"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)


class FinancialNews(Base):
    __tablename__ = "financial_news"
    __table_args__ = (
        CheckConstraint(
            "impact_stars IS NULL OR impact_stars BETWEEN 1 AND 3",
            name="ck_financial_news_impact_stars",
        ),
        CheckConstraint(
            "(classification_status = 'CLASSIFIED' AND impact_stars IS NOT NULL) "
            "OR (classification_status = 'UNKNOWN' AND impact_stars IS NULL)",
            name="ck_financial_news_classification",
        ),
        CheckConstraint("revision_no >= 1", name="ck_financial_news_revision_no"),
        Index(
            "uq_financial_news_source_external_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index(
            "uq_financial_news_dedupe_key",
            "dedupe_key",
            unique=True,
            postgresql_where=text("dedupe_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    impact_level: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    ai_analysis_summary: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(128))
    dedupe_key: Mapped[str | None] = mapped_column(String(64))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    revision_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(Text)
    impact_stars: Mapped[int | None] = mapped_column(Integer)
    classification_status: Mapped[str] = mapped_column(String(16), default="UNKNOWN", nullable=False)
    keywords_matched: Mapped[list[str] | None] = mapped_column(ARRAY(Text))


class EconomicEvent(Base):
    __tablename__ = "economic_events"
    __table_args__ = (
        CheckConstraint("impact_stars IS NULL OR impact_stars BETWEEN 1 AND 3", name="ck_economic_events_impact_stars"),
        CheckConstraint(
            "(classification_status = 'CLASSIFIED' AND impact_stars IS NOT NULL) "
            "OR (classification_status = 'UNKNOWN' AND impact_stars IS NULL)",
            name="ck_economic_events_classification",
        ),
        CheckConstraint(
            "(timezone_status = 'VERIFIED' AND event_timestamp IS NOT NULL) "
            "OR (timezone_status = 'UNKNOWN' AND event_timestamp IS NULL)",
            name="ck_economic_events_timezone",
        ),
        CheckConstraint("revision_no >= 1", name="ck_economic_events_revision_no"),
        Index("idx_economic_events_time", "event_timestamp"),
        Index("idx_economic_events_stars", "impact_stars"),
        Index(
            "uq_economic_events_source_external_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index(
            "uq_economic_events_dedupe_key",
            "dedupe_key",
            unique=True,
            postgresql_where=text("dedupe_key IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128))
    dedupe_key: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    provider_time_raw: Mapped[str] = mapped_column(Text, nullable=False)
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone_status: Mapped[str] = mapped_column(String(16), default="UNKNOWN", nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    previous_value: Mapped[str | None] = mapped_column(String(32))
    forecast_value: Mapped[str | None] = mapped_column(String(32))
    actual_value: Mapped[str | None] = mapped_column(String(32))
    impact_stars: Mapped[int | None] = mapped_column(Integer)
    classification_status: Mapped[str] = mapped_column(String(16), default="UNKNOWN", nullable=False)
    keywords_matched: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    revision_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EconomicEventRevision(Base):
    __tablename__ = "economic_event_revisions"
    __table_args__ = (UniqueConstraint("economic_event_id", "revision_no"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    economic_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("economic_events.id", ondelete="CASCADE"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SimulatedOrder(Base):
    __tablename__ = "simulated_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticket_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), server_default=func.gen_random_uuid(), nullable=False, unique=True
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    order_type: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    lot_size: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    slippage: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.0"), server_default=text("0.0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.0"), server_default=text("0.0"))
    swap: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.0"), server_default=text("0.0"))
    close_reason: Mapped[str | None] = mapped_column(String(32))
    parent_ticket_id: Mapped[int | None] = mapped_column(BigInteger)
    is_breakeven_moved: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    is_partial_closed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    trailing_stop_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    pnl_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    strategy_trigger: Mapped[str | None] = mapped_column(String(64))
    ai_market_context_id: Mapped[int | None] = mapped_column(ForeignKey("financial_news.id"))


class SimulationAccount(Base):
    __tablename__ = "simulation_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("10000.00"), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("10000.00"), nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("10000.00"), nullable=False)
    margin_used: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SimulationMetric(Base):
    __tablename__ = "simulation_metrics"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_trades: Mapped[int] = mapped_column(Integer, default=0)
    loss_trades: Mapped[int] = mapped_column(Integer, default=0)
    winrate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    profit_factor: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)


class SystemTradingConfig(Base):
    __tablename__ = "system_trading_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    execution_mode: Mapped[str] = mapped_column(String(16), default="MANUAL", nullable=False)
    risk_per_trade_percent: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"), nullable=False)
    breakeven_r_multiple: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.50"), nullable=False)
    enable_partial_tp: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    partial_tp_ratio: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.50"), nullable=False)
    partial_tp_r_multiple: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.00"), nullable=False)
    news_circuit_breaker_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    news_circuit_breaker_buffer_mins: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StrategySignal(Base):
    __tablename__ = "strategy_signals"
    __table_args__ = (
        Index("idx_strategy_signals_status", "status"),
        Index("idx_strategy_signals_generated_at", "generated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_name: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    take_profit_1: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    take_profit_2: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    risk_reward: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    invalidated_reason: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    executed_order_id: Mapped[int | None] = mapped_column(ForeignKey("simulated_orders.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)