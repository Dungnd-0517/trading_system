from backend.data_ingestion.chart_streamer import CandleAggregator


def test_mt5_ticks_update_open_candle_and_count_each_distinct_quote_once():
    aggregator = CandleAggregator({"M1": 60})
    timestamp_ms = 1_790_942_400_000

    first = aggregator.ingest_tick("XAUUSD", timestamp_ms, 2685.0, 2685.2)
    duplicate = aggregator.ingest_tick("XAUUSD", timestamp_ms, 2685.0, 2685.2)
    second = aggregator.ingest_tick("XAUUSD", timestamp_ms, 2686.0, 2686.2)

    assert len(first) == 1
    assert duplicate == []
    assert second[0]["candle"] == {
        "time": timestamp_ms // 1000 - (timestamp_ms // 1000) % 60,
        "open": 2685.0,
        "high": 2686.0,
        "low": 2685.0,
        "close": 2686.0,
    }
    assert second[0]["volume"] == {
        "time": second[0]["timestamp"],
        "value": 2.0,
        "unit": "tick_count",
        "color": "up",
    }


def test_mt5_batch_replay_with_same_millisecond_quotes_is_not_counted_twice():
    aggregator = CandleAggregator({"M1": 60})
    timestamp_ms = 1_790_942_400_000
    first = aggregator.ingest_tick("XAUUSD", timestamp_ms, 2685.0, 2685.2)
    second = aggregator.ingest_tick("XAUUSD", timestamp_ms, 2686.0, 2686.2)
    replay_first = aggregator.ingest_tick("XAUUSD", timestamp_ms, 2685.0, 2685.2)
    replay_second = aggregator.ingest_tick("XAUUSD", timestamp_ms, 2686.0, 2686.2)

    assert len(first) == len(second) == 1
    assert replay_first == replay_second == []


def test_mt5_tick_rolls_to_new_candle():
    aggregator = CandleAggregator({"M1": 60})
    start_ms = 1_790_942_400_000
    aggregator.ingest_tick("XAUUSD", start_ms, 2685.0, 2685.2)

    event = aggregator.ingest_tick("XAUUSD", start_ms + 60_000, 2684.0, 2684.2)[0]

    assert event["candle"]["time"] == start_ms // 1000 + 60
    assert event["candle"]["open"] == 2684.0
    assert event["volume"]["value"] == 1.0
    assert event["volume"]["color"] == "up"


def test_binance_kline_keeps_traded_volume_unit():
    aggregator = CandleAggregator()

    event = aggregator.ingest_kline(
        {
            "symbol": "BTCUSDT",
            "timestamp": 1_790_942_400_000,
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 12.5,
        }
    )

    assert event is not None
    assert event["symbol"] == "BTCUSDT"
    assert event["volume"]["value"] == 12.5
    assert event["volume"]["unit"] == "base_asset_quantity"


def test_binance_paxgusdt_mapped_to_xauusd_with_synthetic_spread():
    aggregator = CandleAggregator()

    event = aggregator.ingest_kline(
        {
            "symbol": "PAXGUSDT",
            "timestamp": 1_790_942_400_000,
            "open": 2685.0,
            "high": 2688.0,
            "low": 2683.0,
            "close": 2686.0,
            "volume": 45.2,
        }
    )

    assert event is not None
    assert event["type"] == "chart.update"
    assert event["symbol"] == "XAUUSD"
    assert event["candle"]["close"] == 2686.0
    assert event["price"] == {"value": 2686.0, "bid": 2685.9, "ask": 2686.1}
    assert event["volume"]["value"] == 45.2
    assert event["volume"]["unit"] == "base_asset_quantity"