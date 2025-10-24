import streamlit as st

st.set_page_config(page_title="Owners Daily Digest", page_icon="🗞️", layout="wide")
st.title("Owners Daily Digest")

try:
    from src.components.digest_store import (
        get_tasks, set_tasks, get_notes, set_notes,
        get_pnl, get_health, get_market_reports
    )
    HAS_STORE = True
except Exception:
    HAS_STORE = False

try:
    from src.components.today_queue import render as render_queue
    HAS_QUEUE = True
except Exception:
    HAS_QUEUE = False

if not HAS_STORE:
    st.warning("Storage helper not found. Drop in `src/components/digest_store.py`.")
else:
    pnl = get_pnl()
    health = get_health()

    st.subheader("Key KPIs (Today)")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total PnL", f"{pnl.get('currency','USD')} {pnl.get('total',0):,.2f}",
                  delta=pnl.get("realized",0)+pnl.get("unrealized",0))
    with c2:
        st.metric("Realized", f"{pnl.get('currency','USD')} {pnl.get('realized',0):,.2f}")
    with c3:
        st.metric("Unrealized", f"{pnl.get('currency','USD')} {pnl.get('unrealized',0):,.2f}")
    with c4:
        st.metric("Trades Executed", int(pnl.get("trades", 0)))
    with c5:
        st.metric("Vagal Score", f"{health.get('vagal_score',0)}/100")

    c6, c7, c8 = st.columns(3)
    with c6:
        st.metric("Blood Pressure", f"{health.get('bp_sys',0)}/{health.get('bp_dia',0)} mmHg")
    with c7:
        st.metric("Resting HR", f"{health.get('hr',0)} bpm")
    with c8:
        st.metric("Sleep (last night)", f"{health.get('sleep_hours',0.0):.1f} h")

    st.divider()
    st.subheader("Owner Tasks")
    tasks_state = get_tasks()
    new_task = st.text_input("Add a task…", placeholder="e.g., Wire Sector Flip Alerts to SendGrid")
    if st.button("➕ Add Task", use_container_width=True) and new_task.strip():
        tasks_state["tasks"].append({"text": new_task.strip(), "done": False})
        set_tasks(tasks_state)
        st.experimental_rerun()

    to_remove = []
    for idx, t in enumerate(tasks_state["tasks"]):
        cols = st.columns([0.1, 0.75, 0.15])
        with cols[0]:
            done = st.checkbox("", value=t.get("done", False), key=f"task_{idx}")
        with cols[1]:
            st.write(("~~" + t["text"] + "~~") if done else t["text"])
        with cols[2]:
            if st.button("🗑️", key=f"del_{idx}"): to_remove.append(idx)
        if done != t.get("done", False):
            t["done"] = done

    if to_remove:
        for i in sorted(to_remove, reverse=True):
            tasks_state["tasks"].pop(i)
        set_tasks(tasks_state)

    st.divider()
    st.subheader("Owner Notes")
    notes_val = get_notes()
    notes = st.text_area("Daily Notes", value=notes_val, height=200,
                         placeholder="Key decisions, alerts, and follow-ups…")
    colA, colB = st.columns([1,1])
    if colA.button("💾 Save Notes", use_container_width=True):
        set_notes(notes); st.success("Notes saved.")
    if colB.button("🧹 Clear Notes", use_container_width=True):
        set_notes(""); st.experimental_rerun()

    st.divider()
    st.subheader("Market Reports Snapshot")
    reports = get_market_reports()
    mcol, ecol = st.columns(2)
    with mcol:
        with st.expander("🌅 Morning Briefing (latest)", expanded=True):
            st.write(reports.get("morning", "No morning briefing found yet."))
    with ecol:
        with st.expander("🌇 End-of-Day Briefing (latest)", expanded=True):
            st.write(reports.get("evening", "No end-of-day briefing found yet."))

st.divider()
st.subheader("📌 Today's Trades Queue")
try:
    if HAS_QUEUE:
        render_queue()
    else:
        st.caption("today_queue not available (optional).")
except Exception:
    st.caption("today_queue not available (optional).")
