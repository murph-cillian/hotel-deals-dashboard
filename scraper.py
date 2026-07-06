# Packages
import re
import requests
from urllib.parse import urlsplit, urlunsplit, urljoin
from bs4 import BeautifulSoup
from datetime import datetime, UTC

# Custom modules
from database import SessionLocal
from models import Hotel, Deal, PriceHistory

# Configuration

TRACKING_URL = (
    "https://rorystravelclub.acemlna.com/lt.php"
    "?x=3DZy~GDLJFmb6KCuytA7geJxAK-njdDxkMdgYKPGV6SZ6XF_0Uy.0OFr237ziN~0kfYxbHHJKXib"
)

HEADERS = {
    # A normal browser UA avoids some basic bot-blocking
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

CARD_CLASS_RE = re.compile(r"-offers-card-[a-zA-Z0-9]+$")

COUNTY_TO_PROVINCE = {
    "carlow": "Leinster", "dublin" : "Leinster", "kildare": "Leinster", "kilkenny" : "Leinster", "laois"    : "Leinster", "longford" : "Leinster", "louth": "Leinster", "meath"  : "Leinster", "offaly"  : "Leinster", "westmeath": "Leinster", "wexford": "Leinster", "wicklow": "Leinster",
    "clare" : "Munster" , "cork"   : "Munster" , "kerry"  : "Munster" , "limerick" : "Munster" , "tipperary": "Munster" , "waterford": "Munster" ,
    "galway": "Connacht", "leitrim": "Connacht", "mayo"   : "Connacht", "roscommon": "Connacht", "sligo"    : "Connacht",
    "antrim": "Ulster"  , "armagh" : "Ulster"  , "down"   : "Ulster"  , "fermanagh": "Ulster"  , "derry"    : "Ulster"  , "tyrone"   : "Ulster"  , "cavan": "Ulster"  , "donegal": "Ulster"  , "monaghan": "Ulster"  ,
}

# Scraping Functions

def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text

# Parsing Functions 

def parse_prices(text: str):
    """Extract all €/£ amounts from a deal description and return the min."""

    amounts = re.findall(r"[€£]\s?(\d[\d,]*(?:\.\d{1,2})?)", text)
    if not amounts:
        return None, None
    currency = "€" if "€" in text else ("£" if "£" in text else None)
    values = [float(a.replace(",", "")) for a in amounts]
    return currency, min(values)    


def parse_expiry(text: str):
    if not text:
        return None

    text = text.strip()

    try:
        return datetime.strptime(text, "%B %d, %Y").date()
    except ValueError:
        return None

def scrape_url(url: str) -> list[dict]:
    """Scrape a single URL and return a list of deal dicts."""

    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
 
    # NOTE: bs4 calls class_ functions once per individual class token, not
    # once with the full class list -- so `c` here is a single string.
    cards = soup.find_all("div", class_=lambda c: c and CARD_CLASS_RE.search(c))
 
    records = []
    for card in cards:

        hotel = card.get("data-hotel") or card.find("h3").get_text(strip=True)
        county = card.get("data-county")
 
        img = card.find("img")
        image_url = img.get("src") if img else None
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url
 
        desc = card.find("p", class_=lambda c: c and "description" in c)
        description = desc.get_text(separator="\n", strip=True) if desc else None
 
        expiry = card.find("p", class_=lambda c: c and "expiry" in c)
        expiry = (
            expiry.get_text(strip=True).replace("Valid until:", "").strip()
            if expiry else None
        )
 
        link = card.find("a", href=True)
        offer_url = link["href"] if link else None
 
        records.append({
            "hotel": hotel,
            "county": county,
            "description": description,
            "expiry": expiry,
            "offer_url": offer_url,
            "image_url": image_url,
        })

    return records

def sync_database():
    """Scrape every province page in `locations` and update the SQLAlchemy database."""

    # Follow the redirect to the real page
    response = requests.get(TRACKING_URL)
    response.raise_for_status()

    # Parse the HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all <a> tags with class="icon-wrap"
    links = soup.find_all("a", class_="icon-wrap")

    urls = []

    for link in links:
        href = link.get("href")
        if href:
            
            full_url = urljoin(response.url, href)
            urls.append(full_url)

    with SessionLocal() as session:
        try:

            records = []
            for url in urls:
                records.extend(scrape_url(url))
        
            for record in records:
                county = record.get("county")

                if isinstance(county, str):
                    province = COUNTY_TO_PROVINCE.get(county.strip().lower(), "Unknown")
                else:
                    province = "Unknown"

                # try and retrieve the hotel from the database; if it doesn't exist, create it
                hotel = (
                    session.query(Hotel)
                    .filter_by(name=record["hotel"])
                    .first()
                )

                if hotel is None:
                    hotel = Hotel(
                        name=record["hotel"],
                    )

                    session.add(hotel)
                    session.flush()      # Gives hotel.id
                
                hotel.county = record["county"]
                hotel.province = province
                hotel.image_url = record["image_url"]

                currency, price = parse_prices(record["description"])
                expiry = parse_expiry(record["expiry"])

                existing_deal = (
                    session.query(Deal)
                    .filter_by(
                        hotel_id=hotel.id,
                        offer_url=record["offer_url"]
                    )
                    .first()
                )

                if existing_deal:
                    existing_deal.description = record["description"]
                    existing_deal.price = price
                    existing_deal.currency = currency
                    existing_deal.expiry = expiry
                    existing_deal.offer_url = record["offer_url"]
                    existing_deal.scraped_at = datetime.now(UTC)
               
                else:

                    existing_deal = Deal(
                        hotel_id=hotel.id,
                        description=record["description"],
                        price=price,
                        currency=currency,
                        expiry=expiry,
                        offer_url=record["offer_url"],
                        scraped_at=datetime.now(UTC)
                    )

                    session.add(existing_deal)

                session.add(
                    PriceHistory(
                        deal_id=existing_deal.id,
                        price=price,
                        scraped_at=datetime.now(UTC),
                    )
                )

            session.commit()
        
        except Exception:
            session.rollback()
            raise

 