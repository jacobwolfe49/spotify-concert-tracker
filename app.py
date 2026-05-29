import streamlit as st
import pandas as pd
import requests
from collections import Counter
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Denver Concert Deal Tracker",
    layout="wide",
    page_icon="🎵"
)

# =====================================================
# API KEY
# =====================================================

TICKETMASTER_API_KEY = st.secrets["TICKETMASTER_API_KEY"]

# =====================================================
# TITLE
# =====================================================

st.title("🎵 Denver Concert Deal Tracker")
st.caption("Concert discovery powered by your Spotify history")

# =====================================================
# LOAD CSV
# =====================================================

uploaded_file = st.file_uploader(
    "Upload your Spotify liked songs CSV",
    type=["csv"]
)

if uploaded_file is None:
    st.info("Upload your Spotify export to begin")
    st.stop()

songs_df = pd.read_csv(uploaded_file)

# =====================================================
# DETECT ARTIST COLUMN
# =====================================================

possible_columns = [
    "Artist Name(s)",
    "artist",
    "artists",
    "Artist"
]

artist_column = None

for col in possible_columns:
    if col in songs_df.columns:
        artist_column = col
        break

if artist_column is None:
    st.error("Could not find artist column")
    st.stop()

# =====================================================
# EXTRACT ARTISTS
# =====================================================

all_artists = []

for value in songs_df[artist_column].dropna():
    artists = str(value).replace(",", ";").split(";")
    artists = [a.strip() for a in artists if a.strip()]
    all_artists.extend(artists)

artist_counts = Counter(all_artists)

artist_df = pd.DataFrame(
    artist_counts.items(),
    columns=["artist", "song_count"]
)

artist_df = artist_df.sort_values(
    "song_count",
    ascending=False
)

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Dashboard Settings")

TOP_N = st.sidebar.slider(
    "Artists To Track",
    25,
    300,
    100
)

MAX_PRICE = st.sidebar.slider(
    "Maximum Ticket Price",
    0,
    500,
    150
)

artist_df = artist_df.head(TOP_N)

# =====================================================
# TICKETMASTER SEARCH
# =====================================================

@st.cache_data(ttl=3600)
def search_ticketmaster(artist_name):

    url = "https://app.ticketmaster.com/discovery/v2/events.json"

    params = {
        "apikey": TICKETMASTER_API_KEY,
        "keyword": artist_name,
        "stateCode": "CO",
        "city": "Denver",
        "size": 5,
        "sort": "date,asc"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()

        events = []

        embedded = data.get("_embedded", {})
        tm_events = embedded.get("events", [])

        for event in tm_events:

            venue = "Unknown"

            if "_embedded" in event:
                venues = event["_embedded"].get("venues", [])
                if venues:
                    venue = venues[0].get("name")

           min_price = "N/A"

if "priceRanges" in event:
    ranges = event["priceRanges"]

    if ranges:
        possible_price = ranges[0].get("min")

        if possible_price is not None:
            min_price = round(float(possible_price), 2)

            events.append({
                "artist": artist_name,
                "event": event.get("name"),
                "venue": venue,
                "date": event.get("dates", {}).get("start", {}).get("localDate"),
                "price": min_price,
                "url": event.get("url"),
                "source": "Ticketmaster"
            })

        return events

    except Exception:
        return []

# =====================================================
# SEARCH BUTTON
# =====================================================

if st.button("🔎 Find Denver Concerts"):

    progress = st.progress(0)

    all_events = []

    for idx, row in enumerate(artist_df.itertuples()):

        artist = row.artist

        tm_results = search_ticketmaster(artist)

        all_events.extend(tm_results)

        progress.progress((idx + 1) / len(artist_df))

    if len(all_events) == 0:
        st.warning("No concerts found")
        st.stop()

    events_df = pd.DataFrame(all_events)

    # REMOVE DUPLICATES

    events_df = events_df.drop_duplicates(
        subset=["artist", "event", "date"]
    )

    # DEAL RATING

    def deal_rating(price):

       if price == "N/A":
    return "Unknown"

        if price < 40:
            return "🔥 Amazing"

        if price < 80:
            return "🟢 Good"

        if price < 150:
            return "🟡 Average"

        return "🔴 Expensive"

    events_df["deal"] = events_df["price"].apply(deal_rating)

    # FILTERS

    (events_df["price"] == "N/A") |
(events_df["price"] <= MAX_PRICE)
    ]

    # SORT

    events_df = events_df.sort_values(
        by="price",
        ascending=True,
        na_position="last"
    )

    # METRICS

    col1, col2, col3 = st.columns(3)

    col1.metric("Concerts Found", len(events_df))

    cheap_count = len(
        events_df[
            events_df["deal"].isin([
                "🔥 Amazing",
                "🟢 Good"
            ])
        ]
    )

    col2.metric("Good Deals", cheap_count)

    col3.metric(
        "Artists Touring",
        events_df["artist"].nunique()
    )

    # TABLE

    st.subheader("🎫 Upcoming Concerts")

    st.dataframe(
        events_df,
        use_container_width=True,
        height=700
    )

    # CHART

    st.subheader("📊 Cheapest Upcoming Concerts")

    chart_df = events_df.dropna(subset=["price"])

    if len(chart_df) > 0:

        chart_df = chart_df.head(20)

        fig = px.bar(
            chart_df,
            x="artist",
            y="price",
            hover_data=["venue", "date"],
            title="Lowest Ticket Prices"
        )

        st.plotly_chart(fig, use_container_width=True)

    # DEALS SECTION

    st.subheader("🔥 Best Deals")

    deals = events_df[
        events_df["deal"].isin([
            "🔥 Amazing",
            "🟢 Good"
        ])
    ]

    for row in deals.head(15).itertuples():

        st.markdown(f"""
        ### {row.artist}

        **Venue:** {row.venue}

        **Date:** {row.date}

        **Lowest Ticket:** ${row.price}

        **Rating:** {row.deal}

        [Buy Tickets]({row.url})

        ---
        """)

# =====================================================
# TOP ARTISTS
# =====================================================

st.sidebar.subheader("Top Artists")

st.sidebar.dataframe(
    artist_df.head(25),
    use_container_width=True
)
