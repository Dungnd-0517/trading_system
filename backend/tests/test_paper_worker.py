import pytest
from core.database import engine
from simulation.paper_engine import OrderStatus, PaperEngine
from simulation.paper_worker import PaperEngineWorker


@pytest.mark.anyio
async def test_paper_worker_open_and_manual_close(monkeypatch):
    worker = PaperEngineWorker(PaperEngine(slippage_points=0))
    published_events = []

    async def mock_broadcast(event):
        published_events.append(event)

    monkeypatch.setattr(worker, "_broadcast_order_event", mock_broadcast)

    # 1. Test open order via worker with is_test=True
    order_dict = await worker.open_order(
        symbol="XAUUSD",
        side="BUY",
        lots=0.1,
        stop_loss=2680.0,
        take_profit=2700.0,
        quote=(2685.0, 2685.2),
        is_test=True,
    )

    assert order_dict["symbol"] == "XAUUSD"
    assert order_dict["status"] == "FILLED"
    assert order_dict["entry_price"] == 2685.2
    assert order_dict["is_test"] is True
    assert len(published_events) == 1
    assert published_events[0]["event"] == "ORDER_FILLED"

    ticket = order_dict["id"]

    # 2. Test manual close order via worker
    worker.latest_quotes["XAUUSD"] = {"bid": 2690.0, "ask": 2690.2}
    closed_dict = await worker.close_order(ticket, reason="MANUAL_CLOSE")

    assert closed_dict["id"] == ticket
    assert closed_dict["status"] == "CLOSED"
    assert closed_dict["close_reason"] == "MANUAL_CLOSE"
    assert closed_dict["exit_price"] == 2690.0
    assert closed_dict["realized_pnl"] == 48.0  # (2690 - 2685.2) * 1 * 0.1 * 100 = 48.0
    assert len(published_events) == 2
    assert published_events[1]["event"] == "ORDER_CLOSED"


@pytest.mark.anyio
async def test_paper_worker_on_tick_triggers_tp(monkeypatch):
    worker = PaperEngineWorker(PaperEngine(slippage_points=0))
    published_events = []

    async def mock_broadcast(event):
        published_events.append(event)

    monkeypatch.setattr(worker, "_broadcast_order_event", mock_broadcast)

    order_dict = await worker.open_order(
        symbol="XAUUSD",
        side="BUY",
        lots=0.2,
        stop_loss=2680.0,
        take_profit=2695.0,
        quote=(2685.0, 2685.2),
        is_test=True,
    )
    ticket = order_dict["id"]
    assert order_dict["is_test"] is True

    # Tick that hits Take Profit
    events = await worker.on_tick("XAUUSD", bid=2695.5, ask=2695.7)
    assert len(events) == 1
    assert events[0]["id"] == ticket
    assert events[0]["status"] == "CLOSED"
    assert events[0]["close_reason"] == "TP_HIT"
    assert events[0]["exit_price"] == 2695.5
