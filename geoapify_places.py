import requests
import time
from typing import List, Dict, Any, Optional
import config

GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"
PLACE_DETAILS_URL = "https://api.geoapify.com/v2/place-details"

def get_geoapify_category(category: str) -> str:
    """Maps a user-friendly category name to Geoapify's OSM category."""
    category = category.lower().strip()
    mapping = {
        "restaurant": "catering.restaurant",
        "cafe": "catering.cafe",
        "bakery": "catering.bakery",
        "dentist": "healthcare.dentist",
        "hotel": "accommodation.hotel",
        "pub": "catering.pub",
        "bar": "catering.bar"
    }
    # Return the mapped category, or construct a default if not mapped
    if category in mapping:
        return mapping[category]
    if "." in category:
        return category
    return f"catering.{category}"

def geocode_city(city: str, country: str) -> Optional[str]:
    """Queries Geoapify Geocoding API to resolve the city's unique boundary place ID."""
    if config.USE_MOCK_DATA:
        return f"mock-city-id-{city.lower()}"

    params = {
        "text": f"{city}, {country}",
        "apiKey": config.GEOAPIFY_API_KEY
    }
    
    try:
        print(f"[{city}] Resolving city Place ID via Geocoding API...")
        response = requests.get(GEOCODE_URL, params=params, timeout=15)
        if response.status_code != 200:
            print(f"Geocoding error: Status {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        features = data.get("features", [])
        if not features:
            print(f"Geocoding warning: No boundary found for '{city}, {country}'")
            return None
            
        # Extract the place_id of the city
        properties = features[0].get("properties", {})
        place_id = properties.get("place_id")
        return place_id
        
    except Exception as e:
        print(f"Geocoding exception for {city}: {str(e)}")
        return None

def search_places_basic(city: str, country: str, category: str) -> List[Dict[str, Any]]:
    """
    Searches for places in a given city and country for a target category.
    Returns a basic list of candidate listings (names, IDs, addresses) to check for duplicates.
    """
    if config.USE_MOCK_DATA:
        return _get_mock_places_basic(city, country, category)
        
    city_place_id = geocode_city(city, country)
    if not city_place_id:
        print(f"[{city}] Skipping search: Could not resolve city Place ID.")
        return []
        
    geoapify_category = get_geoapify_category(category)
    
    params = {
        "categories": geoapify_category,
        "filter": f"place:{city_place_id}",
        "limit": 100,  # Query up to 100 places in one request
        "apiKey": config.GEOAPIFY_API_KEY
    }
    
    try:
        print(f"[{city}] Searching category '{geoapify_category}'...")
        response = requests.get(PLACES_URL, params=params, timeout=15)
        if response.status_code != 200:
            print(f"Places search error: Status {response.status_code} - {response.text}")
            return []
            
        data = response.json()
        features = data.get("features", [])
        
        results = []
        for feature in features:
            properties = feature.get("properties", {})
            place_id = properties.get("place_id")
            if not place_id:
                continue
                
            # Basic parsing (before details lookup)
            results.append({
                "place_id": place_id,
                "name": properties.get("name", "Unknown Business"),
                "formatted_address": properties.get("formatted", f"{city}, {country}"),
                "business_status": "OPERATIONAL",  # OSM assumes operational unless tagged closed
                "types": properties.get("categories", [category]),
                # Fallbacks in case basic search already contains contact data
                "website_uri": properties.get("website"),
                "phone_number": properties.get("contact", {}).get("phone") or properties.get("phone")
            })
            
        return results
        
    except Exception as e:
        print(f"Places search exception for {city}: {str(e)}")
        return []

def get_place_details(place_id: str) -> Dict[str, Any]:
    """
    Retrieves full details for a place_id, including phone, email, website,
    opening hours, and wikidata identifiers.
    """
    if config.USE_MOCK_DATA:
        return _get_mock_place_details(place_id)
        
    params = {
        "id": place_id,
        "apiKey": config.GEOAPIFY_API_KEY
    }
    
    try:
        response = requests.get(PLACE_DETAILS_URL, params=params, timeout=10)
        if response.status_code != 200:
            return {}
            
        data = response.json()
        features = data.get("features", [])
        if not features:
            return {}
            
        properties = features[0].get("properties", {})
        details = properties.get("details", {})
        contact = details.get("contact", {})
        
        # Safe properties extraction
        phone = contact.get("phone") or properties.get("phone")
        email = contact.get("email") or properties.get("email")
        website = details.get("website") or properties.get("website")
        opening_hours = details.get("opening_hours") or properties.get("opening_hours")
        
        # Wikidata/Wikipedia links check
        wikidata = details.get("wikidata") or properties.get("wikidata")
        wikipedia = details.get("wikipedia") or properties.get("wikipedia")
        
        return {
            "phone_number": phone,
            "website_uri": website,
            "email": email,
            "opening_hours": opening_hours,
            "wikidata": wikidata,
            "wikipedia": wikipedia
        }
        
    except Exception as e:
        print(f"Place Details exception for {place_id}: {str(e)}")
        return {}

# --- MOCK DATA GENERATOR ---

def _get_mock_places_basic(city: str, country: str, category: str) -> List[Dict[str, Any]]:
    """Generates basic mock data mimicking the Geoapify Places list response."""
    time.sleep(0.3)
    
    # 10 mock places in the city
    names = [
        "Bella Italian Kitchen",       # Hot Lead (needs details lookup)
        "Kebab King Express",          # Hot Lead (needs details lookup)
        "The Greek Corner Tavern",     # Hot Lead (needs details lookup)
        "Downtown Charcoal Steakhouse",# Hot Lead (needs details lookup)
        "Sunrise Retro Diner",         # Hot Lead (needs details lookup)
        "Midwood Grill",               # Has website (should fail filters)
        "Golden Palace Buffet",        # Has website (should fail filters)
        "Taco Fiesta Corner",          # Low score (no phone, no email)
        "Spicy Ramen Shop",            # No phone (should fail filter if REQUIRE_PHONE=true)
        "Old Town Bakery & Cafe"       # Temporarily closed (should fail filter)
    ]
    
    results = []
    for name in names:
        slug = name.lower().replace(" ", "-")
        place_id = f"geoapify-id-{slug}-{city.lower()}"
        
        # Simulate if website is partially returned in search
        website = None
        if name in ("Midwood Grill", "Golden Palace Buffet"):
            website = f"https://www.{slug}.com"
            
        results.append({
            "place_id": place_id,
            "name": name,
            "formatted_address": f"123 OSM Way, {city}, {country}",
            "business_status": "CLOSED_TEMPORARILY" if name == "Old Town Bakery & Cafe" else "OPERATIONAL",
            "types": [get_geoapify_category(category)],
            "website_uri": website,
            "phone_number": None  # Load from details endpoint
        })
        
    return results

def _get_mock_place_details(place_id: str) -> Dict[str, Any]:
    """Generates mock details matching specific place_ids."""
    details_map = {
        "bella-italian-kitchen": {
            "phone_number": "(555) 019-2831",
            "website_uri": None,
            "email": "info@bellaitaliankitchen.com",
            "opening_hours": "Mo-Su 11:00-22:00",
            "wikidata": "Q12345678"
        },
        "kebab-king-express": {
            "phone_number": "(555) 011-3829",
            "website_uri": None,
            "email": None,
            "opening_hours": "Mo-Sa 10:00-23:00",
            "wikidata": None
        },
        "the-greek-corner-tavern": {
            "phone_number": "(555) 018-9271",
            "website_uri": None,
            "email": "contact@greekcornertavern.com",
            "opening_hours": "Mo-Su 11:00-21:00",
            "wikidata": None
        },
        "downtown-charcoal-steakhouse": {
            "phone_number": "(555) 012-7845",
            "website_uri": None,
            "email": "reservations@downtowncharcoal.com",
            "opening_hours": "Mo-Su 16:00-23:00",
            "wikidata": "Q87654321"
        },
        "sunrise-retro-diner": {
            "phone_number": "(555) 015-8833",
            "website_uri": None,
            "email": None,
            "opening_hours": "Mo-Su 06:00-15:00",
            "wikidata": None
        },
        "midwood-grill": {
            "phone_number": "(555) 013-4492",
            "website_uri": "https://www.midwoodgrill.com",
            "email": "hello@midwoodgrill.com",
            "opening_hours": "Mo-Su 11:00-22:00",
            "wikidata": None
        },
        "golden-palace-buffet": {
            "phone_number": "(555) 016-5521",
            "website_uri": "http://goldenpalacebuffet.net",
            "email": "info@goldenpalacebuffet.net",
            "opening_hours": "Mo-Su 11:30-21:30",
            "wikidata": None
        },
        "taco-fiesta-corner": {
            "phone_number": None,
            "website_uri": None,
            "email": None,
            "opening_hours": None,
            "wikidata": None
        },
        "spicy-ramen-shop": {
            "phone_number": None,
            "website_uri": None,
            "email": "spicyramen@ramenshop.com",
            "opening_hours": "Mo-Su 12:00-22:00",
            "wikidata": None
        },
        "old-town-bakery-&-cafe": {
            "phone_number": "(555) 017-6644",
            "website_uri": None,
            "email": "info@oldtownbakery.com",
            "opening_hours": "Mo-Sa 07:00-16:00",
            "wikidata": None
        }
    }
    
    # Try to find a matching key in our details mapping
    matching_detail = {
        "phone_number": None,
        "website_uri": None,
        "email": None,
        "opening_hours": None,
        "wikidata": None
    }
    
    for key, val in details_map.items():
        if key in place_id:
            matching_detail = val
            break
            
    return matching_detail
