
import streamlit as st, pandas as pd
from utils import title_with_flag
title_with_flag("Breadth Grid", "")
st.info("Skeleton breadth grid. Replace with internals feed later.")
data = {"Metric":["Adv/Dec","NH/NL","%>50SMA","%>200SMA"],
        "USA":[0.0,0.0,0.0,0.0],
        "Canada":[0.0,0.0,0.0,0.0],
        "Mexico":[0.0,0.0,0.0,0.0]}
st.dataframe(pd.DataFrame(data), use_container_width=True)
