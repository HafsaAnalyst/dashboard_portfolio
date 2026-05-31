"""
Sample-data generator for the portfolio dashboard.

Everything here is SIMULATED. No external API, no database — the whole
dashboard runs off the deterministic data built in this module so it can be
dropped into a portfolio and opened by anyone.

Design goals
------------
* Deterministic — a fixed RNG seed means the numbers are identical on every
  machine and every reload (good for screenshots / demos).
* Date-stamped — every lead, ad-spend row and appointment carries a real date,
  so the Period filter (Last 7 days / 30 days / etc.) actually changes the KPIs.
* City-tagged — every record carries a city, so the City filter actually
  re-slices the data instead of just re-labelling it.

The single source of truth is `leads_df` (one row per lead). The Executive,
Funnel and Forecast tabs are derived live from it; the Meta, Counsellor and SEO
tabs use calibrated base tables that are scaled to the selected window. That
mix keeps the demo numbers close to the reference screenshots while still
responding to the filters.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

# A fixed "today" keeps the generated window stable for the portfolio demo,
# independent of the real wall-clock date.
TODAY = date(2026, 5, 30)
HISTORY_DAYS = 150  # how far back the simulated history runs

SEED = 42

CITIES = ["Melbourne", "Sydney", "Others", "Unidentified"]
CITY_WEIGHTS = [0.42, 0.40, 0.13, 0.05]

SOURCES = ["Meta Paid", "Organic / SEO", "Chatbot", "Referral", "Other"]
SOURCE_WEIGHTS = [0.54, 0.21, 0.16, 0.06, 0.03]
SOURCE_COLORS = {
    "Meta Paid":     "#3b82f6",
    "Organic / SEO": "#10b981",
    "Chatbot":       "#ef4444",
    "Referral":      "#9ca3af",
    "Other":         "#8b5cf6",
}

PIPELINES = ["Visa", "Education"]
PIPELINE_WEIGHTS = [0.55, 0.45]

VISA_TYPES = [
    "485 Visa", "PR Pathway", "Student Visa", "Partner Visa",
    "Nursing PR", "Master Course", "Diploma",
]

CAMPAIGNS = [
    # (name, account, base_daily_spend, cpl_bias)
    ("PR-Pathway-IT-Mel",      "Melbourne", 195, 0.85),
    ("485-Visa-Extension-Syd", "Sydney",    164, 0.90),
    ("Education-Diploma-Mel",  "Melbourne", 140, 1.05),
    ("Partner-Visa-Combined",  "Both",      129, 1.05),
    ("PR-Pathway-Nursing-Syd", "Sydney",    118, 1.08),
    ("Master-Course-Mel",      "Melbourne",  94, 1.15),
    ("Visa-Ext-Mel-V3",        "Melbourne",  71, 2.70),
    ("TR-to-PR-Combined",      "Both",       37, 0.70),
]

# ---------------------------------------------------------------------
# Counsellors — base figures are calibrated to ~30 days, "All cities".
# city = the counsellor's OFFICE (Gurbir + Navneet work out of Melbourne).
# ---------------------------------------------------------------------
COUNSELLOR_BASE = [
    # name,            short,       type,          city,        slots, booked, showed, convert
    ("Nasir Nawaz",    "Nasir N.",  "Paid · RMA",  "Sydney",    48,  42, 34, 14),
    ("Gurbir Singh",   "Gurbir S.", "Paid · MARA", "Melbourne", 56,  49, 38, 15),
    ("Syed Turab Raza","Turab R.",  "Paid",        "Sydney",    72,  54, 40, 14),
    ("Wajahat Ghafoor","Wajahat G.","Free · TL",   "Sydney",    96,  71, 48, 12),
    ("Saurab Gautam",  "Saurab G.", "Free",        "Sydney",    80,  54, 39, 10),
    ("Kajal Garg",     "Kajal G.",  "Free",        "Sydney",    80,  52, 37,  9),
    ("Navneet Kaur",   "Navneet K.","Free · Mel",  "Melbourne", 72,  44, 30,  8),
    ("Manhal Dandachi","Manhal D.", "Free · Admin","Sydney",    56,  34, 23,  4),
]

# Heatmap — leads dropping off per counsellor, per pipeline stage (~30 days).
HEATMAP_BASE = [
    # counsellor, Booked, Showed, Initial Req., Paid, COE
    ("Nasir N.",   42, 34, 22, 18, 14),
    ("Gurbir S.",  49, 38, 24, 19, 15),
    ("Wajahat G.", 71, 48, 22, 15, 12),
    ("Manhal D.",  34, 23,  9,  5,  4),
    ("Others",    236,166,101, 64, 44),
]

# SEO — base figures calibrated to ~30 days.
SEO_BASE = {
    "sessions":      42800,
    "engaged":       28100,
    "ga4_conv":      218,
    "gsc_clicks":    8400,
    "gsc_impr":      186000,
    "avg_position":  14.2,
}

TOP_PAGES = [
    ("/485-visa-guide",          4820, 38),
    ("/pr-pathway-it",           3940, 31),
    ("/student-visa-extension",  3210, 24),
    ("/partner-visa-australia",  2870, 22),
    ("/coe-vs-voe-explained",    2540, 18),
    ("/nursing-pr-pathway",      2180, 16),
    ("/melbourne-visa-services", 1920, 14),
]

TOP_QUERIES = [
    ("485 visa extension",        842, 4.2),
    ("pr pathway it australia",   721, 6.8),
    ("visa agent melbourne",      612, 8.1),
    ("partner visa australia cost",538, 11.3),
    ("coe certificate enrolment", 484, 5.6),
    ("student visa renewal sydney",421, 9.2),
    ("mara agent harris park",    398, 3.4),
]

LOSS_REASONS = [
    ("Went to Competitor",        0.31),
    ("Price / Fees Too High",     0.24),
    ("Needs More Time",           0.18),
    ("Not Eligible (We Declined)",0.15),
    ("Said No After Consultation",0.12),
]

UPLOADS = [
    ("monthly_summary_oct_2026.xlsx",     "Monthly",   284, "Oct 2026",  "2 days ago",  "Ingested"),
    ("counsellor_paid_consults_q3.csv",   "Quarterly", 142, "Q3 2026",   "1 week ago",  "Ingested"),
    ("partner_visa_outcomes.xlsx",        "Custom",     67, "2026 YTD",  "2 weeks ago", "Ingested"),
    ("budget_actuals_oct.csv",            "Finance",    48, "Oct 2026",  "3 weeks ago", "Mapping needed"),
]


# =====================================================================
# Generation
# =====================================================================

def _build_leads(rng_vol: np.random.Generator, rng: np.random.Generator) -> pd.DataFrame:
    """One row per lead across the simulated history window.

    Two independent RNG streams: `rng_vol` decides how many leads land each day,
    `rng` decides each lead's attributes. Keeping them separate means tuning an
    outcome probability (e.g. the COE rate) no longer perturbs the daily volume.
    """
    start = TODAY - timedelta(days=HISTORY_DAYS - 1)
    rows = []
    lead_id = 0
    for d_off in range(HISTORY_DAYS):
        day = start + timedelta(days=d_off)
        dow = day.weekday()  # 0=Mon .. 6=Sun

        # Volume: gentle upward trend + weekday seasonality + noise.
        # Calibrated so the last-30-day window totals ~1,240 leads (the demo
        # baseline that the reference screenshots show).
        trend = 1.0 + 0.45 * (d_off / HISTORY_DAYS)
        weekday_factor = 0.55 if dow >= 5 else 1.0
        base = 34 * trend * weekday_factor
        n = max(0, int(rng_vol.normal(base, base * 0.18)))

        for _ in range(n):
            lead_id += 1
            city = rng.choice(CITIES, p=CITY_WEIGHTS)
            source = rng.choice(SOURCES, p=SOURCE_WEIGHTS)
            pipeline = rng.choice(PIPELINES, p=PIPELINE_WEIGHTS)
            visa_type = rng.choice(VISA_TYPES)

            # Funnel — each stage conditional on the previous one.
            # Rates calibrated to the screenshot baseline:
            #   booked 34.6% · show 71.4% · show→convert 28.9%.
            booked = rng.random() < 0.346
            showed = booked and (rng.random() < 0.714)
            converted = showed and (rng.random() < 0.289)

            # COE / VOE are issued outcomes, tracked independently of the
            # consult "converted" flag (a contact can be issued a COE without a
            # paid consult, etc.). Probabilities tuned so the 30-day window
            # yields ~87 COEs and ~34 VOEs.
            is_coe = pipeline == "Education" and rng.random() < 0.166
            is_voe = pipeline == "Visa" and rng.random() < 0.054
            issued = is_coe or is_voe

            # Revenue lands on issued outcomes, avg ~$1.5k → ~$184k for 30 days
            # (6.5x ROAS against ~$28.4k ad spend).
            revenue = float(rng.choice([1100, 1300, 1500, 1700, 2000])) if issued else 0.0

            rows.append({
                "lead_id":   lead_id,
                "date":      pd.Timestamp(day),
                "city":      city,
                "source":    source,
                "pipeline":  pipeline,
                "visa_type": visa_type,
                "booked":    booked,
                "showed":    showed,
                "converted": converted,
                "is_coe":    is_coe,
                "is_voe":    is_voe,
                "revenue":   revenue,
            })
    return pd.DataFrame(rows)


def _build_meta_daily(rng: np.random.Generator) -> pd.DataFrame:
    """Daily Meta ad spend per campaign (drives the Meta Ads tab)."""
    start = TODAY - timedelta(days=HISTORY_DAYS - 1)
    rows = []
    for d_off in range(HISTORY_DAYS):
        day = start + timedelta(days=d_off)
        for name, account, base_spend, cpl_bias in CAMPAIGNS:
            # No trend/seasonality on spend, so each campaign's 30-day total
            # lands on its calibrated daily base × 30 (matches the screenshot
            # Campaign Performance table, e.g. PR-Pathway-IT-Mel ≈ $5,840).
            spend = max(0.0, rng.normal(base_spend, base_spend * 0.10))
            # ~1.68% CTR, ~$2 CPC implied; derive impressions/clicks/leads from spend.
            clicks = spend / rng.uniform(1.8, 2.4)
            impressions = clicks / rng.uniform(0.014, 0.020)
            cpl = 42 * cpl_bias * rng.uniform(0.9, 1.1)
            leads = spend / cpl
            rows.append({
                "date":        pd.Timestamp(day),
                "campaign":    name,
                "account":     account,
                "spend":       spend,
                "impressions": impressions,
                "clicks":      clicks,
                "leads":       leads,
                "cpl_bias":    cpl_bias,
            })
    return pd.DataFrame(rows)


def _build_forecast(leads_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """30 days of actuals + 30 days of forecast with a confidence band."""
    actual = (
        leads_df[leads_df["date"] >= pd.Timestamp(TODAY - timedelta(days=29))]
        .groupby("date").size().reset_index(name="value")
    )
    actual["kind"] = "Actual"
    actual["lower"] = np.nan
    actual["upper"] = np.nan

    # Forecast = last value carried forward with a mild upward drift + widening band.
    last_val = actual["value"].tail(7).mean() if not actual.empty else 40
    fc_rows = []
    for i in range(1, 31):
        day = pd.Timestamp(TODAY + timedelta(days=i))
        drift = last_val * (1 + 0.012 * i)
        season = 0.85 if day.weekday() >= 5 else 1.05
        mid = drift * season
        spread = mid * (0.10 + 0.012 * i)
        fc_rows.append({
            "date":  day,
            "value": mid,
            "kind":  "Forecast",
            "lower": max(0, mid - spread),
            "upper": mid + spread,
        })
    forecast = pd.DataFrame(fc_rows)
    return pd.concat([actual, forecast], ignore_index=True)


def _build_upload_trend(rng: np.random.Generator) -> pd.DataFrame:
    """Last 12 months of leads + COEs (drives the Upload Reports bar chart)."""
    months = pd.date_range(end=pd.Timestamp(TODAY).replace(day=1), periods=12, freq="MS")
    rows = []
    for i, m in enumerate(months):
        leads = int(800 + i * 55 + rng.normal(0, 40))
        coes = int(leads * rng.uniform(0.07, 0.10))
        rows.append({"month": m, "leads": leads, "coes": coes})
    return pd.DataFrame(rows)


def build_data() -> dict:
    # Independent streams so each builder is reproducible in isolation.
    leads_df = _build_leads(np.random.default_rng(SEED), np.random.default_rng(SEED + 1))
    meta_daily = _build_meta_daily(np.random.default_rng(SEED + 2))
    forecast = _build_forecast(leads_df, np.random.default_rng(SEED + 3))
    upload_trend = _build_upload_trend(np.random.default_rng(SEED + 4))
    return {
        "today":        TODAY,
        "leads":        leads_df,
        "meta_daily":   meta_daily,
        "forecast":     forecast,
        "upload_trend": upload_trend,
        "counsellors":  COUNSELLOR_BASE,
        "heatmap":      HEATMAP_BASE,
        "seo":          SEO_BASE,
        "top_pages":    TOP_PAGES,
        "top_queries":  TOP_QUERIES,
        "loss_reasons": LOSS_REASONS,
        "uploads":      UPLOADS,
        "campaigns":    CAMPAIGNS,
        "source_colors": SOURCE_COLORS,
    }
