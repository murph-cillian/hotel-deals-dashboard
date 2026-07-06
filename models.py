from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    ForeignKey,
    Text,
    DateTime
)

from sqlalchemy.orm import relationship

from database import Base

class Hotel(Base):

    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True)

    name = Column(String, unique=True)

    county = Column(String)

    province = Column(String)

    latitude = Column(Float)

    longitude = Column(Float)

    image_url = Column(String)

    deals = relationship("Deal", back_populates="hotel")



class Deal(Base):

    __tablename__ = "deals"

    id = Column(Integer, primary_key=True)

    hotel_id = Column(Integer, ForeignKey("hotels.id"))

    description = Column(Text)

    price = Column(Float)

    currency = Column(String)

    expiry = Column(Date)

    offer_url = Column(String)

    scraped_at = Column(DateTime)

    hotel = relationship("Hotel", back_populates="deals")


class Review(Base):

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)

    hotel_id = Column(Integer, ForeignKey("hotels.id"))

    rating = Column(Float)

    review_count = Column(Integer)

    source = Column(String)

    last_updated = Column(DateTime)


class TravelTime(Base):

    __tablename__ = "travel_times"

    id = Column(Integer, primary_key=True)

    hotel_id = Column(Integer, ForeignKey("hotels.id"))

    origin = Column(String)

    duration_minutes = Column(Integer)

    distance_km = Column(Float)

    last_updated = Column(DateTime)


class PriceHistory(Base):

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)

    deal_id = Column(Integer, ForeignKey("deals.id"))

    price = Column(Float)

    scraped_at = Column(DateTime)