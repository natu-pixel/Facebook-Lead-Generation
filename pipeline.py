import datetime
from typing import Dict, Any, List
import config
import database
import geoapify_places
import notifier

# Common national restaurant chains to filter out
CHAIN_KEYWORDS = {
    "mcdonald", "starbucks", "subway", "burger king", "taco bell", "wendy", 
    "domino", "pizza hut", "dunkin", "kfc", "chipotle", "panera", "sonic", 
    "applebee", "chili's", "olive garden", "buffalo wild wings", "ihop", 
    "denny", "red lobster", "outback", "dairy queen", "jack in the box",
    "papa john", "little caesars", "arbys", "arby's", "five guys"
}

def is_chain(name: str) -> bool:
    """Heuristic check to identify and filter out major national chains."""
    normalized_name = name.lower()
    for chain in CHAIN_KEYWORDS:
        if chain in normalized_name:
            return True
    return False

def calculate_lead_score(place: Dict[str, Any]) -> int:
    """
    Calculates a lead priority score out of 100.
    A hot lead is defined as an operational local business with high reviews,
    a high rating, an available phone number, but no website.
    Supports OpenStreetMap data from Geoapify (e.g. email, opening_hours, wiki).
    """
    score = 40  # Base score for meeting initial filters
    
    # Phone number presence
    if place.get("phone_number"):
        score += 15
        
    # Email availability (+10 points)
    if place.get("email"):
        score += 10
        
    # Opening hours availability (+15 points)
    if place.get("opening_hours"):
        score += 15
        
    # Established indicator (Wikidata or Wikipedia) (+10 points)
    if place.get("wikidata") or place.get("wikipedia"):
        score += 10
        
    # Review count weight if present (up to 20 points)
    reviews_count = place.get("user_rating_count") or 0
    if reviews_count > 0:
        review_bonus = min(20, int(reviews_count * 0.05))
        score += review_bonus
    
    # Rating weight if present (up to 10 points)
    rating = place.get("rating") or 0.0
    if rating >= 3.5:
        rating_bonus = min(10, int((rating - 3.5) * 8))
        score += rating_bonus
        
    # Active profile / status weight
    if place.get("business_status") == "OPERATIONAL":
        score += 10
        
    # Deduct points if it behaves like a chain
    if is_chain(place["name"]):
        score -= 50
        
    return max(0, min(100, score))

def run_pipeline() -> List[Dict[str, Any]]:
    """Runs the lead generation pipeline across all configured target cities."""
    # Ensure database is initialized
    database.init_db()
    
    country = config.TARGET_COUNTRY
    cities = config.TARGET_CITIES
    category = config.TARGET_CATEGORY
    
    print(f"Starting Geoapify Lead Generation Pipeline")
    print(f"Target Country: {country}")
    print(f"Target Cities: {', '.join(cities)}")
    print(f"Category: {category}")
    print(f"Filters: Min Reviews={config.MIN_REVIEWS}, Min Rating={config.MIN_RATING}, Require Phone={config.REQUIRE_PHONE}, Require Website={config.REQUIRE_WEBSITE}")
    print("-" * 50)
    
    qualified_leads = []
    
    for city in cities:
        print(f"\nProcessing city: {city}...")
        # Get basic list of places
        places = geoapify_places.search_places_basic(city, country, category)
        
        city_leads_found = 0
        city_skipped_duplicates = 0
        city_skipped_filters = 0
        
        for place in places:
            place_id = place["place_id"]
            
            # Check duplicate state first
            if database.is_duplicate(place_id):
                city_skipped_duplicates += 1
                continue
                
            # Basic Filters (before hitting details endpoint to save API calls)
            
            # Status check
            if place.get("business_status") != "OPERATIONAL":
                city_skipped_filters += 1
                continue
                
            # Chain exclusion
            if is_chain(place["name"]):
                city_skipped_filters += 1
                continue
                
            # Pre-filter website if already present in basic search
            has_website = place.get("website_uri") is not None
            if not config.REQUIRE_WEBSITE and has_website:
                city_skipped_filters += 1
                continue
                
            # Retrieve detailed properties (contact, hours, email, etc.)
            details = geoapify_places.get_place_details(place_id)
            
            # Update place properties with details
            place["website_uri"] = details.get("website_uri") or place.get("website_uri")
            
            # Double check: If no website is listed in OpenStreetMap details, perform a live online verification
            if not place["website_uri"]:
                online_website = geoapify_places.verify_website_online(place["name"], city)
                if online_website:
                    place["website_uri"] = online_website
                    
            place["phone_number"] = details.get("phone_number") or place.get("phone_number")
            place["email"] = details.get("email")
            place["opening_hours"] = details.get("opening_hours")
            place["wikidata"] = details.get("wikidata")
            place["wikipedia"] = details.get("wikipedia")
            
            # Full Filters (after details lookup)
            
            # Website criteria filter
            has_website = place.get("website_uri") is not None
            if config.REQUIRE_WEBSITE != has_website:
                city_skipped_filters += 1
                continue
                
            # Phone criteria filter
            has_phone = place.get("phone_number") is not None
            if config.REQUIRE_PHONE and not has_phone:
                city_skipped_filters += 1
                continue
                
            # Reviews criteria filter (Optional: only if reviews count is available)
            reviews_count = place.get("user_rating_count")
            if config.MIN_REVIEWS > 0 and reviews_count is not None and reviews_count < config.MIN_REVIEWS:
                city_skipped_filters += 1
                continue
                
            # Rating criteria filter (Optional: only if rating is available)
            rating = place.get("rating")
            if config.MIN_RATING > 0.0 and rating is not None and rating < config.MIN_RATING:
                city_skipped_filters += 1
                continue
                
            # Compute score and check if it qualified
            score = calculate_lead_score(place)
            
            # Generate a universally clickable Google Maps search link for cold outreach
            maps_url = f"https://www.google.com/maps/search/?api=1&query={place['name']}+{city}+{country}".replace(" ", "+")
            
            # Generate a Facebook Search Link for pages matching this business name in this city
            facebook_search_url = f"https://www.facebook.com/search/pages/?q={place['name']}+{city}".replace(" ", "+")
            
            lead_data = {
                "place_id": place_id,
                "name": place["name"],
                "city": city,
                "country": country,
                "rating": rating,
                "reviews_count": reviews_count,
                "phone": place.get("phone_number"),
                "email": place.get("email"),
                "opening_hours": place.get("opening_hours"),
                "facebook_search_url": facebook_search_url,
                "maps_url": maps_url,
                "score": score,
                "found_at": datetime.datetime.utcnow().isoformat()
            }
            
            # Save to SQLite db
            database.save_lead(lead_data)
            
            # Send real-time notification
            notifier.send_notification(lead_data)
            
            qualified_leads.append(lead_data)
            city_leads_found += 1
            
        print(f"[{city}] Done: {city_leads_found} new leads qualified, {city_skipped_duplicates} duplicates skipped, {city_skipped_filters} filtered out.")
        
    print("\n" + "=" * 50)
    print(f"Pipeline Completed! Total new qualified leads found: {len(qualified_leads)}")
    print("=" * 50)
    
    return qualified_leads
