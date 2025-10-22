import os,glob,pandas as pd
from src.engine.vector_metrics import compute_from_df

def run_scan(data_dir, kind="rising_wedge", limit=50):
    rec=[]
    for p in sorted(glob.glob(os.path.join(data_dir,"*.csv"))):
        sym=os.path.splitext(os.path.basename(p))[0]
        df=pd.read_csv(p)
        m=compute_from_df(df)
        rec.append({"symbol":sym,"close":float(df.iloc[-1]['close']),"score":1.0,**m})
    return pd.DataFrame(rec).head(limit)
