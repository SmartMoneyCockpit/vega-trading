
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
from src.engine import risk_scoring as rs

app = FastAPI(title="Vega Risk Scoring API")

class PricePoint(BaseModel):
    date: str
    close: float

class ScoreRequest(BaseModel):
    prices: List[PricePoint]
    benchmark: Optional[List[PricePoint]] = None
    rf: float = 0.0
    freq: str = "D"
    price_col: str = "close"
    weights: Optional[Dict[str, float]] = None

class BatchItem(BaseModel):
    symbol: str
    prices: List[PricePoint]

class BatchRequest(BaseModel):
    items: List[BatchItem]
    benchmark: Optional[List[PricePoint]] = None
    rf: float = 0.0
    freq: str = "D"
    price_col: str = "close"
    weights: Optional[Dict[str, float]] = None

def _list_to_df(points: List[PricePoint]) -> pd.DataFrame:
    df = pd.DataFrame([{"date": p.date, "close": p.close} for p in points])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values("date").set_index("date")

@app.post("/risk_scoring/score")
def score(req: ScoreRequest):
    asset = _list_to_df(req.prices)
    bench = _list_to_df(req.benchmark) if req.benchmark else None
    metrics = rs.score_from_prices(asset, benchmark=bench, price_col=req.price_col, rf=req.rf, freq=req.freq, weights=req.weights)
    return metrics

@app.post("/risk_scoring/batch")
def batch(req: BatchRequest):
    assets = {item.symbol: _list_to_df(item.prices) for item in req.items}
    bench = _list_to_df(req.benchmark) if req.benchmark else None
    df = rs.batch_score(assets, benchmark=bench, price_col=req.price_col, rf=req.rf, freq=req.freq, weights=req.weights)
    return {"results": df.to_dict(orient="records")}

# To run standalone:
# uvicorn src.services.http_gateway.risk_scoring_endpoint:app --host 0.0.0.0 --port 8080
