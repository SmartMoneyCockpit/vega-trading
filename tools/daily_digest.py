from pathlib import Path
import datetime as dt
import os

def save(prefix,md):
    root=Path(os.getenv("VEGA_NEWS_PATH","data/news")); (root/"posts").mkdir(parents=True,exist_ok=True)
    slug=f"{prefix}_"+dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    (root/"posts"/f"{slug}.md").write_text(md)
    with open(root/"vega_news.md","a") as f: f.write(md+"\n---\n\n")

if __name__=="__main__":
    save("morning", "# Morning Digest\n\nSample")
