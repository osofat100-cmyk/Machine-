# Second-level price data: what this environment can reach (23 Nov 2026)

Tried only sources reachable without changing the environment.

| Source | Reachable | Finest step | Notes |
|---|---|---|---|
| Yahoo Finance | yes | 1 minute (last 30 days); 2 and 5 minutes (60 days) | stocks and ETFs; used for the S&P 500 and Microsoft tests |
| Nasdaq real-time trades (api.nasdaq.com) | yes | single trades | only during today's session; "not available" after hours; no history |
| Hugging Face datasets, small files | yes | varies | files over ~10 MB are served from a blocked address |
| - sheganinans/TickData | yes | **millisecond ticks** | EUR/USD forex bid/ask, only 28 Jul - 1 Aug 2023 (5 days) |
| - AdamAtractor/24_crypto_orderbook_30lvl | yes | 1 minute | 24 coins, 30-level order book + candles |
| - arthurneuron/cryptocurrency-futures-ohlcv-dataset-1m | yes | 1 minute | 51 crypto futures |
| Public GitHub repositories (git) | yes | - | no repository with second-level crypto/stock data found |
| Binance, Kraken, Coinbase, OKX, Bybit, Dukascopy, IEX HIST, Alpaca, Polygon | **no** | seconds / ticks | blocked by the environment's network list |

Conclusion: no second-level crypto or stock history is reachable from here. The finest reachable stock data is
Yahoo's 1-minute bars; the only sub-second history reachable is 5 days of EUR/USD forex ticks.
