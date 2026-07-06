"""
app.py

Streamlit dashboard for Rory's Travel Club deals.

This file is UI only -- it doesn't know how cards are assembled (that's
queries.py) or how filtering/sorting works (that's filters.py). It just
asks for DealCards and renders them.

Run with:
    streamlit run app.py
"""

import re
import streamlit as st

from scraper import sync_database, LOCATIONS
from queries import get_deal_cards, get_known_counties, get_known_provinces, get_known_travel_origins
from filters import filter_deals, sort_deals, SORT_OPTIONS


st.set_page_config(page_title="Rory's Travel Club — Deals Board", page_icon="🧳", layout="wide")

st.markdown("""
<style>
div[data-testid="stImage"] img {
    height: 160px;
    object-fit: cover;
    border-radius: 8px;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    position: relative;
}

button[kind="secondary"][data-testid="baseButton-secondary"].card-overlay-btn {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    z-index: 1;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)


@st.dialog("Deal details")
def show_deal(deal):
    st.image(deal.image_url, use_container_width=True)
    st.markdown(f"**{deal.hotel.strip().title()}**")
    st.write(deal.description)
    if deal.rating is not None:
        st.markdown(f"⭐ {deal.rating:.1f} ({deal.review_count or 0} reviews, {deal.review_source or 'n/a'})")
    if deal.travel_minutes is not None:
        st.markdown(f"🚗 {deal.travel_minutes} min away")
    if deal.min_price is not None:
        st.markdown(f"💶 from {deal.currency or ''}{deal.min_price:.0f}")
    if deal.offer_url:
        st.link_button("View deal ↗", deal.offer_url)


# --- Sidebar: data controls -------------------------------------------------
st.sidebar.header("Data")

travel_origins = get_known_travel_origins()
travel_origin = st.sidebar.selectbox("Travel time from", ["(none)"] + travel_origins)
travel_origin = None if travel_origin == "(none)" else travel_origin

if st.sidebar.button("🔄 Scrape live now"):
    with st.spinner("Scraping Rory's Travel Club..."):
        sync_database(LOCATIONS)
        get_deal_cards.clear()  # Clear cache to reload fresh data

    st.sidebar.success("Deals refreshed")

deals = get_deal_cards(travel_origin)

if not deals:
    st.warning("No deals found in the database. Click 'Scrape live now' to populate it.")
    st.stop()

# --- Sidebar: filters --------------------------------------------------------
st.sidebar.header("Filters")
search = st.sidebar.text_input("Search hotel, county, or description")

counties = get_known_counties(deals)
county_choice = st.sidebar.multiselect("County", counties, default=[])

provinces = get_known_provinces(deals)
province_choice = st.sidebar.multiselect("Province", provinces, default=[])

min_rating = st.sidebar.slider("Minimum rating", 0.0, 5.0, 0.0, step=0.5)
min_rating = None if min_rating == 0.0 else min_rating

sort_choice = st.sidebar.selectbox("Sort by", SORT_OPTIONS)

filtered = filter_deals(deals, search, county_choice, province_choice, min_rating)
filtered = sort_deals(filtered, sort_choice)

# --- Header / stats ----------------------------------------------------------
st.title("🧳 Rory's Travel Club — Deals Board")
st.caption("Every live hotel offer, searchable and filterable.")

c1, c2, c3 = st.columns(3)
c1.metric("Live deals", len(deals))
c2.metric("Counties", len(counties))

expiries = [d.days_left for d in deals if d.days_left is not None]
c3.metric("Days to nearest expiry", max(min(expiries), 0) if expiries else "—")

st.divider()

CARD_HEIGHT = 455
DESC_LIMIT = 120

# --- Deal cards ---------------------------------------------------------------
if not filtered:
    st.info("No deals match those filters.")
else:
    cols = st.columns(3)
    for i, deal in enumerate(filtered):
        col = cols[i % 3]
        with col:
            with st.container(border=True, height=CARD_HEIGHT):
                if deal.image_url:
                    st.image(deal.image_url, use_container_width=True)

                hotel_name = re.sub(r'[^a-zA-Z ]', '', deal.hotel)
                st.markdown(f"**{hotel_name.strip().title()}**")

                st.caption(f"📍 {str(deal.county).title()} · {deal.province or ''}")

                if deal.rating is not None:
                    st.caption(f"⭐ {deal.rating:.1f} ({deal.review_count or 0})")

                desc = str(deal.description)
                short_desc = desc if len(desc) <= DESC_LIMIT else desc[:DESC_LIMIT].rsplit(" ", 1)[0] + "…"
                st.write(short_desc)

                price_col, expiry_col = st.columns(2)

                with price_col:
                    if deal.min_price is not None:
                        st.markdown(f"💶 from {deal.currency or ''}{deal.min_price:.0f}")

                with expiry_col:
                    days_left = deal.days_left
                    if days_left is not None:
                        if days_left < 0:
                            st.markdown(":red[Expired]")
                        elif days_left <= 21:
                            st.markdown(f":red[⏰ {days_left}d left]")
                        else:
                            st.markdown(f"⏰ {days_left}d left")
                    else:
                        st.markdown(f"⏰ {deal.expiry}")

                if deal.travel_minutes is not None:
                    st.caption(f"🚗 {deal.travel_minutes} min away")

                if deal.offer_url:
                    st.link_button("View deal ↗", deal.offer_url, use_container_width=True)

                if st.button("🔍 Zoom in", key=f"zoom_{i}"):
                    show_deal(deal)

st.divider()
st.caption("Data is stored in a local SQLite database and refreshed by the scraper.")
