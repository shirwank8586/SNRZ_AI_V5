from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from market import candles
from snrz_engine import Candle, analyze, multi_timeframe
app=FastAPI(title='SNRZ AI V5',version='5.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
BASE=Path(__file__).resolve().parent
@app.get('/')
def home(): return FileResponse(BASE/'index.html')
@app.get('/api/health')
def health(): return {'ok':True,'mode':'paper/educational','engine':'SNRZ AI V5'}
@app.get('/api/candles')
async def get_candles(interval='15m',outputsize=250):
    try:return {'interval':interval,'values':await candles(interval,outputsize)}
    except Exception as e:raise HTTPException(400,str(e))
@app.get('/api/analyze')
async def analyze_one(interval='15m'):
    try:raw=await candles(interval,250)
    except Exception as e:raise HTTPException(400,str(e))
    return analyze([Candle(**x) for x in raw],interval)
@app.get('/api/multi-analysis')
async def multi_analysis():
    result={}
    for iv in ['1w','1d','4h','1h','15m','5m']:
        try: result[iv]=analyze([Candle(**x) for x in await candles(iv,250)],iv)
        except Exception as e: result[iv]={'status':'ERROR','error':str(e)}
    mt=multi_timeframe({k:[Candle(**x) for x in await candles(k,250)] for k in []})
    trends={k:v.get('structure',{}).get('trend') for k,v in result.items()}
    bull=sum(x=='BULLISH' for x in trends.values()); bear=sum(x=='BEARISH' for x in trends.values())
    alignment='BULLISH-LEANING' if bull>bear and bull>=2 else ('BEARISH-LEANING' if bear>bull and bear>=2 else 'MIXED/UNCLEAR')
    return {'symbol':'XAU/USD','mode':'paper/educational','engine':'SNRZ AI V5','structure_alignment':alignment,'analysis':result}
