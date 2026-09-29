from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

BUY = {"V.S", "I-VR", "RBS", "SRR", "PO2"}
SELL = {"V.R", "I-VS", "SBR", "RSS"}

@dataclass
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float

def body(c): return abs(c.close-c.open)
def rng(c): return max(c.high-c.low,1e-12)
def bull(c): return c.close>c.open
def bear(c): return c.close<c.open

def pivots(cs, left=2, right=2):
    highs=[]; lows=[]
    for i in range(left,len(cs)-right):
        h=cs[i].high; l=cs[i].low
        if h>=max(x.high for x in cs[i-left:i+right+1]): highs.append((i,h))
        if l<=min(x.low for x in cs[i-left:i+right+1]): lows.append((i,l))
    return highs,lows

def structure(cs:List[Candle],lookback=80):
    c=cs[-lookback:]
    if len(c)<7:return {"trend":"INSUFFICIENT_DATA","hh":0,"hl":0,"lh":0,"ll":0}
    hs,ls=pivots(c); hh=lh=hl=ll=0
    for a,b in zip(hs,hs[1:]): hh+=b[1]>a[1]; lh+=b[1]<a[1]
    for a,b in zip(ls,ls[1:]): hl+=b[1]>a[1]; ll+=b[1]<a[1]
    if hh and hl and hh+hl>lh+ll: t='BULLISH'
    elif lh and ll and lh+ll>hh+hl: t='BEARISH'
    else:t='RANGE/UNCLEAR'
    return {'trend':t,'hh':hh,'hl':hl,'lh':lh,'ll':ll,'pivot_highs':len(hs),'pivot_lows':len(ls)}

def engulfing(cs):
    if len(cs)<2:return {'bullish':False,'bearish':False}
    a,b=cs[-2],cs[-1]
    return {'bullish':bear(a) and bull(b) and b.open<=a.close and b.close>=a.open,
            'bearish':bull(a) and bear(b) and b.open>=a.close and b.close<=a.open}

def classify_break(prev, c, level):
    return {'up_close':prev.close<=level and c.close>level,
            'down_close':prev.close>=level and c.close<level,
            'sweep_up':c.high>level and c.close<=level,
            'sweep_down':c.low<level and c.close>=level}

def detect_levels(cs:List[Candle], tolerance=0.0012, min_touches=2):
    """Conservative candidates only. This does not claim PDF confirmation rules that are not numerically specified."""
    if len(cs)<12:return []
    hs,ls=pivots(cs)
    raw=[]
    for kind,pts in [('S',ls),('R',hs)]:
        for idx,level in pts:
            touches=[]
            for j,x in enumerate(cs):
                val=x.low if kind=='S' else x.high
                if abs(val-level)/max(abs(level),1e-9)<=tolerance: touches.append(j)
            if len(touches)>=min_touches:
                raw.append({'base':kind,'level':level,'touches':len(touches),'first_touch':touches[0],'last_touch':touches[-1]})
    raw.sort(key=lambda z:(-z['touches'],abs(z['level']-cs[-1].close)))
    zones=[]
    for z in raw:
        if any(abs(z['level']-u['level'])/max(abs(z['level']),1e-9)<=tolerance for u in zones):continue
        zones.append(z)
    return zones[:20]

def enrich_zones(cs,zones):
    out=[]
    for z in zones:
        level=z['level']; i=z['last_touch']; later=cs[i+1:] if i+1<len(cs) else []
        reaction_up=any(x.close>level for x in later[-10:])
        reaction_dn=any(x.close<level for x in later[-10:])
        typ=None
        # Base classification is deliberately limited to what OHLC evidence can safely support.
        if z['base']=='S' and reaction_up: typ='V.S'
        elif z['base']=='R' and reaction_dn: typ='V.R'
        # Break / inversion candidates: require a close across the level, not a wick alone.
        if i>0:
            for k in range(max(1,i-8),min(len(cs),i+10)):
                p=cs[k-1]; c=cs[k]; b=classify_break(p,c,level)
                if b['up_close'] and z['base']=='R': typ='RBS'; break
                if b['down_close'] and z['base']=='S': typ='SBR'; break
        # PO2 candidate: two separated touches to the same level; do not call it confirmed.
        if z['touches']>=2 and z['first_touch']<z['last_touch']:
            gap=z['last_touch']-z['first_touch']
            if gap>=2: z['po2_candidate']=True
        z=dict(z,type=typ or 'S/R CANDIDATE')
        out.append(z)
    return out

def liquidity(cs,level):
    if level is None or not cs:return {'sweep':False,'run':False,'direction':None}
    c=cs[-1]
    return {'sweep':(c.high>level and c.close<=level) or (c.low<level and c.close>=level),
            'run':c.close>level or c.close<level,
            'direction':'UP' if c.close>level else ('DOWN' if c.close<level else None)}

def analyze(cs:List[Candle],timeframe:str,level:Optional[float]=None):
    if not cs:return {'timeframe':timeframe,'status':'NO_DATA'}
    st=structure(cs); eg=engulfing(cs); zones=enrich_zones(cs,detect_levels(cs));
    buys=[z for z in zones if z['type'] in BUY]; sells=[z for z in zones if z['type'] in SELL]
    selected=level if level is not None else (zones[0]['level'] if zones else None)
    liq=liquidity(cs,selected)
    reasons=[]
    if liq['sweep']:reasons.append('Liquidity Sweep candidate')
    if liq['run']:reasons.append('Price closed beyond selected level (break/run candidate)')
    if eg['bullish']:reasons.append('Bullish Engulfing on latest candle')
    if eg['bearish']:reasons.append('Bearish Engulfing on latest candle')
    if st['trend']=='BULLISH' and buys: status='BUY FRAMEWORK CANDIDATE'
    elif st['trend']=='BEARISH' and sells: status='SELL FRAMEWORK CANDIDATE'
    else: status='WAIT / NO CONFIRMED SNRZ SETUP'
    return {'timeframe':timeframe,'status':status,'structure':st,'latest':asdict(cs[-1]),'engulfing':eg,
            'selected_level':selected,'liquidity':liq,'zones':zones[:12],'buy_candidates':buys[:6],'sell_candidates':sells[:6],
            'reasons':reasons,
            'limitations':['Automatic labels are candidates, not PDF-confirmed setups.','The engine will not invent a zone when OHLC evidence is insufficient.','No trade execution; paper/educational analysis only.']}

def multi_timeframe(all_candles:Dict[str,List[Candle]]):
    order=['1w','1d','4h','1h','15m','5m']
    out={}
    for tf in order:
        if tf in all_candles: out[tf]=analyze(all_candles[tf],tf)
    # Cross-timeframe summary, without inventing a trade signal.
    trends={tf:x.get('structure',{}).get('trend') for tf,x in out.items()}
    bull=sum(v=='BULLISH' for v in trends.values()); bear=sum(v=='BEARISH' for v in trends.values())
    alignment='BULLISH-LEANING' if bull>bear and bull>=2 else ('BEARISH-LEANING' if bear>bull and bear>=2 else 'MIXED/UNCLEAR')
    return {'timeframes':out,'structure_alignment':alignment,'trend_counts':{'bullish':bull,'bearish':bear,'other':len(out)-bull-bear}}
