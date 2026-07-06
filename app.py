"""
app.py

Streamlit dashboard for Rory's Travel Club deals. Regenerated from
app.ipynb -- keep both in sync.

Run with:
    streamlit run app.py
"""

import os
from datetime import date
import pandas as pd
import streamlit as st
import re

from scraper import scrape_all, LOCATIONS

CSV_PATH = "data/deals.csv"

# --- Load data ---------------------------------------------------------------
def load_from_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")

    return df

if os.path.exists(CSV_PATH):
    df = load_from_csv(CSV_PATH)
else:
    df = scrape_all(LOCATIONS)
    df.to_csv(CSV_PATH, index=False)


def filter_deals(df, search="", counties=None, provinces=None, sort_by="Soonest to expire"):
    filtered = df.copy()

    if search:
        s = search.lower()
        mask = (
            filtered["hotel"].str.lower().str.contains(s, na=False)
            | filtered["county"].str.lower().str.contains(s, na=False)
            | filtered["description"].str.lower().str.contains(s, na=False)
        )
        filtered = filtered[mask]

    if counties:
        filtered = filtered[filtered["county"].isin(counties)]

    if provinces:
        filtered = filtered[filtered["province"].isin(provinces)]

    filtered["days_left"] = (filtered["expiry"] - pd.Timestamp(date.today())).dt.days

    if sort_by == "Soonest to expire":
        filtered = filtered.sort_values("days_left", na_position="last")
    elif sort_by == "Lowest price first":
        filtered = filtered.sort_values("min_price", na_position="last")
    else:
        filtered = filtered.sort_values("hotel")

    return filtered

@st.dialog("Deal details")
def show_deal(deal):
    st.image(deal["image_url"], use_container_width=True)
    st.markdown(f"**{deal['hotel'].strip().title()}**")
    st.write(deal["description"])
    if pd.notna(deal.get("min_price")):
        st.markdown(f"💶 from {deal.get('currency','')}{deal['min_price']:.0f}")
    if pd.notna(deal.get("offer_url")):
        st.link_button("View deal ↗", deal["offer_url"])


st.set_page_config(page_title="Rory's Travel Club — Deals Board", page_icon="🧳", layout="wide")

# Image Markdown for same hieghts

