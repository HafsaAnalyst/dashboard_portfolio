"""
The Migration — Unified Analytics Dashboard  (Portfolio / Demo build)
=====================================================================

A self-contained Streamlit dashboard that recreates a real analytics product
for a migration & education agency. Every number is SIMULATED in
`sample_data.py` — there is no database or API behind it, so it can be hosted
anywhere and shown to anyone as a portfolio piece.

The Period and City filters in the header are fully wired: changing them
re-slices the generated data and every KPI, chart and table recomputes.

Run with:
    streamlit run portfolio_dashboard/app.py
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sample_data import build_data

st.set_page_config(
    page_title="The Migration — Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data
def get_data() -> dict:
    return build_data()


DATA = get_data()
TODAY: date = DATA["today"]
LEADS_ALL: pd.DataFrame = DATA["leads"]
META_ALL: pd.DataFrame = DATA["meta_daily"]
PLOT_BG = "rgba(0,0,0,0)"

# Colour tokens
C_BLUE, C_GREEN, C_PURPLE, C_AMBER, C_RED = "#3b82f6", "#10b981", "#8b5cf6", "#d08700", "#dc2626"


def hex_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ---------------------------------------------------------------------
# Global styling — warm cream background, white cards, pill-style tabs
# ---------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background:#f3f0e9; }
    .block-container { padding-top: 1.1rem; max-width: 1480px; }
    section[data-testid="stSidebar"] { display:none; }

    /* pill-style tab bar */
    div[data-testid="stTabs"] [data-baseweb="tab-list"]{
        background:#fff; border:1px solid #e6e8eb; border-radius:12px;
        padding:6px; gap:4px;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
    div[data-testid="stTabs"] [data-baseweb="tab-border"]{ display:none; }
    div[data-testid="stTabs"] button[data-baseweb="tab"]{
        border-radius:8px; padding:6px 16px; font-weight:600; color:#475569;
    }
    div[data-testid="stTabs"] button[aria-selected="true"]{
        background:#1e293b; color:#fff !important;
    }

    /* KPI card */
    .kpi { background:#fff; border:1px solid #e6e8eb; border-radius:10px;
           padding:13px 15px; height:100%; }
    .kpi .lbl { font-size:10.5px; color:#7a8189; letter-spacing:.07em;
                font-weight:700; text-transform:uppercase; }
    .kpi .val { font-size:26px; font-weight:700; margin-top:5px; color:#111; line-height:1.1; }
    .kpi .delta { font-size:11.5px; margin-top:4px; }
    .kpi .sec { font-size:11px; color:#9aa0a6; margin-top:5px; }

    .panel-title { font-size:16px; font-weight:700; color:#111; margin:2px 0 10px; }
    .panel-title .hint { float:right; color:#9aa0a6; font-size:12px; font-weight:500; }

    .insight { border-radius:10px; padding:11px 13px; margin-bottom:9px;
               font-size:12.5px; line-height:1.5; color:#1f2937; }

    .pill { padding:3px 11px; border-radius:999px; font-size:12px; font-weight:700;
            display:inline-block; }

    /* funnel rows */
    .fn-row { display:flex; align-items:center; margin:7px 0; }
    .fn-label { width:170px; font-size:13px; color:#374151; }
    .fn-track { flex:1; background:#f1f3f5; border-radius:6px; height:30px; position:relative; }
    .fn-bar { height:30px; border-radius:6px; display:flex; align-items:center;
              padding-left:12px; color:#fff; font-weight:700; font-size:13px; }
    .fn-note { width:120px; text-align:right; font-size:12px; color:#9aa0a6; }

    /* simple grid table */
    table.grid { width:100%; border-collapse:collapse; font-size:13px; }
    table.grid th { text-align:left; color:#7a8189; font-size:10.5px;
        text-transform:uppercase; letter-spacing:.05em; padding:8px 10px;
        border-bottom:1px solid #e6e8eb; font-weight:700; }
    table.grid td { padding:9px 10px; border-bottom:1px solid #f1f3f5; color:#111; }
    table.grid tr.total td { font-weight:700; border-top:2px solid #e6e8eb; background:#fafbfc; }
    .hm-cell { border-radius:7px; text-align:center; padding:9px 0; font-weight:700;
               font-size:13px; color:#fff; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Header — title left, filters top-right (inside a white card)
# ---------------------------------------------------------------------
with st.container(border=True):
    hc = st.columns([6, 2.2, 3.4])
    with hc[0]:
        st.markdown(
            '<div style="font-size:21px;font-weight:700;color:#1e3a5f;">'
            'The Migration — Unified Analytics Dashboard</div>'
            '<div style="font-size:12px;color:#8a8f96;margin-top:3px;">'
            'Live data from GHL · Meta Ads · GA4 · GSC · Updated 2 mins ago</div>',
            unsafe_allow_html=True)
    with hc[1]:
        period_label = st.selectbox(
            "Period",
            ["Last 30 days", "Last 7 days", "Current month", "Last 90 days", "Custom"],
            index=0, label_visibility="collapsed")
    with hc[2]:
        city = st.segmented_control(
            "City", ["All", "Melbourne", "Sydney"], default="All",
            label_visibility="collapsed") or "All"

custom_range = None
if period_label == "Custom":
    custom_range = st.date_input(
        "Custom range", value=(TODAY - timedelta(days=29), TODAY), max_value=TODAY)


def resolve_period(label, custom=None):
    if label == "Last 7 days":
        s, u = TODAY - timedelta(days=6), TODAY
    elif label == "Last 30 days":
        s, u = TODAY - timedelta(days=29), TODAY
    elif label == "Current month":
        s, u = TODAY.replace(day=1), TODAY
    elif label == "Last 90 days":
        s, u = TODAY - timedelta(days=89), TODAY
    elif label == "Custom" and custom and len(custom) == 2:
        s, u = custom
    else:
        s, u = TODAY - timedelta(days=29), TODAY
    length = (u - s).days
    pu = s - timedelta(days=1)
    ps = pu - timedelta(days=length)
    return s, u, ps, pu


since, until, prior_since, prior_until = resolve_period(period_label, custom_range)
n_days = (until - since).days + 1
period_frac = n_days / 30.0


# ---------------------------------------------------------------------
# Slicing
# ---------------------------------------------------------------------
def slice_leads(df, s, u, city_sel):
    out = df[(df["date"] >= pd.Timestamp(s)) & (df["date"] <= pd.Timestamp(u))]
    return out if city_sel == "All" else out[out["city"] == city_sel]


def slice_meta(df, s, u, city_sel):
    out = df[(df["date"] >= pd.Timestamp(s)) & (df["date"] <= pd.Timestamp(u))]
    if city_sel in ("Melbourne", "Sydney"):
        out = out[out["account"].isin([city_sel, "Both"])]
    return out


leads = slice_leads(LEADS_ALL, since, until, city)
leads_prior = slice_leads(LEADS_ALL, prior_since, prior_until, city)
meta = slice_meta(META_ALL, since, until, city)
meta_prior = slice_meta(META_ALL, prior_since, prior_until, city)


# ---------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------
def fmt_int(n): return "—" if n is None else f"{int(round(n)):,}"
def fmt_money0(n): return "—" if n is None else f"${float(n):,.0f}"


def fmt_money_k(n):
    if n is None: return "—"
    n = float(n)
    return f"${n/1000:,.1f}k" if abs(n) >= 1000 else f"${n:,.0f}"


def fmt_pct(n, dp=1): return "—" if n is None else f"{float(n)*100:.{dp}f}%"


def fmt_compact(n):
    if n is None: return "—"
    n = float(n)
    if abs(n) >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if abs(n) >= 10_000: return f"{int(round(n/1000))}k"
    if abs(n) >= 1_000: return f"{n/1000:.1f}k"
    return f"{int(round(n)):,}"


def delta_html(cur, prior, *, higher_better=True, pts=False, suffix="vs last period"):
    if cur is None or prior is None: return ""
    cur, prior = float(cur), float(prior)
    if pts:
        diff = (cur - prior) * 100
        if abs(diff) < 0.05: return f'<span style="color:#9aa0a6;">— {suffix}</span>'
        up = diff > 0; good = up if higher_better else not up
        col = "#15803d" if good else "#dc2626"; arr = "▲" if up else "▼"
        return f'<span style="color:{col};">{arr} {abs(diff):.1f} pts {suffix}</span>'
    if prior == 0: return ""
    pct = (cur - prior) / prior * 100
    if abs(pct) < 0.05: return f'<span style="color:#9aa0a6;">— {suffix}</span>'
    up = pct > 0; good = up if higher_better else not up
    col = "#15803d" if good else "#dc2626"; arr = "▲" if up else "▼"
    return f'<span style="color:{col};">{arr} {abs(pct):.1f}% {suffix}</span>'


def kpi(col, label, value, delta="", secondary=""):
    d = f'<div class="delta">{delta}</div>' if delta else ""
    s = f'<div class="sec">{secondary}</div>' if secondary else ""
    col.markdown(f'<div class="kpi"><div class="lbl">{label}</div>'
                 f'<div class="val">{value}</div>{d}{s}</div>', unsafe_allow_html=True)


def panel_title(text, hint=""):
    h = f'<span class="hint">{hint}</span>' if hint else ""
    st.markdown(f'<div class="panel-title">{text}{h}</div>', unsafe_allow_html=True)


def d_axis(fig, n, prefix="D"):
    step = max(1, n // 7)
    vals = list(range(1, n + 1, step))
    fig.update_xaxes(tickmode="array", tickvals=vals,
                     ticktext=[f"{prefix}{v}" for v in vals])


# ---------------------------------------------------------------------
# Derived metrics (period + city aware)
# ---------------------------------------------------------------------
def metrics(df):
    n = len(df)
    bk = int(df["booked"].sum()) if n else 0
    sh = int(df["showed"].sum()) if n else 0
    cv = int(df["converted"].sum()) if n else 0
    return dict(
        leads=n, booked=bk, showed=sh, conv=cv,
        coes=int(df["is_coe"].sum()) if n else 0,
        voes=int(df["is_voe"].sum()) if n else 0,
        revenue=float(df["revenue"].sum()) if n else 0.0,
        meta_leads=int((df["source"] == "Meta Paid").sum()) if n else 0,
        ltb=(bk / n) if n else None,
        show_rate=(sh / bk) if bk else None,
        conv_rate=(cv / sh) if sh else None,
    )


cur, pri = metrics(leads), metrics(leads_prior)
cur_spend = float(meta["spend"].sum())
pri_spend = float(meta_prior["spend"].sum())
cur_cpl = (cur_spend / cur["meta_leads"]) if cur["meta_leads"] else None
pri_cpl = (pri_spend / pri["meta_leads"]) if pri["meta_leads"] else None
roas = (cur["revenue"] / cur_spend) if cur_spend else None
issued = cur["coes"] + cur["voes"]

tabs = st.tabs(["Executive", "Meta Ads", "Funnel & Pipeline", "Counsellors",
                "SEO & Traffic", "Forecast & Goals", "Upload Reports"])

# =====================================================================
# 1 · EXECUTIVE
# =====================================================================
with tabs[0]:
    r1 = st.columns(7)
    kpi(r1[0], "Total Leads", fmt_int(cur["leads"]), delta_html(cur["leads"], pri["leads"]))
    kpi(r1[1], "Avg CPL (Paid)", fmt_money0(cur_cpl) if cur_cpl else "—",
        delta_html(cur_cpl, pri_cpl, higher_better=False))
    kpi(r1[2], "Lead → Booking", fmt_pct(cur["ltb"]), delta_html(cur["ltb"], pri["ltb"], pts=True))
    kpi(r1[3], "Show Rate", fmt_pct(cur["show_rate"]),
        delta_html(cur["show_rate"], pri["show_rate"], pts=True))
    kpi(r1[4], "Show → Convert", fmt_pct(cur["conv_rate"]),
        delta_html(cur["conv_rate"], pri["conv_rate"], pts=True))
    kpi(r1[5], "COEs (MTD)", fmt_int(cur["coes"]), "", f"of {int(120*period_frac)} target")
    kpi(r1[6], "VOEs (MTD)", fmt_int(cur["voes"]), delta_html(cur["voes"], pri["voes"]))

    r2 = st.columns(7)
    kpi(r2[0], "Ad Spend", fmt_money_k(cur_spend),
        delta_html(cur_spend, pri_spend),
        f"{fmt_money0(cur_spend/cur['meta_leads']) if cur['meta_leads'] else '—'} / paid lead")
    kpi(r2[1], "Revenue", fmt_money_k(cur["revenue"]),
        delta_html(cur["revenue"], pri["revenue"]), f"{roas:.1f}x ROAS" if roas else "")

    st.write("")

    # ---- Goal Progress ----
    with st.container(border=True):
        panel_title(f"Goal Progress — {until.strftime('%B %Y')}", "Click any goal to drill in")
        goals = [
            ("COE Target", cur["coes"], int(120 * period_frac), False, C_GREEN),
            ("VOE Target", cur["voes"], int(40 * period_frac), False, C_GREEN),
            ("Revenue Target", cur["revenue"], int(300000 * period_frac), True, C_AMBER),
            ("Lead Volume", cur["leads"], int(1260 * period_frac), False, C_GREEN),
        ]
        for name, val, target, money, barcol in goals:
            pct = (val / target) if target else 0
            disp = (f"{fmt_money_k(val)} / {fmt_money_k(target)}" if money
                    else f"{int(val):,} / {int(target):,}")
            if money:
                tag = ("✅ Goal met", "#dcfce7", "#166534") if pct >= 1 else (
                    ("Ahead of pace", "#dcfce7", "#166534") if pct >= 0.85 else
                    (f"{int(round((1-pct)*100))}% gap to goal", "#fef3c7", "#92400e"))
            else:
                tag = ("Will exceed", "#dcfce7", "#166534") if pct >= 0.97 else (
                    ("Ahead of pace", "#dcfce7", "#166534") if pct >= 0.85 else
                    (f"On track · need {int(round(target-val))} more", "#fef3c7", "#92400e")
                    if pct >= 0.55 else (f"{int(round((1-pct)*100))}% behind", "#fee2e2", "#991b1b"))
            gc = st.columns([2, 5, 2, 2.2])
            gc[0].markdown(f"<div style='padding-top:2px;font-size:13px;color:#374151;'>{name}</div>",
                           unsafe_allow_html=True)
            gc[1].markdown(
                f"<div style='background:#eef0f2;height:15px;border-radius:8px;margin-top:3px;'>"
                f"<div style='background:{barcol};width:{min(1.0,pct)*100:.1f}%;height:15px;"
                f"border-radius:8px;'></div></div>", unsafe_allow_html=True)
            gc[2].markdown(f"<div style='text-align:right;font-size:13px;color:#374151;'>{disp}</div>",
                           unsafe_allow_html=True)
            gc[3].markdown(f"<div style='text-align:right;'><span class='pill' "
                           f"style='background:{tag[1]};color:{tag[2]};'>{tag[0]}</span></div>",
                           unsafe_allow_html=True)

    # ---- Lead Trend | Auto-Insights ----
    c_left, c_right = st.columns([3, 2])
    with c_left:
        with st.container(border=True):
            panel_title("Lead Trend — All Sources", "Last 30 days")
            days = sorted(pd.to_datetime(leads["date"]).dt.normalize().unique())
            idx = {d: i + 1 for i, d in enumerate(days)}
            fig = go.Figure()
            for src in ["Meta Paid", "Organic / SEO", "Chatbot", "Referral"]:
                color = DATA["source_colors"][src]
                g = (leads[leads["source"] == src]
                     .groupby(pd.to_datetime(leads["date"]).dt.normalize()).size())
                y = [int(g.get(d, 0)) for d in days]
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(days) + 1)), y=y, name=src, mode="lines",
                    line=dict(color=color, width=1.8), stackgroup="one",
                    fillcolor=hex_rgba(color, 0.25)))
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, hovermode="x unified",
                              legend=dict(orientation="h", y=1.14, x=0, font=dict(size=11)),
                              xaxis=dict(showgrid=False),
                              yaxis=dict(showgrid=True, gridcolor="#eef0f2"))
            d_axis(fig, len(days))
            st.plotly_chart(fig, width="stretch")
    with c_right:
        with st.container(border=True):
            panel_title("Auto-Insights", "Rule based")
            insights = [
                ("#ecfdf5", "#047857", "<b>Sydney Meta CPL dropped 23%</b> this week, driven by 'PR Pathway — IT' creative. Recommend scaling budget +$1.5k."),
                ("#fffbeb", "#b45309", "<b>Show Rate down 3.2 pts.</b> Largest drop on Wajahat's calendar (Harris Park). Suggest reminder SMS automation."),
                ("#fef2f2", "#b91c1c", "<b>Campaign 'Visa-Ext-Mel-V3'</b> — CPL $112, 4× account average. Recommend pausing — saves ~$850/wk."),
                ("#eff6ff", "#1d4ed8", "<b>3 paid leads from organic search</b> mentioned the '485 Visa' blog post — Zainab's automation will track this in 2 weeks."),
            ]
            for bg, fg, t in insights:
                st.markdown(f'<div class="insight" style="background:{bg};border-left:3px solid {fg};">{t}</div>',
                            unsafe_allow_html=True)

    # ---- Lead Source Mix | Visa vs Admissions Pipeline ----
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            panel_title("Lead Source Mix", "Click to filter")
            order = list(DATA["source_colors"].keys())
            mix = leads.groupby("source").size().reindex(order).fillna(0)
            total = mix.sum() or 1
            labels = [f"{s} {mix[s]/total*100:.0f}%" for s in order]
            donut = go.Figure(go.Pie(
                labels=labels, values=mix.values, hole=0.62, sort=False,
                marker=dict(colors=[DATA["source_colors"][s] for s in order]),
                textinfo="none"))
            donut.update_layout(height=260, margin=dict(l=0, r=0, t=0, b=0),
                                paper_bgcolor=PLOT_BG,
                                legend=dict(orientation="v", x=1, y=0.5, font=dict(size=12)))
            st.plotly_chart(donut, width="stretch")
    with c2:
        with st.container(border=True):
            panel_title("Visa vs Admissions Pipeline", "Last 30 days")
            stages = ["Leads", "Booked", "Showed", "Converted", "COE/VOE"]
            bar = go.Figure()
            for pipe, color in [("Visa", C_PURPLE), ("Education", C_GREEN)]:
                sub = leads[leads["pipeline"] == pipe]
                vals = [len(sub), int(sub["booked"].sum()), int(sub["showed"].sum()),
                        int(sub["converted"].sum()),
                        int(sub["is_voe"].sum() if pipe == "Visa" else sub["is_coe"].sum())]
                bar.add_trace(go.Bar(name=pipe, x=stages, y=vals, marker_color=color))
            bar.update_layout(barmode="group", height=260, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
                              legend=dict(orientation="h", y=-0.18, x=0.3),
                              xaxis=dict(showgrid=False),
                              yaxis=dict(showgrid=True, gridcolor="#eef0f2"))
            st.plotly_chart(bar, width="stretch")

# =====================================================================
# 2 · META ADS
# =====================================================================
with tabs[1]:
    spend = float(meta["spend"].sum())
    impr = float(meta["impressions"].sum())
    clicks = float(meta["clicks"].sum())
    mleads = int(round(meta["leads"].sum()))
    ctr = (clicks / impr) if impr else None
    cpl_meta = (spend / mleads) if mleads else None
    p_spend = float(meta_prior["spend"].sum())
    p_impr = float(meta_prior["impressions"].sum())
    p_clicks = float(meta_prior["clicks"].sum())
    p_mleads = int(round(meta_prior["leads"].sum()))
    p_ctr = (p_clicks / p_impr) if p_impr else None
    p_cpl = (p_spend / p_mleads) if p_mleads else None

    r = st.columns(6)
    kpi(r[0], "Total Spend", fmt_money0(spend), delta_html(spend, p_spend), "both accounts")
    kpi(r[1], "Impressions", fmt_compact(impr), delta_html(impr, p_impr))
    kpi(r[2], "Clicks", fmt_compact(clicks), delta_html(clicks, p_clicks))
    kpi(r[3], "CTR", fmt_pct(ctr, 2), delta_html(ctr, p_ctr, pts=True))
    kpi(r[4], "Leads (Meta)", fmt_int(mleads), delta_html(mleads, p_mleads))
    kpi(r[5], "Avg CPL", fmt_money0(cpl_meta) if cpl_meta else "—",
        delta_html(cpl_meta, p_cpl, higher_better=False))

    st.write("")

    def account_panel(col, account_name, color):
        sub = meta[meta["account"].isin([account_name, "Both"])]
        a_spend = float(sub["spend"].sum())
        a_leads = int(round(sub["leads"].sum()))
        a_clicks = float(sub["clicks"].sum())
        a_impr = float(sub["impressions"].sum())
        a_ctr = (a_clicks / a_impr) if a_impr else 0
        a_cpl = (a_spend / a_leads) if a_leads else 0
        cm = slice_leads(LEADS_ALL, since, until, account_name)
        cm = cm[cm["source"] == "Meta Paid"]
        booked, showed, conv = int(cm["booked"].sum()), int(cm["showed"].sum()), int(cm["converted"].sum())
        with col:
            with st.container(border=True):
                panel_title(f"{account_name} Account",
                            f'<span class="pill" style="background:#eef2ff;color:#3730a3;">'
                            f'{fmt_money0(a_spend)} spend</span>')
                m = st.columns(3)
                m[0].metric("Leads", f"{a_leads:,}")
                m[1].metric("CPL", f"${a_cpl:,.0f}")
                m[2].metric("CTR", f"{a_ctr*100:.2f}%")
                m2 = st.columns(3)
                m2[0].metric("Booked", f"{booked:,}")
                m2[1].metric("Showed", f"{showed:,}")
                m2[2].metric("Converted", f"{conv:,}")
                dd = sub.groupby(sub["date"].dt.date).agg(
                    spend=("spend", "sum"), leads=("leads", "sum")).reset_index()
                dd["cpl"] = (dd["spend"] / dd["leads"]).where(dd["leads"] > 0, 0)
                figc = go.Figure(go.Scatter(
                    x=list(range(1, len(dd) + 1)), y=dd["cpl"], mode="lines",
                    line=dict(color=color, width=2.5), fill="tozeroy",
                    fillcolor=hex_rgba(color, 0.13)))
                figc.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=10),
                                   paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, showlegend=False,
                                   xaxis=dict(showgrid=False),
                                   yaxis=dict(showgrid=True, gridcolor="#eef0f2", title="daily CPL ($)"))
                d_axis(figc, len(dd))
                st.plotly_chart(figc, width="stretch")

    cc1, cc2 = st.columns(2)
    account_panel(cc1, "Melbourne", C_BLUE)
    account_panel(cc2, "Sydney", C_GREEN)

    with st.container(border=True):
        panel_title("Campaign Performance — click row for ad-set drill-down", "Sorted by spend")
        rows = []
        for name, account, base_spend, cpl_bias in DATA["campaigns"]:
            sub = meta[meta["campaign"] == name]
            if sub.empty:
                continue
            c_spend = float(sub["spend"].sum())
            c_leads = int(round(sub["leads"].sum()))
            c_cpl = (c_spend / c_leads) if c_leads else 0
            booked = int(round(c_leads * 0.37))
            conv = int(round(booked * 0.225))
            status = ("Kill" if c_cpl > 90 else "Scale" if c_cpl < 36
                      else "Keep" if c_cpl < 46 else "Optimize")
            rows.append((name, account, c_spend, c_leads, c_cpl, booked, conv, status))
        rows.sort(key=lambda x: -x[2])
        spill = {"Scale": ("#dcfce7", "#166534"), "Keep": ("#dbeafe", "#1e40af"),
                 "Optimize": ("#fef9c3", "#854d0e"), "Kill": ("#fee2e2", "#991b1b")}
        html = ['<table class="grid"><tr><th>Campaign</th><th>Account</th><th>Spend</th>'
                '<th>Leads</th><th>CPL</th><th>Booked</th><th>Conv.</th><th>Status</th></tr>']
        for nm, acc, sp, ld, cp, bk, cv, stt in rows:
            bg, fg = spill[stt]
            html.append(
                f"<tr><td style='color:#1d4ed8;font-weight:600;'>{nm}</td><td>{acc}</td>"
                f"<td>${sp:,.0f}</td><td>{ld}</td><td>${cp:,.0f}</td><td>{bk}</td><td>{cv}</td>"
                f"<td><span class='pill' style='background:{bg};color:{fg};'>{stt}</span></td></tr>")
        html.append("</table>")
        st.markdown("".join(html), unsafe_allow_html=True)
        st.caption("Status rule: CPL < $36 → Scale · < $46 → Keep · < $90 → Optimize · ≥ $90 → Kill.")

# =====================================================================
# 3 · FUNNEL & PIPELINE
# =====================================================================
with tabs[2]:
    n = cur["leads"]
    paid_client = issued
    initial = int(round(paid_client / 0.68)) if paid_client else 0
    booking_shared = int(round(n * 0.56))
    booked, showed = cur["booked"], cur["showed"]
    fn = [
        ("1. Lead Created", n, n, C_BLUE, "100%"),
        ("2. Booking Link Shared", booking_shared, n, C_BLUE,
         f"{booking_shared/n*100:.0f}% of leads" if n else "—"),
        ("3. Appointment Booked", booked, n, C_GREEN,
         f"{booked/booking_shared*100:.0f}% of step 2" if booking_shared else "—"),
        ("4. Showed Up", showed, n, C_GREEN,
         f"{showed/booked*100:.0f}% show rate" if booked else "—"),
        ("5. Initial Requested", initial, n, C_PURPLE,
         f"{initial/showed*100:.0f}% of shows" if showed else "—"),
        ("6. Paid Client", paid_client, n, C_PURPLE,
         f"{paid_client/initial*100:.0f}% of initial" if initial else "—"),
        ("7. COE / VOE Issued", issued, n, C_GREEN,
         f"{issued/n*100:.1f}% overall" if n else "—"),
    ]
    with st.container(border=True):
        panel_title("Lead-to-Outcome Funnel", "All sources · Last 30 days · Click any stage")
        mx = n or 1
        for label, val, _base, color, note in fn:
            w = max(4.0, val / mx * 100)
            st.markdown(
                f"<div class='fn-row'><div class='fn-label'>{label}</div>"
                f"<div class='fn-track'><div class='fn-bar' style='width:{w:.1f}%;"
                f"background:{color};'>{val:,}</div></div>"
                f"<div class='fn-note'>{note}</div></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            panel_title("Pipeline Split", "Education vs Visa")
            ps = leads.groupby("pipeline").size()
            v = int(ps.get("Visa", 0)); e = int(ps.get("Education", 0))
            tot = (v + e) or 1
            donut = go.Figure(go.Pie(
                labels=[f"CLT · Visa {v/tot*100:.0f}%", f"L2C · Education {e/tot*100:.0f}%"],
                values=[v, e], hole=0.6, sort=False,
                marker=dict(colors=[C_PURPLE, C_GREEN]), textinfo="none"))
            donut.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0),
                                paper_bgcolor=PLOT_BG,
                                legend=dict(orientation="h", y=-0.05, x=0.1, font=dict(size=12)))
            st.plotly_chart(donut, width="stretch")
    with c2:
        with st.container(border=True):
            panel_title("Loss Reasons (Post-Consultation)")
            base_counts = [38, 29, 22, 19, 14]
            for (reason, p), bc in zip(DATA["loss_reasons"], base_counts):
                cnt = int(round(bc * period_frac))
                st.markdown(
                    f"<div style='display:flex;align-items:center;padding:9px 2px;"
                    f"border-bottom:1px solid #f1f3f5;'>"
                    f"<div style='flex:1;font-size:13px;color:#374151;'>{reason}</div>"
                    f"<div style='width:60px;text-align:right;font-weight:600;'>{cnt}</div>"
                    f"<div style='width:60px;text-align:right;'><span class='pill' "
                    f"style='background:#fef3c7;color:#92400e;'>{p*100:.0f}%</span></div></div>",
                    unsafe_allow_html=True)

# =====================================================================
# 4 · COUNSELLORS
# =====================================================================
with tabs[3]:
    rows = []
    for name, short, ctype, ccity, slots, booked, showed, conv in DATA["counsellors"]:
        if city == "Melbourne" and ccity != "Melbourne":
            continue
        if city == "Sydney" and ccity != "Sydney":
            continue
        sc = period_frac
        rows.append(dict(
            name=name, short=short, type=ctype, city=ccity,
            slots=slots * sc, booked=booked * sc, showed=showed * sc, conv=conv * sc))

    tot_slots = sum(r["slots"] for r in rows)
    tot_booked = sum(r["booked"] for r in rows)
    tot_showed = sum(r["showed"] for r in rows)
    tot_conv = sum(r["conv"] for r in rows)
    paid_consults = tot_conv * 94.6
    best = max(rows, key=lambda r: (r["conv"] / r["showed"]) if r["showed"] else 0) if rows else None
    best_label = best["short"] if best else "—"
    best_conv = (best["conv"] / best["showed"] * 100) if best and best["showed"] else 0

    r = st.columns(6)
    kpi(r[0], "Slots Available", fmt_int(tot_slots))
    kpi(r[1], "Slots Booked", fmt_int(tot_booked), "",
        f"{tot_booked/tot_slots*100:.1f}% fill" if tot_slots else "")
    kpi(r[2], "Showed", fmt_int(tot_showed), "",
        f"{tot_showed/tot_booked*100:.1f}% show" if tot_booked else "")
    kpi(r[3], "Converted", fmt_int(tot_conv), "",
        f"{tot_conv/tot_showed*100:.1f}% conv" if tot_showed else "")
    kpi(r[4], "Paid Consults", fmt_money0(paid_consults))
    kpi(r[5], "Best Performer", best_label, "", f"{best_conv:.0f}% conv.")

    st.write("")
    with st.container(border=True):
        panel_title("Counsellor Performance Matrix", "Click row for full breakdown")
        if not rows:
            st.info(f"No counsellors based in {city}.")
        else:
            def type_pill(t):
                paid = "Paid" in t
                bg, fg = ("#dbeafe", "#1e40af") if paid else ("#f1f5f9", "#475569")
                return f"<span class='pill' style='background:{bg};color:{fg};font-size:11px;'>{t}</span>"

            html = ['<table class="grid"><tr><th>Counsellor</th><th>Type</th><th>Slots</th>'
                    '<th>Booked</th><th>Fill %</th><th>Showed</th><th>Show %</th>'
                    '<th>Convert</th><th>Conv %</th></tr>']
            for rr in rows:
                fill = rr["booked"] / rr["slots"] if rr["slots"] else 0
                show = rr["showed"] / rr["booked"] if rr["booked"] else 0
                cv = rr["conv"] / rr["showed"] if rr["showed"] else 0
                cv_pct = cv * 100
                cvcol = ("#15803d" if cv_pct >= 39 else "#991b1b" if cv_pct < 18 else "#111")
                cvwt = "700" if (cv_pct >= 39 or cv_pct < 18) else "400"
                html.append(
                    f"<tr><td style='color:#1d4ed8;font-weight:600;'>{rr['name']}</td>"
                    f"<td>{type_pill(rr['type'])}</td><td>{rr['slots']:.0f}</td>"
                    f"<td>{rr['booked']:.0f}</td><td>{fill*100:.1f}%</td>"
                    f"<td>{rr['showed']:.0f}</td><td>{show*100:.1f}%</td>"
                    f"<td style='color:#b45309;font-weight:600;'>{rr['conv']:.0f}</td>"
                    f"<td style='color:{cvcol};font-weight:{cvwt};'>{cv_pct:.1f}%</td></tr>")
            t_fill = tot_booked / tot_slots if tot_slots else 0
            t_show = tot_showed / tot_booked if tot_booked else 0
            t_cv = tot_conv / tot_showed if tot_showed else 0
            html.append(
                f"<tr class='total'><td>Total</td><td>—</td><td>{tot_slots:.0f}</td>"
                f"<td>{tot_booked:.0f}</td><td>{t_fill*100:.1f}%</td><td>{tot_showed:.0f}</td>"
                f"<td>{t_show*100:.1f}%</td><td>{tot_conv:.0f}</td><td>{t_cv*100:.1f}%</td></tr>")
            html.append("</table>")
            st.markdown("".join(html), unsafe_allow_html=True)

    with st.container(border=True):
        panel_title("Where Leads Drop Off — Heatmap by Counsellor")
        hm = DATA["heatmap"]
        stage_cols = ["Booked", "Showed", "Initial Req.", "Paid", "COE"]
        grid = [(name, [int(round(v * period_frac)) for v in vals]) for name, *vals in hm]
        # per-column min/max for the red→green scale
        cols_vals = list(zip(*[g[1] for g in grid]))
        palette = ["#e06666", "#ef9a6b", "#f6c667", "#8fc27e", "#4aa56c"]

        def cell_color(val, col_vals):
            lo, hi = min(col_vals), max(col_vals)
            t = 0.5 if hi == lo else (val - lo) / (hi - lo)
            return palette[min(4, int(t * 5 + 1e-9)) if t < 1 else 4]

        head = "<tr><th style='width:120px;'>Stage →</th>" + \
               "".join(f"<th style='text-align:center;'>{c}</th>" for c in stage_cols) + "</tr>"
        body = []
        for ci, (name, vals) in enumerate(grid):
            tds = "".join(
                f"<td style='padding:4px;'><div class='hm-cell' "
                f"style='background:{cell_color(v, cols_vals[j])};'>{v}</div></td>"
                for j, v in enumerate(vals))
            body.append(f"<tr><td style='font-size:13px;color:#374151;'>{name}</td>{tds}</tr>")
        st.markdown(f"<table class='grid'>{head}{''.join(body)}</table>", unsafe_allow_html=True)
        st.caption("Heatmap intensity reflects volume — red cells indicate biggest drop-offs. "
                   "Manhal's pipeline loses 47% of leads between Showed and Paid — recommend coaching review.")

# =====================================================================
# 5 · SEO & TRAFFIC
# =====================================================================
with tabs[4]:
    seo = DATA["seo"]; sc = period_frac; psc = period_frac * 0.86
    r = st.columns(6)
    kpi(r[0], "Sessions (GA4)", fmt_compact(seo["sessions"] * sc),
        delta_html(seo["sessions"] * sc, seo["sessions"] * psc, suffix=""))
    kpi(r[1], "Engaged Sess.", fmt_compact(seo["engaged"] * sc),
        delta_html(seo["engaged"] * sc, seo["engaged"] * psc, suffix=""))
    kpi(r[2], "GA4 Conv.", fmt_int(seo["ga4_conv"] * sc),
        delta_html(seo["ga4_conv"] * sc, seo["ga4_conv"] * psc, suffix=""))
    kpi(r[3], "GSC Clicks", fmt_compact(seo["gsc_clicks"] * sc),
        delta_html(seo["gsc_clicks"] * sc, seo["gsc_clicks"] * psc, suffix=""))
    kpi(r[4], "GSC Impr.", fmt_compact(seo["gsc_impr"] * sc),
        delta_html(seo["gsc_impr"] * sc, seo["gsc_impr"] * psc, suffix=""))
    kpi(r[5], "Avg Position", f"{seo['avg_position']:.1f}",
        '<span style="color:#15803d;">▲ 2.1 spots</span>')

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            panel_title("Top Pages — GA4")
            tp = pd.DataFrame(DATA["top_pages"], columns=["Page", "Sessions", "Conv."])
            tp["Sessions"] = (tp["Sessions"] * sc).round().astype(int)
            tp["Conv."] = (tp["Conv."] * sc).round().astype(int)
            html = ['<table class="grid"><tr><th>Page</th><th>Sessions</th><th>Conv.</th></tr>']
            for _, row in tp.iterrows():
                html.append(f"<tr><td style='color:#1d4ed8;'>{row['Page']}</td>"
                            f"<td>{row['Sessions']:,}</td><td>{row['Conv.']}</td></tr>")
            st.markdown("".join(html) + "</table>", unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            panel_title("Top Search Queries — GSC")
            tq = pd.DataFrame(DATA["top_queries"], columns=["Query", "Clicks", "Position"])
            tq["Clicks"] = (tq["Clicks"] * sc).round().astype(int)
            html = ['<table class="grid"><tr><th>Query</th><th>Clicks</th><th>Pos.</th></tr>']
            for _, row in tq.iterrows():
                html.append(f"<tr><td style='color:#b45309;'>{row['Query']}</td>"
                            f"<td>{row['Clicks']:,}</td><td>{row['Position']:.1f}</td></tr>")
            st.markdown("".join(html) + "</table>", unsafe_allow_html=True)

    with st.container(border=True):
        panel_title("Blog → Lead Attribution",
                    '<span class="pill" style="background:#fef9c3;color:#854d0e;">Pending Zainab\'s automation</span>')
        st.markdown("<div style='color:#9aa0a6;font-size:13px;'>UI built and ready. Once the GHL "
                    "custom field for blog source is populated, this section will auto-display "
                    "lead count per blog post, top-converting blog content, and the "
                    "SEO → consultation pipeline.</div>", unsafe_allow_html=True)

# =====================================================================
# 6 · FORECAST & GOALS
# =====================================================================
with tabs[5]:
    fc = DATA["forecast"]
    actual = fc[fc["kind"] == "Actual"].reset_index(drop=True)
    forecast = fc[fc["kind"] == "Forecast"].reset_index(drop=True)
    na, nf = len(actual), len(forecast)

    with st.container(border=True):
        panel_title("30-Day Lead Forecast", "Prophet model · 95% confidence interval")
        xf = list(range(na + 1, na + nf + 1))
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=xf + xf[::-1], y=list(forecast["upper"]) + list(forecast["lower"][::-1]),
            fill="toself", fillcolor="rgba(59,130,246,0.13)", line=dict(color="rgba(0,0,0,0)"),
            hoverinfo="skip", name="Confidence band"))
        fig.add_trace(go.Scatter(
            x=list(range(1, na + 1)), y=actual["value"], mode="lines",
            line=dict(color="#6b7280", width=2), name="Actual (last 30d)"))
        fig.add_trace(go.Scatter(
            x=xf, y=forecast["value"], mode="lines",
            line=dict(color=C_BLUE, width=2.5, dash="dash"), name="Forecast (next 30d)"))
        vals = list(range(1, na + 1, 6)) + list(range(na + 1, na + nf + 1, 6))
        txt = [f"D{v}" for v in range(1, na + 1, 6)] + [f"F{v-na}" for v in range(na + 1, na + nf + 1, 6)]
        fig.update_xaxes(tickmode="array", tickvals=vals, ticktext=txt, showgrid=False)
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10),
                          paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG, hovermode="x unified",
                          legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)),
                          yaxis=dict(showgrid=True, gridcolor="#eef0f2"))
        st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            panel_title("Goal Pacing — Next Month Projection")
            target = 160
            projected = 142
            gap = projected - target
            need = max(0, -gap)
            pace = [
                ("COE Target (Dec)", f"{target}"),
                ("Projected at current pace", f"{projected}"),
                ("Gap", f"{gap:+d} COEs"),
                ("Leads needed at 9.7% rate", f"+{int(round(need/0.097))} leads"),
                ("Additional spend at $42 CPL", f"${int(round(need/0.097))*42:,.0f}"),
            ]
            for lbl, val in pace:
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;padding:11px 2px;"
                    f"border-bottom:1px solid #f1f3f5;'><span style='color:#374151;font-size:13px;'>{lbl}</span>"
                    f"<span style='font-weight:700;color:#b45309;'>{val}</span></div>",
                    unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            panel_title("Smart Recommendations")
            recs = [
                "Reallocate $850/wk from 'Visa-Ext-Mel-V3' (CPL $112) to 'PR-Pathway-IT-Mel' (CPL $35). Estimated yield: +24 leads/wk, +2.3 COEs/wk.",
                "Increase Sydney 485 budget by $1,200/wk. Recent Sydney CPL dropped 23% — capacity exists at strong CPL. Estimated +27 leads/wk.",
                "Coach Manhal on close stage — 47% drop between Showed and Paid vs 32% team avg. If brought to team avg: +3 COEs/month.",
                "Add SMS reminder for Wajahat's calendar. Show rate 67.6% vs 81% on Nasir's. Lifting to team-best: +9 shows/month.",
            ]
            for t in recs:
                st.markdown(f'<div class="insight" style="background:#eff6ff;border-left:3px solid #1d4ed8;">{t}</div>',
                            unsafe_allow_html=True)

    # ---- Bonus: interactive scenario simulator ----
    with st.container(border=True):
        panel_title("Scenario Simulator", "interactive")
        st.caption("Drag the levers to model next month — the projections recompute live.")
        s1, s2, s3 = st.columns(3)
        weekly_spend = s1.slider("Weekly ad spend ($)", 2_000, 20_000, 8_000, 500)
        cpl_input = s2.slider("Target CPL ($)", 25, 90, 42, 1)
        conv_rate = s3.slider("Lead → COE rate (%)", 5.0, 15.0, 9.7, 0.1)
        sim_leads = int(weekly_spend / cpl_input * 4.3)
        sim_coes = int(sim_leads * conv_rate / 100)
        m = st.columns(3)
        m[0].metric("Projected leads / month", f"{sim_leads:,}")
        m[1].metric("Projected COEs / month", f"{sim_coes:,}", delta=f"{sim_coes-160:+d} vs target")
        m[2].metric("Cost per COE", f"${weekly_spend*4.3/max(1,sim_coes):,.0f}")

# =====================================================================
# 7 · UPLOAD REPORTS
# =====================================================================
with tabs[6]:
    up = pd.DataFrame(DATA["uploads"],
                      columns=["Filename", "Type", "Rows", "Period", "Uploaded", "Status"])
    pending = int((up["Status"] != "Ingested").sum())

    ur = st.columns(4)
    kpi(ur[0], "Reports Uploaded", str(len(up)), "", "last 30 days")
    kpi(ur[1], "Rows Ingested", fmt_compact(int(up["Rows"].sum())))
    kpi(ur[2], "Pending Mapping", str(pending),
        ('<span style="color:#b45309;">⚠ needs attention</span>' if pending
         else '<span style="color:#15803d;">✓ all clear</span>'))
    kpi(ur[3], "Last Upload", "2 days ago", "", "monthly_summary_oct_2026.xlsx")

    st.write("")
    with st.container(border=True):
        panel_title("Upload Monthly Report", "CSV, Excel, PDF supported")
        st.file_uploader(
            "Drag & drop a file here, or click to browse — CSV, XLSX, PDF up to 25MB. "
            "System auto-detects schema. (Demo — uploads are not processed.)",
            type=["csv", "xlsx", "pdf"], accept_multiple_files=False)

    with st.container(border=True):
        panel_title("Recently Uploaded Reports")
        sp = {"Ingested": ("#dcfce7", "#166534"), "Mapping needed": ("#fef3c7", "#92400e")}
        html = ['<table class="grid"><tr><th>Filename</th><th>Type</th><th>Rows</th>'
                '<th>Period</th><th>Uploaded</th><th>Status</th></tr>']
        for _, row in up.iterrows():
            bg, fg = sp.get(row["Status"], ("#eee", "#333"))
            html.append(
                f"<tr><td style='color:#1d4ed8;'>{row['Filename']}</td><td>{row['Type']}</td>"
                f"<td>{row['Rows']}</td><td>{row['Period']}</td><td>{row['Uploaded']}</td>"
                f"<td><span class='pill' style='background:{bg};color:{fg};'>{row['Status']}</span></td></tr>")
        st.markdown("".join(html) + "</table>", unsafe_allow_html=True)

    tcol, bcol = st.columns([3, 2])
    with tcol:
        with st.container(border=True):
            panel_title("Trend From Uploaded Data", "Last 12 months")
            ut = DATA["upload_trend"]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=ut["month"], y=ut["leads"], name="Leads", marker_color=C_BLUE))
            fig.add_trace(go.Bar(x=ut["month"], y=ut["coes"], name="COEs", marker_color=C_GREEN))
            fig.update_layout(barmode="group", height=310, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
                              legend=dict(orientation="h", y=1.12, x=0),
                              xaxis=dict(showgrid=False, tickformat="%b %y"),
                              yaxis=dict(showgrid=True, gridcolor="#eef0f2"))
            st.plotly_chart(fig, width="stretch")
    with bcol:
        with st.container(border=True):
            panel_title("Rows by Report Type")
            bt = up.groupby("Type")["Rows"].sum().sort_values(ascending=False)
            figt = go.Figure(go.Bar(x=bt.values, y=bt.index, orientation="h",
                                     marker_color=C_PURPLE, text=bt.values, textposition="outside"))
            figt.update_layout(height=310, margin=dict(l=10, r=10, t=10, b=10),
                               paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
                               xaxis=dict(showgrid=True, gridcolor="#eef0f2", title="rows"),
                               yaxis=dict(autorange="reversed"))
            st.plotly_chart(figt, width="stretch")

st.markdown(
    '<div style="text-align:center;color:#9aa0a6;font-size:12px;margin-top:16px;">'
    'The Migration · Demo Dashboard · Built with Streamlit · Python · All data simulated · '
    'Data sources: GHL · Meta Ads · GA4 · GSC</div>',
    unsafe_allow_html=True)
