from pathlib import Path
import datetime as dt, os
r=Path(os.getenv("VEGA_NEWS_PATH","data/news")); (r/"posts").mkdir(parents=True,exist_ok=True)
slug="morning_"+dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
(r/"posts"/f"{slug}.md").write_text("# Pre-Market Summary\n\nSample")
with open(r/"vega_news.md","a") as f: f.write("# Pre-Market Summary\n\nSample\n---\n\n")
