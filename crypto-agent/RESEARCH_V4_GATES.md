# V4 research quality gates

- Data: spot 5m OHLCV, quote volume, trade count and taker-buy volume. Public Binance archives do **not** include historical spot L2 snapshots. L2 must be sourced separately and provenance tracked; OHLCV participation is only a proxy.
- Labels: log all generated candidate opportunities, including rejected ones; use next-open entry and fixed future horizon. Purge overlapping labels at chronological split boundaries.
- Training: independent train / calibration / out-of-sample segments. Never calibrate on OOS trades. Persist model and sample counts for audit.
- Execution: model partial fills with conservative quote-volume participation caps and leave remainder unfilled. Include normal, adverse, extreme fees/spread/slippage scenarios.
- Validation: lookahead prefix invariance, recursive warmup stability, fold leakage, cost sensitivity, selection overfit, minimum trades, benchmark comparison and no-trade baseline.
- Release gate: fail closed if required tests or data provenance fail. Never infer real L2 from candle volume. No live trading or leverage without independent verification.

References: Binance public data format; Freqtrade lookahead-analysis and recursive-analysis.
