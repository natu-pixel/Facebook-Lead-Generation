import argparse
import sys
import os
import config
import database
import pipeline

def print_report():
    """Prints a formatted report of all leads saved in the database."""
    leads = database.get_all_leads()
    if not leads:
        print("No leads found in the database.")
        return
        
    print("\n" + "=" * 120)
    print(f"{'Name':<25} | {'City':<12} | {'Score':<5} | {'Phone':<15} | {'Email':<28} | {'Hours':<25}")
    print("-" * 120)
    for lead in leads:
        name = lead['name']
        if len(name) > 25:
            name = name[:22] + "..."
        phone = lead['phone'] or "N/A"
        email = lead.get('email') or "N/A"
        if len(email) > 28:
            email = email[:25] + "..."
        hours = lead.get('opening_hours') or "N/A"
        if len(hours) > 25:
            hours = hours[:22] + "..."
        print(f"{name:<25} | {lead['city']:<12} | {lead['score']:<5} | {phone:<15} | {email:<28} | {hours:<25}")
    print("=" * 120)
    print(f"Total leads in database: {len(leads)}")

def clear_database():
    """Resets the SQLite database tables."""
    db_path = database.DB_PATH
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("Database cleared successfully.")
        except Exception as e:
            print(f"Error clearing database: {str(e)}")
    else:
        print("No database file found to clear.")

def main():
    parser = argparse.ArgumentParser(description="Geoapify Business Lead Generator")
    parser.add_argument("--mock", action="store_true", help="Force run the pipeline with mock data (ignores .env)")
    parser.add_argument("--live", action="store_true", help="Force run the pipeline with live Geoapify API (ignores .env)")
    parser.add_argument("--report", action="store_true", help="Show all leads currently stored in the SQLite database")
    parser.add_argument("--clear-db", action="store_true", help="Reset the database to clear previous runs and duplicates")
    parser.add_argument("--category", type=str, help="Override target search category (e.g. bakery)")
    parser.add_argument("--cities", type=str, help="Override target cities list (comma-separated, e.g. Columbus,Tampa)")
    parser.add_argument("--country", type=str, help="Override target country")
    
    args = parser.parse_args()
    
    # Process commands that don't execute the main search loop
    if args.report:
        print_report()
        return
        
    if args.clear_db:
        clear_database()
        return
        
    # Apply CLI overrides to configuration parameters
    if args.mock:
        config.USE_MOCK_DATA = True
    elif args.live:
        config.USE_MOCK_DATA = False
        
    if args.category:
        config.TARGET_CATEGORY = args.category.strip()
        
    if args.cities:
        config.TARGET_CITIES = [c.strip() for c in args.cities.split(",") if c.strip()]
        
    if args.country:
        config.TARGET_COUNTRY = args.country.strip()
        
    # Run pipeline
    pipeline.run_pipeline()

if __name__ == "__main__":
    main()
