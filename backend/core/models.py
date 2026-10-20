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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


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
    data_source: Mapped[str] = mapped_column(String(16), nullable=False, server_default="twelvedata")
    """Nguồn dữ liệu: 'mt5' (MetaTrader5 bridge), 'twelvedata' (Twelve Data Spot Gold XAU/USD), 'synthetic' (tổng hợp M1)"""


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
    __table_args__ = (
        Index("idx_simulated_orders_is_test", "is_test"),
    )

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
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
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
    atr_sl_multiplier: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.50"), server_default=text("1.50"), nullable=False)
    min_risk_reward_ratio: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.50"), server_default=text("1.50"), nullable=False)
    trading_allowed: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    halt_reason: Mapped[str | None] = mapped_column(Text)
    updated_by_agent: Mapped[str] = mapped_column(String(64), default="SYSTEM_INIT", server_default=text("'SYSTEM_INIT'"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StrategySignal(Base):
    __tablename__ = "strategy_signals"
    __table_args__ = (
        Index("idx_strategy_signals_status", "status"),
        Index("idx_strategy_signals_generated_at", "generated_at"),
        Index("idx_strategy_signals_is_test", "is_test"),
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
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TradingKnowledge(Base):
    __tablename__ = "trading_knowledge"
    __table_args__ = (
        Index("idx_trading_knowledge_category", "category"),
        Index("idx_trading_knowledge_school", "school_of_thought"),
        Index("idx_trading_knowledge_source_type", "source_type"),
        Index("idx_trading_knowledge_metadata", "metadata", postgresql_using="gin"),
        Index("idx_trading_knowledge_is_test", "is_test"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    school_of_thought: Mapped[str] = mapped_column(
        String(64), default="GENERAL", server_default=text("'GENERAL'"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(64), default="SYSTEM_CORE", server_default=text("'SYSTEM_CORE'"), nullable=False
    )
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by_trader: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), default=Decimal("1.00"), server_default=text("1.00"), nullable=False
    )
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)


class StandardizedTradingStrategy(Base):
    __tablename__ = "standardized_trading_strategies"
    __table_args__ = (
        Index("idx_std_strategies_school", "school_of_thought"),
        Index("idx_std_strategies_is_test", "is_test"),
        Index("idx_std_strategies_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    school_of_thought: Mapped[str] = mapped_column(String(64), nullable=False)
    timeframe_focus: Mapped[str] = mapped_column(String(32), default="M15", server_default=text("'M15'"), nullable=False)
    target_risk_reward: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("2.00"), server_default=text("2.00"), nullable=False)
    philosophy: Mapped[str] = mapped_column(Text, nullable=False)
    setup_checklist: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False)
    entry_rules: Mapped[str] = mapped_column(Text, nullable=False)
    stop_loss_rules: Mapped[str] = mapped_column(Text, nullable=False)
    take_profit_rules: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation_conditions: Mapped[str] = mapped_column(Text, nullable=False)
    risk_guardrails: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    source_documents: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"), nullable=False)
    system_file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)


class EpisodicTradeMemory(Base):
    __tablename__ = "episodic_trade_memory"
    __table_args__ = (
        Index("idx_episodic_trade_memory_order_id", "order_id"),
        Index("idx_episodic_trade_memory_outcome", "outcome"),
        Index("idx_episodic_trade_memory_mistake", "mistake_category"),
        Index("idx_episodic_trade_memory_is_test", "is_test"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("simulated_orders.id", ondelete="CASCADE"), nullable=True
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    market_context_summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text)
    lesson_learned: Mapped[str] = mapped_column(Text, nullable=False)
    mistake_category: Mapped[str | None] = mapped_column(String(64))
    rule_to_add: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentDecisionLog(Base):
    __tablename__ = "agent_decision_logs"
    __table_args__ = (
        Index("idx_agent_decision_logs_timestamp", "timestamp"),
        Index("idx_agent_decision_logs_is_test", "is_test"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    market_regime: Mapped[str] = mapped_column(String(64), nullable=False)
    suggested_bias: Mapped[str] = mapped_column(String(32), nullable=False)
    consensus_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    technical_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    macro_sentiment_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    active_circuit_breaker: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    applied_risk_pct: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    applied_sl_mult: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    applied_min_rr: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    trading_allowed: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    halt_reason: Mapped[str | None] = mapped_column(Text)
    rationale_summary: Mapped[str] = mapped_column(Text, nullable=False)
    agent_votes: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        Index("idx_chat_conversations_updated_at", "updated_at"),
        Index("idx_chat_conversations_is_pinned", "is_pinned"),
        Index("idx_chat_conversations_is_test", "is_test"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(
        String(255), default="Cuộc trò chuyện mới", server_default=text("'Cuộc trò chuyện mới'"), nullable=False
    )
    agent_target: Mapped[str] = mapped_column(
        String(64), default="GOVERNOR", server_default=text("'GOVERNOR'"), nullable=False
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)

    dialogues: Mapped[list["AgentTraderDialogue"]] = relationship(
        "AgentTraderDialogue", back_populates="conversation", cascade="all, delete-orphan"
    )


class AgentTraderDialogue(Base):
    __tablename__ = "agent_trader_dialogue"
    __table_args__ = (
        Index("idx_agent_trader_dialogue_timestamp", "timestamp"),
        Index("idx_agent_trader_dialogue_is_test", "is_test"),
        Index("idx_agent_trader_dialogue_conv_id", "conversation_id"),
        Index("idx_agent_trader_dialogue_client_msg_id", "client_msg_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=True
    )
    client_msg_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_agent: Mapped[str] = mapped_column(
        String(64), default="GOVERNOR", server_default=text("'GOVERNOR'"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sender: Mapped[str] = mapped_column(String(32), nullable=False)  # 'TRADER', 'GOVERNOR'
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'TEXT', 'COMMAND', 'BRIEFING', 'APPROVAL_REQUEST', 'OVERRIDE_CONFIRM'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False
    )
    approval_status: Mapped[str | None] = mapped_column(String(32))  # 'PENDING', 'APPROVED', 'REJECTED', 'EXPIRED'
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)

    conversation: Mapped[ChatConversation | None] = relationship("ChatConversation", back_populates="dialogues")

