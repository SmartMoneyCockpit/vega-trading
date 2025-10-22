def make_light_badge(region):
    return f"🟡 Wait / Selective • Score 0.50 • Breadth 50% • RS 50% • Vol 2.00"

def passes_rules(symbol,region,rr_ratio=3.0,pop=0.6):
    return {"pass": True, "reasons": []}
