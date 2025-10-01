import os, pandas as pd, streamlit as st, altair as alt
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_ANON_KEY"))

st.set_page_config(page_title="Hurricanes News Dashboard", layout="wide")
st.title("🏒 Hurricanes News Dashboard")

@st.cache_data(ttl=300)
def load_data():
    res = sb.table("articles").select("*").order("published_at", desc=True).limit(200).execute()
    df = pd.DataFrame(res.data or [])
    if not df.empty:
        # clean
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
        df = df[~df["id"].astype(str).str.startswith("test_")]  # hide the test insert
        df["author"] = df["author"].fillna("Unknown")
        # pretty link column
        if "source_url" in df.columns:
            df["link"] = df.apply(
                lambda r: f"[open]({r['source_url']})" if pd.notna(r.get("source_url")) else "",
                axis=1
            )
    return df

df = load_data()

if df.empty:
    st.info("No data yet. Run collect → structure → load.")
else:
    # compact table
    show = df[["title", "author", "published_at", "link", "summary"]].rename(
        columns={"published_at": "date"}
    )
    st.subheader("All Articles")
    st.dataframe(show, use_container_width=True, hide_index=True)

    left, right = st.columns(2)

    # Articles per day
    with left:
        st.subheader("Articles per day")
        daily = df.assign(date=df["published_at"].dt.date).groupby("date").size().reset_index(name="count")
        chart = alt.Chart(daily).mark_bar().encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("count:Q", title="Articles"),
            tooltip=["date:T", "count:Q"]
        )
        st.altair_chart(chart, use_container_width=True)

    # Top authors
    with right:
        st.subheader("Top authors")
        top = df["author"].value_counts().reset_index()
        top.columns = ["author", "count"]
        top = top.head(10)
        chart = alt.Chart(top).mark_bar().encode(
            x=alt.X("count:Q", title="Articles"),
            y=alt.Y("author:N", sort="-x", title="Author"),
            tooltip=["author:N", "count:Q"]
        )
        st.altair_chart(chart, use_container_width=True)
