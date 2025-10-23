
import numpy as np
import pandas as pd

def _to_returns(df: pd.DataFrame, price_col: str = "close", freq: str = "D") -> pd.Series:
    s = pd.to_numeric(df[price_col], errors="coerce").ffill()
    r = s.pct_change().dropna()
    return r

def _ann_factor(freq: str) -> float:
    if freq.upper() in ("D","DAY","DAILY"):
        return 252.0
    if freq.upper() in ("W","WEEK","WEEKLY"):
        return 52.0
    if freq.upper() in ("M","MO","MONTH","MONTHLY"):
        return 12.0
    if freq.upper() in ("H","HOUR","HOURLY"):
        return 252.0*6.5
    return 252.0

def sharpe(returns: pd.Series, rf: float = 0.0, freq: str = "D") -> float:
    ann = _ann_factor(freq)
    ex = returns - (rf/ann)
    mu = ex.mean()
    sd = ex.std(ddof=1)
    if sd == 0 or np.isnan(sd): 
        return np.nan
    return (mu / sd) * np.sqrt(ann)

def sortino(returns: pd.Series, rf: float = 0.0, freq: str = "D") -> float:
    ann = _ann_factor(freq)
    ex = returns - (rf/ann)
    downside = ex[ex < 0]
    dd = downside.std(ddof=1)
    if dd == 0 or np.isnan(dd):
        return np.nan
    mu = ex.mean()
    return (mu / dd) * np.sqrt(ann)

def beta_alpha(returns: pd.Series, bench: pd.Series, rf: float = 0.0, freq: str = "D"):
    df = pd.concat([returns, bench], axis=1).dropna()
    if df.shape[0] < 2:
        return np.nan, np.nan
    r = df.iloc[:,0]
    b = df.iloc[:,1]
    cov = np.cov(r, b, ddof=1)
    var_b = cov[1,1]
    if var_b == 0 or np.isnan(var_b):
        return np.nan, np.nan
    beta = cov[0,1] / var_b
    ann = _ann_factor(freq)
    mean_r = r.mean() * ann
    mean_b = b.mean() * ann
    alpha = mean_r - (rf + beta * (mean_b - rf))
    return float(beta), float(alpha)

def volatility(returns: pd.Series, freq: str = "D") -> float:
    ann = _ann_factor(freq)
    return returns.std(ddof=1) * np.sqrt(ann)

def max_drawdown(series: pd.Series) -> float:
    s = series.dropna()
    if s.empty:
        return np.nan
    roll_max = s.cummax()
    dd = (s / roll_max) - 1.0
    return dd.min()

def cagr(df: pd.DataFrame, price_col: str = "close", freq: str = "D") -> float:
    s = pd.to_numeric(df[price_col], errors="coerce").ffill().dropna()
    if s.shape[0] < 2:
        return np.nan
    start, end = s.iloc[0], s.iloc[-1]
    ann = _ann_factor(freq)
    years = len(s) / ann
    if start <= 0:
        return np.nan
    return (end / start) ** (1.0 / years) - 1.0

def cvar(returns: pd.Series, alpha: float = 0.05) -> float:
    if returns.empty:
        return np.nan
    q = returns.quantile(alpha)
    tail = returns[returns <= q]
    if tail.empty:
        return np.nan
    return tail.mean()

def rolling_metrics(returns: pd.Series, window: int = 63):
    out = {}
    out["roll_sharpe"] = returns.rolling(window).apply(lambda x: np.sqrt(252)* (x.mean() / (x.std(ddof=1) if x.std(ddof=1)!=0 else np.nan)), raw=False)
    out["roll_vol"] = returns.rolling(window).std(ddof=1) * np.sqrt(252)
    return pd.DataFrame(out)

DEFAULT_WEIGHTS = {
    "sharpe": 0.22,
    "sortino": 0.18,
    "beta": 0.10,
    "vol": 0.10,
    "mdd": 0.15,
    "cvar": 0.10,
    "cagr": 0.15
}

def composite_score(metrics: dict, weights: dict = None) -> float:
    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()
    import numpy as np, pandas as pd
    m = pd.Series(metrics, dtype=float)
    inv_beta = -abs(m.get("beta", np.nan)) if np.isfinite(m.get("beta", np.nan)) else np.nan
    inv_vol  = -m.get("vol", np.nan) if np.isfinite(m.get("vol", np.nan)) else np.nan
    inv_mdd  = -abs(m.get("mdd", np.nan)) if np.isfinite(m.get("mdd", np.nan)) else np.nan
    inv_cvar = -abs(m.get("cvar", np.nan)) if np.isfinite(m.get("cvar", np.nan)) else np.nan
    transformed = {
        "sharpe": m.get("sharpe", np.nan),
        "sortino": m.get("sortino", np.nan),
        "beta": inv_beta,
        "vol": inv_vol,
        "mdd": inv_mdd,
        "cvar": inv_cvar,
        "cagr": m.get("cagr", np.nan)
    }
    def squash(x):
        if not np.isfinite(x):
            return 0.5
        return 1.0 / (1.0 + np.exp(-x))
    contribs = {k: squash(v) * (weights.get(k,0)) for k,v in transformed.items()}
    raw = sum(contribs.values())
    wsum = sum([weights.get(k,0) for k in transformed.keys()]) or 1.0
    score01 = raw / wsum
    return float(np.clip(score01 * 100.0, 0.0, 100.0))

def score_from_prices(df: pd.DataFrame, benchmark: pd.DataFrame = None, price_col: str = "close", rf: float = 0.0, freq: str = "D", weights: dict = None) -> dict:
    r = _to_returns(df, price_col=price_col, freq=freq)
    eq = (1 + r).cumprod()
    rb = _to_returns(benchmark, price_col=price_col, freq=freq) if benchmark is not None else None
    s = sharpe(r, rf=rf, freq=freq)
    so = sortino(r, rf=rf, freq=freq)
    b, a = (np.nan, np.nan)
    if rb is not None:
        b, a = beta_alpha(r, rb, rf=rf, freq=freq)
    vol = volatility(r, freq=freq)
    mdd = max_drawdown(eq)
    es  = cvar(r, alpha=0.05)
    cg  = cagr(df, price_col=price_col, freq=freq)
    metrics = {"sharpe": s, "sortino": so, "beta": b, "alpha": a, "vol": vol, "mdd": mdd, "cvar": es, "cagr": cg}
    score = composite_score(metrics, weights=weights)
    metrics["score"] = score
    return metrics

def metrics_to_row(symbol: str, metrics: dict) -> pd.DataFrame:
    row = {"symbol": symbol}
    row.update({k: metrics.get(k) for k in ["score","sharpe","sortino","beta","alpha","vol","mdd","cvar","cagr"]})
    return pd.DataFrame([row])
