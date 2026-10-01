from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    impact_level: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    ai_analysis_summary: Mapped[str | None] = mapped_column(Text)


class SimulatedOrder(Base):
    __tablename__ = "simulated_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    order_type: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    lot_size: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    pnl_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    strategy_trigger: Mapped[str | None] = mapped_column(String(64))
    ai_market_context_id: Mapped[int | None] = mapped_column(ForeignKey("financial_news.id"))


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