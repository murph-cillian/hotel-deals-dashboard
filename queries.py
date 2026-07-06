"""
queries.py

All database access for the Deals Board lives here. Nothing outside this
file should import SQLAlchemy or the models directly -- app.py and
filters.py only ever see plain `DealCard` objects.

To add a new data source (e.g. a new table):
  1. Write a small `get_x()` function that returns a dict keyed by hotel_id.
  2. Add the matching field(s) to `DealCard`.
  3. Merge it in `get_deal_cards()`.
Nothing else in the app needs to change.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import streamlit as st
from sqlalchemy import select, func

from database import SessionLocal
from models import Hotel, Deal, Review, TravelTime


@dataclass
class DealCard:
    """One fully-merged record -- everything needed to render a single card.
    Add new fields here as new tables get joined in."""

    hotel_id: int
    hotel: str
    county: Optional[str]
    province: Optional[str]
    image_url: Optional[str]

    description: Optional[str]
    min_price: Optional[float]
    currency: Optional[str]
    expiry: Optional[date]
    offer_url: Optional[str]
    days_left: Optional[int] = None

    # Review fields (populated once Review scraping exists)
    rating: Optional[float] = None
    review_count: Optional[int] = None
    review_source: Optional[str] = None

    # Travel time fields (populated once TravelTime scraping exists)
    travel_minutes: Optional[int] = None
    travel_distance_km: Optional[float] = None


def _get_deals(session) -> list[dict]:
    """One row per hotel+deal. This is the base of every card."""

    stmt = (
        select(
            Hotel.id.label("hotel_id"),
            Hotel.name.label("hotel"),
            Hotel.county,
            Hotel.province,
            Hotel.image_url,
            Deal.description,
            Deal.price.label("min_price"),
            Deal.currency,
            Deal.expiry,
            Deal.offer_url,
        )
        .join(Deal)
    )
    return [dict(row) for row in session.execute(stmt).mappings().all()]


def _get_latest_reviews(session) -> dict[int, dict]:
    """Most recently updated review per hotel, keyed by hotel_id.
    Reduced to one row per hotel here so merging never fans out rows."""

    latest = (
        select(Review.hotel_id, func.max(Review.last_updated).label("latest"))
        .group_by(Review.hotel_id)
        .subquery()
    )

    stmt = select(
        Review.hotel_id,
        Review.rating,
        Review.review_count,
        Review.source,
    ).join(
        latest,
        (Review.hotel_id == latest.c.hotel_id) & (Review.last_updated == latest.c.latest),
    )

    return {row["hotel_id"]: dict(row) for row in session.execute(stmt).mappings().all()}


def _get_travel_times(session, origin: Optional[str] = None) -> dict[int, dict]:
    """Travel time per hotel from a given origin, keyed by hotel_id.
    `origin` is a user-facing parameter (e.g. "Dublin"), not something to
    collapse automatically -- pass it through from the UI."""

    stmt = select(
        TravelTime.hotel_id,
        TravelTime.duration_minutes,
        TravelTime.distance_km,
    )
    if origin:
        stmt = stmt.where(TravelTime.origin == origin)

    return {row["hotel_id"]: dict(row) for row in session.execute(stmt).mappings().all()}


@st.cache_data
def get_deal_cards(travel_origin: Optional[str] = None) -> list[DealCard]:
    """Assemble the full list of DealCards from every table.
    This is the single entry point app.py should call."""

    with SessionLocal() as session:
        deal_rows = _get_deals(session)
        reviews_by_hotel = _get_latest_reviews(session)
        travel_by_hotel = _get_travel_times(session, travel_origin)

    today = date.today()
    cards = []
    for row in deal_rows:
        review = reviews_by_hotel.get(row["hotel_id"])
        travel = travel_by_hotel.get(row["hotel_id"])

        cards.append(
            DealCard(
                hotel_id=row["hotel_id"],
                hotel=row["hotel"],
                county=row["county"],
                province=row["province"],
                image_url=row["image_url"],
                description=row["description"],
                min_price=row["min_price"],
                currency=row["currency"],
                expiry=row["expiry"],
                offer_url=row["offer_url"],
                days_left=(row["expiry"] - today).days if row["expiry"] else None,
                rating=review["rating"] if review else None,
                review_count=review["review_count"] if review else None,
                review_source=review["source"] if review else None,
                travel_minutes=travel["duration_minutes"] if travel else None,
                travel_distance_km=travel["distance_km"] if travel else None,
            )
        )

    return cards


def get_known_counties(cards: list[DealCard]) -> list[str]:
    return sorted({c.county for c in cards if c.county})


def get_known_provinces(cards: list[DealCard]) -> list[str]:
    return sorted({c.province for c in cards if c.province})


def get_known_travel_origins(session=None) -> list[str]:
    """All distinct origins recorded in TravelTime, for a UI dropdown."""

    owns_session = session is None
    session = session or SessionLocal()
    try:
        stmt = select(TravelTime.origin).distinct()
        return sorted({row[0] for row in session.execute(stmt).all() if row[0]})
    finally:
        if owns_session:
            session.close()
