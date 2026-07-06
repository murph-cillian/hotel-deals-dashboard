
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Configuration

URL_BASE = "https://rorystravelclub.com/pages/rtc-"
 
HEADERS = {
    # A normal browser UA avoids some basic bot-blocking
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

CARD_CLASS_RE = re.compile(r"-offers-card-[a-zA-Z0-9]+$")

COUNTY_TO_PROVINCE = {
    "carlow": "Leinster", "dublin": "Leinster", "kildare": "Leinster", "kilkenny": "Leinster",
    "laois": "Leinster", "longford": "Leinster", "louth": "Leinster", "meath": "Leinster",
    "offaly": "Leinster", "westmeath": "Leinster", "wexford": "Leinster", "wicklow": "Leinster",
    "clare": "Munster", "cork": "Munster", "kerry": "Munster", "limerick": "Munster",
    "tipperary": "Munster", "waterford": "Munster",
    "galway": "Connacht", "leitrim": "Connacht", "mayo": "Connacht", "roscommon": "Connacht",
    "sligo": "Connacht",
    "cavan": "Ulster", "donegal": "Ulster", "monaghan": "Ulster",
}

LOCATIONS = ['leinster-offers', 'munster-offers', 'connacht-offers', 'ulster-offers-1']

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
    """'Valid until: August 31, 2026' -> Timestamp, or None if unparsable."""

    match = re.search(r"Valid until:\s*(.+)", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return pd.to_datetime(match.group(1).strip(), errors="coerce")
    except Exception:
        return None

def scrape_location(location: str) -> list[dict]:
    """Scrape a single province page (e.g. 'leinster-offers') and return a list of deal dicts."""

    url = URL_BASE + location
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

def scrape_all(locations: list[str] = LOCATIONS) -> pd.DataFrame:
    """Scrape every province page in `locations` and return one combined DataFrame."""

    records = []
    for location in locations:
        records.extend(scrape_location(location))
 
    df = pd.DataFrame(records)
    if df.empty:
        return df
 
    # Enrich with derived columns the dashboard uses
    df["province"] = df["county"].str.lower().map(COUNTY_TO_PROVINCE).fillna("Unknown")

    df[["currency", "min_price"]] = df["description"].fillna("").apply(lambda t: pd.Series(parse_prices(t)))

    df["expiry_date"] = df["expiry"].apply(parse_expiry)

    return df
 
if __name__ == "__main__":
    
    # Quick manual run: `python scraper.py` scrapes everything and saves a CSV.
    df = scrape_all()
    df.to_csv("deals.csv", index=False)
    print(f"Saved {len(df)} deals to deals.csv")
 