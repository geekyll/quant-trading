from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    ticker: str
    name: str
    start: str  # earliest reliable data date


UNIVERSE: list[Asset] = [
    Asset("QQQ", "Invesco QQQ Trust (NASDAQ 100 ETF)", "2005-01-01"),
    Asset("SOXL", "Direxion Semiconductor Bull 3x ETF", "2010-03-11"),
    Asset("SOXS", "Direxion Semiconductor Bear 3x ETF", "2010-03-11"),
    Asset("BTC-USD", "Bitcoin USD", "2015-01-01"),
]

TICKERS: list[str] = [a.ticker for a in UNIVERSE]
