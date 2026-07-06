"""
filters.py

Pure functions over lists of DealCard. No Streamlit, no SQLAlchemy --
this file only knows about the DealCard shape, so it's reusable outside
the dashboard (CLI report, scheduled digest, tests, etc.) and never needs
to change just because a new table gets joined into DealCard upstream.
"""

from typing import Optional

from queries import DealCard

SORT_OPTIONS = [
    "Soonest to expire",
    "Lowest price first",
    "Highest rated",
    "Closest travel time",
    "Hotel name (A-Z)",
]


def filter_deals(
    cards: list[DealCard],
    search: str = "",
    counties: Optional[list[str]] = None,
    provinces: Optional[list[str]] = None,
    min_rating: Optional[float] = None,
) -> list[DealCard]:
    filtered = cards

    if search:
        s = search.lower()

        def matches(c: DealCard) -> bool:
            hotel = (c.hotel or "").lower()
            county = (c.county or "").lower()
            description = (c.description or "").lower()
            return s in hotel or s in county or s in description

        filtered = [c for c in filtered if matches(c)]

    if counties:
        filtered = [c for c in filtered if c.county in counties]

    if provinces:
        filtered = [c for c in filtered if c.province in provinces]

    if min_rating is not None:
        filtered = [c for c in filtered if c.rating is not None and c.rating >= min_rating]

    return filtered


def sort_deals(cards: list[DealCard], sort_by: str = "Soonest to expire") -> list[DealCard]:
    # (value is None, value) puts missing values last, ascending otherwise
    if sort_by == "Soonest to expire":
        return sorted(cards, key=lambda c: (c.days_left is None, c.days_left))
    elif sort_by == "Lowest price first":
        return sorted(cards, key=lambda c: (c.min_price is None, c.min_price))
    elif sort_by == "Highest rated":
        return sorted(cards, key=lambda c: (c.rating is None, -(c.rating or 0)))
    elif sort_by == "Closest travel time":
        return sorted(cards, key=lambda c: (c.travel_minutes is None, c.travel_minutes))
    else:
        return sorted(cards, key=lambda c: (c.hotel or "").lower())
