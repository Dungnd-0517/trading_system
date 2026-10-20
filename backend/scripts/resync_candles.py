"""
Script to manually trigger full candle purge & resync for XAUUSD.
Usage:
    docker exec trading_backend python -m scripts.resync_candles
"""

import asyncio
import logging
import sys

from data_ingestion.resync_service import resync_candles_full

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "XAUUSD"
    print(f"Triggering Full Candle Resync for {symbol}...")
    result = await resync_candles_full(symbol=symbol, outputsize_per_tf=500, force_purge=True)
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