st.markdown("""
<style>
div[data-testid="stImage"] img {
    height: 160px;
    object-fit: cover;
    border-radius: 8px;
}

/* Make the card position:relative so the overlay button can fill it */
div[data-testid="stVerticalBlockBorderWrapper"] {
    position: relative;
}

/* Target the invisible "click-catcher" button and stretch it over the card */
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


# --- Sidebar: data controls -------------------------------------------------
st.sidebar.header("Data")
if st.sidebar.button("🔄 Scrape live now"):
    with st.spinner("Scraping rorystravelclub.com..."):
        fresh = scrape_all(LOCATIONS)
        fresh.to_csv(CSV_PATH, index=False)
        df = fresh
        df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
    st.sidebar.success(f"Pulled {len(fresh)} deals")

if df.empty:
    st.warning(
        "No data yet. Run the scraper cells above first, "
        "or click **Scrape live now** in the sidebar."
    )
    st.stop()

# --- Sidebar: filters --------------------------------------------------------
st.sidebar.header("Filters")
search = st.sidebar.text_input("Search hotel, county, or description")

counties = sorted(df["county"].dropna().unique())
county_choice = st.sidebar.multiselect("County", counties, default=[])

provinces = sorted(df["province"].dropna().unique())
province_choice = st.sidebar.multiselect("Province", provinces, default=[])

sort_choice = st.sidebar.selectbox(
    "Sort by", ["Soonest to expire", "Lowest price first", "Hotel name (A-Z)"]
)

filtered = filter_deals(df, search, county_choice, province_choice, sort_choice)

# --- Header / stats ----------------------------------------------------------
st.title("🧳 Rory's Travel Club — Deals Board")
st.caption("Every live hotel offer, searchable and filterable.")

c1, c2, c3 = st.columns(3)
c1.metric("Live deals", len(df))
c2.metric("Counties", df["county"].nunique())
soonest = df["expiry"].dropna()

if not soonest.empty:
    days_to_soonest = (soonest.min() - pd.Timestamp(date.today())).days
    c3.metric("Days to nearest expiry", max(days_to_soonest, 0))
else:
    c3.metric("Days to nearest expiry", "—")

st.divider()

CARD_HEIGHT = 455
DESC_LIMIT = 120

# --- Deal cards ---------------------------------------------------------------
if filtered.empty:
    st.info("No deals match those filters.")
else:
    cols = st.columns(3)
    for i, (_, deal) in enumerate(filtered.iterrows()):
        col = cols[i % 3]
        with col:
            with st.container(border=True, height = CARD_HEIGHT):
                if pd.notna(deal.get("image_url")):
                    st.image(deal["image_url"], use_container_width=True)

                hotel_name = re.sub(r'[^a-zA-Z ]', '', deal['hotel'])
                st.markdown(f"**{hotel_name.strip().title()}**")

                st.caption(f"📍 {str(deal['county']).title()} · {deal.get('province', '')}")

                desc = str(deal["description"])
                short_desc = desc if len(desc) <= DESC_LIMIT else desc[:DESC_LIMIT].rsplit(" ", 1)[0] + "…"
                st.write(short_desc)

                price_col, expiry_col = st.columns(2)

                with price_col:
                    if pd.notna(deal.get("min_price")):
                        st.markdown(f"💶 from {deal.get('currency', '')}{deal['min_price']:.0f}")

                with expiry_col:
                    days_left = deal.get("days_left")
                    if pd.notna(days_left):
                        if days_left < 0:
                            st.markdown(":red[Expired]")
                        elif days_left <= 21:
                            st.markdown(f":red[⏰ {int(days_left)}d left]")
                        else:
                            st.markdown(f"⏰ {int(days_left)}d left")
                    else:
                        st.markdown(f"⏰ {deal['expiry']}")

                if pd.notna(deal.get("offer_url")):
                    st.link_button("View deal ↗", deal["offer_url"], use_container_width=True)

                # if len(desc) > DESC_LIMIT:
                #     with st.popover("Read more ↗"):
                #         st.markdown(f"**{hotel_name.strip().title()}**")
                #         st.write(desc)
                #         if pd.notna(deal.get("min_price")):
                #             st.markdown(f"💶 from {deal.get('currency','')}{deal['min_price']:.0f}")
                #         if pd.notna(deal.get("offer_url")):
                #             st.link_button("View deal ↗", deal["offer_url"])

                if st.button("🔍 Zoom in", key=f"zoom_{i}"):
                    show_deal(deal)

st.divider()
st.caption(
    "Data columns match the scraper's DataFrame: hotel, county, description, "
    "expiry, offer_url, image_url (plus derived province/price/expiry). "
    "Add more province slugs to LOCATIONS in scraper.py as you find them."
)


# """
# app.py

# Streamlit dashboard for Rory's Travel Club deals. Regenerated from
# app.ipynb -- keep both in sync.

# Run with:
#     streamlit run app.py
# """

# import os
# from datetime import date
# import pandas as pd
# import streamlit as st
# import re

# from scraper import scrape_all, LOCATIONS

# CSV_PATH = "deals.csv"

# # --- Load data ---------------------------------------------------------------
# def load_from_csv(path: str) -> pd.DataFrame:
#     df = pd.read_csv(path)
#     df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")

#     return df

# if os.path.exists(CSV_PATH):
#     df = load_from_csv(CSV_PATH)
# else:
#     df = scrape_all(LOCATIONS)
#     df.to_csv(CSV_PATH, index=False)


# def filter_deals(df, search="", counties=None, provinces=None, sort_by="Soonest to expire"):
#     filtered = df.copy()

#     if search:
#         s = search.lower()
#         mask = (
#             filtered["hotel"].str.lower().str.contains(s, na=False)
#             | filtered["county"].str.lower().str.contains(s, na=False)
#             | filtered["description"].str.lower().str.contains(s, na=False)
#         )
#         filtered = filtered[mask]

#     if counties:
#         filtered = filtered[filtered["county"].isin(counties)]

#     if provinces:
#         filtered = filtered[filtered["province"].isin(provinces)]

#     filtered["days_left"] = (filtered["expiry"] - pd.Timestamp(date.today())).dt.days

#     if sort_by == "Soonest to expire":
#         filtered = filtered.sort_values("days_left", na_position="last")
#     elif sort_by == "Lowest price first":
#         filtered = filtered.sort_values("min_price", na_position="last")
#     else:
#         filtered = filtered.sort_values("hotel")

#     return filtered


# @st.dialog("Deal details")
# def show_deal(deal):
#     st.image(deal["image_url"], use_container_width=True)
#     st.markdown(f"**{deal['hotel'].strip().title()}**")
#     st.write(deal["description"])
#     if pd.notna(deal.get("min_price")):
#         st.markdown(f"💶 from {deal.get('currency','')}{deal['min_price']:.0f}")
#     if pd.notna(deal.get("offer_url")):
#         st.link_button("View deal ↗", deal["offer_url"], use_container_width=True)


# st.set_page_config(page_title="Rory's Travel Club — Deals Board", page_icon="🧳", layout="wide")

# # --- Styling: consistent image heights + whole-card click overlay -----------
# st.markdown("""
# <style>
# div[data-testid="stImage"] img {
#     height: 160px;
#     object-fit: cover;
#     border-radius: 8px;
# }

# /* Bordered card containers become the positioning context for the overlay */
# div[data-testid="stVerticalBlockBorderWrapper"] {
#     position: relative;
# }

# /* The first button inside a card is our invisible click-catcher.
#    Stretch it over the whole card and hide it visually, but keep it
#    clickable (z-index above the card content). */
            
# div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"]:first-of-type {
#     position: absolute;
#     inset: 0;
#     z-index: 5;
# }
            
# div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"]:first-of-type button {
#     width: 100%;
#     height: 100%;
#     opacity: 0;
#     cursor: pointer;
# }
# </style>
# """, unsafe_allow_html=True)


# # --- Sidebar: data controls -------------------------------------------------
# st.sidebar.header("Data")
# if st.sidebar.button("🔄 Scrape live now"):
#     with st.spinner("Scraping rorystravelclub.com..."):
#         fresh = scrape_all(LOCATIONS)
#         fresh.to_csv(CSV_PATH, index=False)
#         df = fresh
#         df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
#     st.sidebar.success(f"Pulled {len(fresh)} deals")

# if df.empty:
#     st.warning(
#         "No data yet. Run the scraper cells above first, "
#         "or click **Scrape live now** in the sidebar."
#     )
#     st.stop()

# # --- Sidebar: filters --------------------------------------------------------
# st.sidebar.header("Filters")
# search = st.sidebar.text_input("Search hotel, county, or description")

# counties = sorted(df["county"].dropna().unique())
# county_choice = st.sidebar.multiselect("County", counties, default=[])

# provinces = sorted(df["province"].dropna().unique())
# province_choice = st.sidebar.multiselect("Province", provinces, default=[])

# sort_choice = st.sidebar.selectbox(
#     "Sort by", ["Soonest to expire", "Lowest price first", "Hotel name (A-Z)"]
# )

# filtered = filter_deals(df, search, county_choice, province_choice, sort_choice)

# # --- Header / stats ----------------------------------------------------------
# st.title("🧳 Rory's Travel Club — Deals Board")
# st.caption("Every live hotel offer, searchable and filterable.")

# c1, c2, c3 = st.columns(3)
# c1.metric("Live deals", len(df))
# c2.metric("Counties", df["county"].nunique())
# soonest = df["expiry"].dropna()

# if not soonest.empty:
#     days_to_soonest = (soonest.min() - pd.Timestamp(date.today())).days
#     c3.metric("Days to nearest expiry", max(days_to_soonest, 0))
# else:
#     c3.metric("Days to nearest expiry", "—")

# st.divider()

# CARD_HEIGHT = 455
# DESC_LIMIT = 120

# # --- Deal cards ---------------------------------------------------------------
# if filtered.empty:
#     st.info("No deals match those filters.")
# else:
#     cols = st.columns(3)
#     for i, (_, deal) in enumerate(filtered.iterrows()):
#         col = cols[i % 3]
#         with col:
#             with st.container(border=True, height=CARD_HEIGHT):
#                 # Invisible full-card click-catcher. Must be the FIRST widget
#                 # in the container so the CSS `:first-of-type` selector picks
#                 # it up and stretches it over everything else in the card.
#                 card_clicked = st.button(" ", key=f"card_click_{i}")

#                 if pd.notna(deal.get("image_url")):
#                     st.image(deal["image_url"], use_container_width=True)

#                 hotel_name = re.sub(r'[^a-zA-Z ]', '', deal['hotel'])
#                 st.markdown(f"**{hotel_name.strip().title()}**")

#                 st.caption(f"📍 {str(deal['county']).title()} · {deal.get('province', '')}")

#                 desc = str(deal["description"])
#                 short_desc = desc if len(desc) <= DESC_LIMIT else desc[:DESC_LIMIT].rsplit(" ", 1)[0] + "…"
#                 st.write(short_desc)

#                 price_col, expiry_col = st.columns(2)

#                 with price_col:
#                     if pd.notna(deal.get("min_price")):
#                         st.markdown(f"💶 from {deal.get('currency', '')}{deal['min_price']:.0f}")

#                 with expiry_col:
#                     days_left = deal.get("days_left")
#                     if pd.notna(days_left):
#                         if days_left < 0:
#                             st.markdown(":red[Expired]")
#                         elif days_left <= 21:
#                             st.markdown(f":red[⏰ {int(days_left)}d left]")
#                         else:
#                             st.markdown(f"⏰ {int(days_left)}d left")
#                     else:
#                         st.markdown(f"⏰ {deal['expiry']}")

#                 # Note: "View deal" now lives inside the dialog only. The
#                 # invisible overlay button sits on top of the whole card, so
#                 # a second real button on the card face would be unclickable
#                 # underneath it.

#                 if card_clicked:
#                     show_deal(deal)

# st.divider()
# st.caption(
#     "Data columns match the scraper's DataFrame: hotel, county, description, "
#     "expiry, offer_url, image_url (plus derived province/price/expiry). "
#     "Add more province slugs to LOCATIONS in scraper.py as you find them."
# )
