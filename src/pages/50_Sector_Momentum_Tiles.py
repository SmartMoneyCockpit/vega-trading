import os, io, json, urllib.parse
import pandas as pd
import numpy as np
import streamlit as st
from src.engine import sector_momentum as sm

VERSION = 'Sector Tiles v4'

st.set_page_config(page_title='Sector Momentum Tiles', page_icon='📈', layout='wide')
st.title('📈 Sector Momentum Tiles')
st.caption(f'{VERSION} — Momentum tiles, RS, daily snapshots, flips, and TradingView embeds.')

tabs = st.tabs(['USA','Canada','Mexico','LATAM ex-MX'])

def _tv_proxy_url(path: str):
    safe = urllib.parse.quote(path, safe='')
    return f'/tv/forward?url={safe}'

def region_ui(label: str, tv_url_key: str):
    with st.expander(f'{label} — Uploads', expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            files = st.file_uploader(f'{label}: Sector CSVs', type=['csv'], accept_multiple_files=True, key=f'{label}_files')
        with c2:
            bench = st.file_uploader(f'{label}: Benchmark CSV (optional)', type=['csv'], accept_multiple_files=False, key=f'{label}_bench')
        st.caption('CSV columns: `date, close` (other columns ignored).')

    st.divider()
    cA, cB, cC, cD = st.columns([1,1,1,1])
    with cA:
        price_col = st.text_input('Price column', value='close', key=f'{label}_price')
    with cB:
        tile_limit = st.number_input('Show top N tiles', min_value=1, max_value=50, value=12, step=1, key=f'{label}_limit')
    with cC:
        run = st.button(f'Build Tiles — {label}', type='primary', key=f'{label}_run')
    with cD:
        snapshot = st.checkbox('Auto-save daily snapshot', value=True, key=f'{label}_snap')

    if not run:
        st.info('Upload sector CSVs and click **Build Tiles**.')
    else:
        try:
            bench_df = None
            if bench is not None:
                bdf = pd.read_csv(bench)
                if 'date' in bdf.columns:
                    bdf['date'] = pd.to_datetime(bdf['date'], errors='coerce')
                    bdf = bdf.sort_values('date').set_index('date')
                else:
                    bdf.iloc[:,0] = pd.to_datetime(bdf.iloc[:,0], errors='coerce')
                    bdf = bdf.rename(columns={bdf.columns[0]:'date'}).sort_values('date').set_index('date')
                bench_df = bdf

            df = sm.tiles_from_files(files, bench_df=bench_df, price_col=price_col)
            df = df.sort_values('score', ascending=False)
            df['grade'] = df['score'].apply(sm.grade)
            st.dataframe(df, use_container_width=True)

            st.subheader('Tiles')
            cols = st.columns(min(int(tile_limit), 6))
            for i, (_, r) in enumerate(df.head(int(tile_limit)).iterrows()):
                with cols[i % len(cols)]:
                    st.metric(f"{r['sector']}  {r['grade']}", f"{r['score']*100:.1f}")
                    rs_val = r['rs'] if np.isfinite(r['rs']) else 0.0
                    st.caption(f"1w {r['h_1w']:.2%} • 1m {r['h_1m']:.2%} • 3m {r['h_3m']:.2%} • 6m {r['h_6m']:.2%} • RS {rs_val:.2f}")

            # Snapshot & flips
            if snapshot:
                path = sm.save_snapshot(df[['sector','score','h_1w','h_1m','h_3m','h_6m','rs','grade']], region=label)
                flips, alert_path = sm.detect_flips(df[['sector','score']], region=label)
                st.success(f'Saved snapshot → {path}')
                if flips:
                    st.warning('Sector flips detected:')
                    st.json(flips)
                    st.caption(f'Alert log: {alert_path}')
                else:
                    st.caption('No flips vs last snapshot.')

            # Download
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False)
            st.download_button(f'Download {label} tiles (CSV)', data=csv_buf.getvalue(),
                               file_name=f"{label.lower().replace(' ','_')}_sector_tiles.csv", mime='text/csv')
        except Exception as e:
            st.exception(e)

    # TradingView block
    with st.expander(f'{label} — TradingView Sector View', expanded=False):
        mode = st.radio('Data mode', ['Public (widget)','Authenticated (proxy)'], index=0, key=f'{label}_tv_mode')
        url = st.text_input('TradingView sector URL (layout or screener)', value=st.secrets.get(tv_url_key, ''), key=f'{label}_tv_url')
        height = st.number_input('Embed height (px)', value=700, min_value=400, max_value=2000, step=50, key=f'{label}_tv_h')
        if url:
            if mode.startswith('Public'):
                st.components.v1.html(f'<iframe src="{url}" style="width:100%;height:{height}px;border:0;"></iframe>', height=height)
            else:
                proxied = _tv_proxy_url(url)
                st.components.v1.html(f'<iframe src="{proxied}" style="width:100%;height:{height}px;border:0;"></iframe>', height=height)
        else:
            st.info('Provide a TradingView URL or add it to `.streamlit/secrets.toml`.')

with tabs[0]:
    region_ui('USA', 'TV_URL_USA')
with tabs[1]:
    region_ui('Canada', 'TV_URL_CAN')
with tabs[2]:
    region_ui('Mexico', 'TV_URL_MEX')
with tabs[3]:
    region_ui('LATAM ex-MX', 'TV_URL_LATAM')
