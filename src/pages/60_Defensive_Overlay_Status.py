import os, io, json, glob
import pandas as pd
import numpy as np
import streamlit as st
from src.engine import defensive_signals as ds

st.set_page_config(page_title='Defensive Overlay Status', page_icon='🛡️', layout='wide')
st.title('🛡️ Defensive Overlay Status')
st.caption('Composite Risk Index from VIX, defensive ratio (TLT/SPY), yield curve, sector breadth, and RS flips.')

with st.expander('Data Sources', expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        vix_file = st.text_input('VIX CSV path', 'data/vix.csv')
        tlt_file = st.text_input('TLT CSV path', 'data/tlt.csv')
        spread_file = st.text_input('Yield Curve CSV (columns: date, spread)', 'data/yield_curve.csv')
    with c2:
        spy_file = st.text_input('SPY CSV path', 'data/spy.csv')
        tiles_glob = st.text_input('Sector Tiles CSV (glob allowed, e.g., data/exports/USA_*.csv)', 'data/exports/*USA*sector_tiles*.csv')
        alerts_dir = st.text_input('Alerts dir (for flips)', 'data/alerts')
    st.caption('Tip: leave paths blank and use uploads below to test.')

with st.expander('Or Upload CSVs (overrides above)', expanded=False):
    u1, u2, u3 = st.columns(3)
    with u1:
        up_vix = st.file_uploader('VIX CSV', type=['csv'])
        up_tlt = st.file_uploader('TLT CSV', type=['csv'])
    with u2:
        up_spy = st.file_uploader('SPY CSV', type=['csv'])
        up_spread = st.file_uploader('Yield Curve CSV', type=['csv'])
    with u3:
        up_tiles = st.file_uploader('Sector Tiles CSV', type=['csv'])

run = st.button('Compute Defensive Status', type='primary')

def _resolve_glob(pattern: str):
    paths = sorted(glob.glob(pattern))
    return paths[-1] if paths else pattern

if run:
    base = 'data/defensive/uploads'
    os.makedirs(base, exist_ok=True)
    def _save_up(fobj, name):
        if not fobj: return None
        p = os.path.join(base, name)
        with open(p, 'wb') as o: o.write(fobj.read())
        return p

    vix_p = _save_up(up_vix, 'vix.csv') or vix_file
    tlt_p = _save_up(up_tlt, 'tlt.csv') or tlt_file
    spy_p = _save_up(up_spy, 'spy.csv') or spy_file
    spread_p = _save_up(up_spread, 'yield_curve.csv') or spread_file
    tiles_p = _save_up(up_tiles, 'sector_tiles.csv') or _resolve_glob(tiles_glob)

    out = ds.compute_overlay(
        vix_path=vix_p, tlt_path=tlt_p, spy_path=spy_p,
        spread_path=spread_p, tiles_path=tiles_p,
        alerts_dir=alerts_dir
    )

    st.header(out['status'])
    st.metric('Composite Risk Index', f"{out['record']['risk_index'] if out['record']['risk_index'] is not None else 'NA'}")    

    st.subheader('Component Scores (0–100)')
    st.json(out['scores'])

    cA, cB, cC = st.columns(3)
    with cA:
        st.metric('VIX', f"{out['record']['vix'] if out['record']['vix'] is not None else 'NA'}")
        st.metric('Yield Curve (10y-2y)', f"{out['record']['yield_curve'] if out['record']['yield_curve'] is not None else 'NA'}")
    with cB:
        st.metric('TLT/SPY (last)', f"{out['record']['ratio'] if out['record']['ratio'] is not None else 'NA'}")
        st.metric('Breadth: % Strong', f"{out['record']['breadth_pct_strong'] if out['record']['breadth_pct_strong'] is not None else 'NA'}")
    with cC:
        st.metric('Flips (Strong→Weak, 24h)', f"{out['record']['flips_strong_to_weak']}")

    st.subheader('Charts')
    s = out['series']
    if not s['vix'].empty: st.line_chart(s['vix'].rename('VIX'))
    if not s['ratio'].empty: st.line_chart(s['ratio'].rename('TLT/SPY'))
    if not s['yield_curve'].empty: st.line_chart(s['yield_curve'].rename('10y-2y spread'))

    if st.checkbox('Save snapshot to history.csv', value=True):
        p = ds.save_snapshot(out['record'], path='data/defensive/history.csv')
        st.caption(f'Saved → {p}')

    st.subheader('Recent Sector Flips (24h)')
    if out['flips_recent']:
        st.json(out['flips_recent'])
    else:
        st.caption('No recent Strong→Weak flips.')
else:
    st.info('Configure sources or upload CSVs, then **Compute Defensive Status**.')
