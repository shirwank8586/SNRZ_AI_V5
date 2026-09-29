import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, Query
from market import candles
from snrz_engine import Candle, analyze, multi_timeframe

app = FastAPI(
    title="SNRZ AI V7",
    version="7.0"
)

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "engine": "SNRZ AI V7",
        "method": "SNRZ-only",
        "mode": "paper/educational"
    }

@app.get("/api/analyze")
async def analyze_one(
    interval: str = Query("15m")
):
    try:
        raw = await candles(interval, 250)
        cs = [Candle(**x) for x in raw]
        return analyze(cs, interval)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=str(e)
        )

@app.get("/api/multi-analysis")
async def multi_analysis():

    all_data = {}
    errors = {}

    for tf in [
        "1mo",
        "1w",
        "1d",
        "4h",
        "1h",
        "30m",
        "15m",
        "5m",
        "1m"
    ]:

        try:
            raw = await candles(tf, 250)
            all_data[tf] = [
                Candle(**x)
                for x in raw
            ]

        except Exception as e:
            errors[tf] = str(e)

    if not all_data:
        raise HTTPException(
            status_code=502,
            detail="No market data. Configure TWELVE_DATA_API_KEY."
        )

    result = multi_timeframe(all_data)

    result["engine"] = "SNRZ AI V7"
    result["method"] = "SNRZ-only"
    result["mode"] = "paper/educational"
    result["data_errors"] = errors

    return result
