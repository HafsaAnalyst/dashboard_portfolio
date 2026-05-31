# The Migration — Unified Analytics Dashboard (Portfolio Demo)

A self-contained, interactive analytics dashboard for a migration & education
agency. Built with **Streamlit + Plotly**. Every number is **simulated** — there
is no database or API behind it, so it runs anywhere and can be shared with
anyone as a portfolio piece.

![tabs](Executive · Meta Ads · Funnel & Pipeline · Counsellors · SEO & Traffic · Forecast & Goals · Upload Reports)

## What it shows

| Tab | Highlights |
|-----|-----------|
| **Executive** | 9 KPI cards, goal-progress bars, stacked lead-trend chart, auto-insights, source-mix donut, Visa-vs-Education comparison |
| **Meta Ads** | Spend / impressions / clicks / CTR / CPL KPIs, per-account (Melbourne / Sydney) panels with daily CPL charts, campaign-performance table with Scale/Keep/Optimize/Kill status |
| **Funnel & Pipeline** | 7-stage lead-to-outcome funnel, pipeline split donut, post-consultation loss reasons |
| **Counsellors** | Performance matrix (fill %, show %, conversion), drop-off heatmap |
| **SEO & Traffic** | GA4 + GSC KPIs, top pages, top search queries |
| **Forecast & Goals** | 30-day lead forecast with confidence band, goal pacing, smart recommendations |
| **Upload Reports** | File-upload UI, recent-uploads table, 12-month trend |

## Interactive filters

The **Period** (Last 7 / 30 / 90 days, current month, custom range) and **City**
(All / Melbourne / Sydney / …) selectors at the top are fully wired. Changing
either re-slices the underlying simulated dataset and **every** KPI, chart and
table recomputes live — they're not just labels.

## Run it locally

```bash
cd portfolio_dashboard
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## Deploy it (free) for your portfolio

1. Push this folder to a public GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), connect the repo, and
   set the main file to `portfolio_dashboard/app.py`.
3. You get a public URL you can link from your CV / portfolio.

## How it works

- **`sample_data.py`** — deterministic data generator (fixed RNG seed). Produces
  one row per lead across ~150 days of history, plus daily Meta ad spend, a lead
  forecast, and calibrated base tables for the counsellor / SEO tabs. Every
  record is date-stamped and city-tagged so the filters genuinely change the data.
- **`app.py`** — the Streamlit UI. Slices the generated data by the selected
  period & city, computes KPIs and deltas vs the prior equal-length window, and
  renders all seven tabs.

Built as a portfolio demonstration of a real product design — the production
version connects to GoHighLevel (GHL), Meta Ads, GA4 and Google Search Console.
