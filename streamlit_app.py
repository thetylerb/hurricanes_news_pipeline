# streamlit_app.py
import os
import pandas as pd
import streamlit as st
import altair as alt
from supabase import create_client
from dotenv import load_dotenv

# --- Setup ---
load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))
LOCAL_TZ = os.getenv("LOCAL_TZ", "UTC")  # Set to "US/Eastern" if you want local time

st.set_page_config(page_title="Hurricanes News Dashboard", layout="wide")
st.title("🏒 Hurricanes News Dashboard")

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    res = sb.table("articles").select("*").order("published_at", desc=True).limit(200).execute()
    df = pd.DataFrame(res.data or [])
    if df.empty:
        return df

    # ---- Robust datetime handling for 'published_at' ----
    pub = df.get("published_at")

    if pub is None:
        dt = pd.to_datetime([], utc=True)
    else:
        if pd.api.types.is_datetime64_any_dtype(pub):
            # Already datetime-like: handle tz
            dt = pub
            try:
                _ = dt.dt.tz  # raises if no datetime accessor
                dt = dt.dt.tz_localize("UTC") if dt.dt.tz is None else dt.dt.tz_convert("UTC")
            except Exception:
                dt = pd.to_datetime(pub, errors="coerce", utc=True)
        else:
            # Strings / mixed objects
            dt = pd.to_datetime(pub, errors="coerce", utc=True)

    # Optional: convert to local timezone
    try:
        dt_local = dt.dt.tz_convert(LOCAL_TZ) if LOCAL_TZ and LOCAL_TZ != "UTC" else dt
    except Exception:
        dt_local = dt  # fallback to UTC

    df["published_at"] = dt_local
    df["date"] = df["published_at"].dt.date

    # ---- Cleaning / presentation helpers ----
    df = df[~df["id"].astype(str).str.startswith("test_")]  # drop test row
    df["author"] = df["author"].fillna("Unknown")
    df["link"] = df.get("source_url")

    return df

# ---- Load and render ----
df = load_data()

if df.empty:
    st.info("No data yet. Run collect → structure → load.")
else:
    st.subheader("All Articles")
    show = df[["title", "author", "date", "link", "summary"]]

    st.dataframe(
        show,
        use_container_width=True,
        hide_index=True,
        column_config={"link": st.column_config.LinkColumn("link", display_text="open")},
    )

    left, right = st.columns(2)

    # Articles per day
    with left:
        st.subheader("Articles per day")
        daily = (
            df.dropna(subset=["date"])
              .groupby("date")
              .size()
              .reset_index(name="count")
        )
        chart = alt.Chart(daily).mark_bar().encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("count:Q", title="Articles"),
            tooltip=["date:T", "count:Q"],
        )
        st.altair_chart(chart, use_container_width=True)

    # Top authors
    with right:
        st.subheader("Top authors")
        # Use reset_index(name="count") to avoid duplicate column names
        top = df["author"].value_counts().reset_index(name="count").rename(columns={"index": "author"}).head(10)
        chart = alt.Chart(top).mark_bar().encode(
            x=alt.X("count:Q", title="Articles"),
            y=alt.Y("author:N", sort="-x", title="Author"),
            tooltip=["author:N", "count:Q"],
        )
        st.altair_chart(chart, use_container_width=True)
