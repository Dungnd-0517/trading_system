import unittest

from backend.simulation.paper_engine import OrderStatus, PaperEngine
from backend.simulation.statistics import summarize_trades


class PaperEngineTests(unittest.TestCase):
    def test_buy_fill_accounts_for_ask_and_slippage(self):
        engine = PaperEngine(slippage_points=2, point_size=0.01)
        order = engine.open_market("XAUUSD", "BUY", 0.1, 2000.0, 2000.2, 1995.0, 2010.0)
        self.assertAlmostEqual(order.entry, 2000.22)
        self.assertEqual(order.status, OrderStatus.FILLED)

    def test_buy_closes_at_stop_and_realizes_loss(self):
        engine = PaperEngine(slippage_points=0)
        order = engine.open_market("XAUUSD", "BUY", 0.1, 2000.0, 2000.1, 1995.0, 2010.0)
        closed = engine.on_tick("XAUUSD", 1994.9, 1995.0)
        self.assertEqual(closed, [order])
        self.assertEqual(order.status, OrderStatus.CLOSED)
        self.assertLess(order.realized_pnl, 0)

    def test_rejects_invalid_stop_and_target_order(self):
        engine = PaperEngine()
        with self.assertRaises(ValueError):
            engine.open_market("XAUUSD", "BUY", 0.1, 2000.0, 2000.1, 2001.0, 2010.0)

    def test_trade_statistics(self):
        stats = summarize_trades([10.0, -4.0, 6.0])
        self.assertEqual(stats["total_trades"], 3)
        self.assertAlmostEqual(stats["winrate"], 200 / 3, places=5)
        self.assertEqual(stats["total_pnl"], 12.0)

    def test_manual_close_order(self):
        engine = PaperEngine(slippage_points=0)
        order = engine.open_market("XAUUSD", "BUY", 0.1, 2685.0, 2685.2, 2680.0, 2695.0)
        closed = engine.close_order(order.ticket, exit_price=2690.0, reason="MANUAL_CLOSE")
        self.assertIsNotNone(closed)
        self.assertEqual(closed.status, OrderStatus.CLOSED)
        self.assertEqual(closed.close_reason, "MANUAL_CLOSE")
        self.assertEqual(closed.exit_price, 2690.0)
        self.assertAlmostEqual(closed.realized_pnl, (2690.0 - 2685.2) * 1 * 0.1 * 100.0, places=2)

    def test_sell_closes_at_take_profit(self):
        engine = PaperEngine(slippage_points=0)
        order = engine.open_market("XAUUSD", "SELL", 0.2, 2685.0, 2685.2, 2690.0, 2680.0)
        closed = engine.on_tick("XAUUSD", 2679.5, 2679.7)
        self.assertEqual(closed, [order])
        self.assertEqual(order.status, OrderStatus.CLOSED)
        self.assertEqual(order.close_reason, "TP_HIT")
        self.assertGreater(order.realized_pnl, 0)


if __name__ == "__main__":
    unittest.main()