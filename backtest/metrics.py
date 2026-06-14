import numpy as np
import pandas as pd


def cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1


def mdd(equity: pd.Series) -> float:
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    return float(drawdown.min())


def sharpe(returns: pd.Series, risk_free: float = 0.0) -> float:
    excess = returns - risk_free / 252
    if excess.std() == 0:
        return 0.0
    return float((excess.mean() / excess.std()) * np.sqrt(252))


def summary(equity: pd.Series, returns: pd.Series) -> dict:
    total = equity.iloc[-1] / equity.iloc[0] - 1
    return {
        "total_return": round(total * 100, 2),
        "cagr": round(cagr(equity) * 100, 2),
        "mdd": round(mdd(equity) * 100, 2),
        "sharpe": round(sharpe(returns), 3),
    }
