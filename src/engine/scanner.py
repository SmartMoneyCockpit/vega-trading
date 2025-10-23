# src/engine/scanner.py
from __future__ import annotations
import math
from typing import Iterable, List, Dict, Any
import pandas as pd

MIN_ABS_VOLUME = 100_000  # hard floor
MIN_RVOL = 1.0            # hard floor

def _calc_rvol(df: pd.DataFrame) -> pd.Series:
    """
    RVOL = today's volume / 30D average volume.
    Accept common column name variations.
    """
    vol = None
    for c in ["Volume", "volume"]:
        if c in df.columns:
            vol = df[c]
            break
    avg = None
    for c in ["30D Volume", "avg30d_volume", "Avg30DVolume", "30d_avg_volume"]:
        if c in df.columns:
            avg = df[c]
            break
    if vol is None or avg is None:
        # If we cannot compute, return NaNs so filter drops them.
        return pd.Series([math.nan] * len(df), index=df.index)
    with pd.option_context("mode.use_inf_as_na", True):
        return (vol.astype(float) / avg.astype(float)).replace([math.inf, -math.inf], pd.NA)

def find_matches_from_zero(
    universe: Iterable[Dict[str, Any]] | pd.DataFrame,
    *,
    apply_smart_money_prefilter: bool = True,
    hard_cap_symbols_to_process: int | None = None,
    max_matches_to_return: int = 150,
    start_offset_in_symbol_list: int = 0,
) -> pd.DataFrame:
    """
    Accepts either a list of dicts or a DataFrame with at least:
    'Symbol' (or 'symbol'), 'Sector' (optional), 'Volume', '30D Volume' (or alias columns).
    Returns a filtered & sorted DataFrame with RVOL and hard floors applied.

    NOTE: We DO NOT stop at 'A*'—we iterate the entire (sliced) universe.
    """
    # Normalize to DataFrame
    if isinstance(universe, pd.DataFrame):
        df = universe.copy()
    else:
        df = pd.DataFrame(list(universe))

    # Normalize column names we rely on
    colmap = {}
    if "symbol" in df.columns and "Symbol" not in df.columns:
        colmap["symbol"] = "Symbol"
    if "sector" in df.columns and "Sector" not in df.columns:
        colmap["sector"] = "Sector"
    df = df.rename(columns=colmap)

    # Enforce offset & hard cap on the raw universe *before* filtering
    if start_offset_in_symbol_list and start_offset_in_symbol_list > 0:
        df = df.iloc[start_offset_in_symbol_list:].reset_index(drop=True)
    if hard_cap_symbols_to_process and hard_cap_symbols_to_process > 0:
        df = df.iloc[:hard_cap_symbols_to_process].reset_index(drop=True)

    # Compute RVOL
    df["RVOL"] = _calc_rvol(df)

    # Apply hard floors
    vol_col = "Volume" if "Volume" in df.columns else ("volume" if "volume" in df.columns else None)
    if vol_col is None:
        # If we cannot verify volume, drop everything to avoid bad signals
        return df.iloc[0:0]

    mask = (
        (df[vol_col].fillna(0).astype(float) >= MIN_ABS_VOLUME) &
        (df["RVOL"].astype(float) >= MIN_RVOL)
    )

    # Optional “Smart Money” prefilter: keep only rows that have all the
    # core metric columns (prevents empty/zeroed lines from slipping in).
    if apply_smart_money_prefilter:
        core_cols = ["RS", "RT", "VST"]
        for c in core_cols:
            if c not in df.columns:
                df[c] = pd.NA
        mask &= df[core_cols].notna().all(axis=1)

    filtered = df.loc[mask].copy()

    # Stable sort: by highest RVOL then by dollar % change if present, then by symbol
    sort_cols = []
    if "RVOL" in filtered.columns: sort_cols.append(("RVOL", False))
    if "% PRC" in filtered.columns: sort_cols.append(("% PRC", False))
    sort_by = [c for (c, _) in sort_cols]
    ascending = [asc for (_, asc) in sort_cols]
    if sort_by:
        filtered = filtered.sort_values(by=sort_by, ascending=ascending)
    filtered = filtered.sort_values(by="Symbol", ascending=True, kind="stable")

    # Limit results
    if max_matches_to_return and max_matches_to_return > 0:
        filtered = filtered.head(max_matches_to_return)

    # Nice column order if present
    preferred = ["Symbol", "Sector", "S Change (From Yesterday)", "% PRC", "Value",
                 "RS", "RT", "VST", "CI", "Stop", "GRT", "EPS", "Volume", "30D Volume", "RVOL"]
    cols = [c for c in preferred if c in filtered.columns] + \
           [c for c in filtered.columns if c not in preferred]
    return filtered.loc[:, cols]
