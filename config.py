import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name, str(default)).lower()
    return val in ("true", "1", "yes", "on", "t")

def get_int_env(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default

def get_float_env(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default

# API Config
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "").strip()
USE_MOCK_DATA = get_bool_env("USE_MOCK_DATA", False)

# Targeting Config
TARGET_COUNTRY = os.getenv("TARGET_COUNTRY", "United States").strip()
TARGET_CITIES_RAW = os.getenv("TARGET_CITIES", "Charlotte,Columbus,Indianapolis,Nashville,Tampa")
TARGET_CITIES = [city.strip() for city in TARGET_CITIES_RAW.split(",") if city.strip()]
TARGET_CATEGORY = os.getenv("TARGET_CATEGORY", "restaurant").strip()

# Filtering Config
MIN_REVIEWS = get_int_env("MIN_REVIEWS", 20)
MIN_RATING = get_float_env("MIN_RATING", 4.0)
REQUIRE_WEBSITE = get_bool_env("REQUIRE_WEBSITE", False)
REQUIRE_PHONE = get_bool_env("REQUIRE_PHONE", True)

# Notification Config
NOTIFICATION_CHANNEL = os.getenv("NOTIFICATION_CHANNEL", "console").strip().lower()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()

# Validation
if not USE_MOCK_DATA and not GEOAPIFY_API_KEY:
    raise ValueError("GEOAPIFY_API_KEY is required in .env unless USE_MOCK_DATA is enabled.")

if NOTIFICATION_CHANNEL == "telegram" and (not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID):
    print("Warning: Telegram channel selected but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing. Falling back to console.")
    NOTIFICATION_CHANNEL = "console"

if NOTIFICATION_CHANNEL == "slack" and not SLACK_WEBHOOK_URL:
    print("Warning: Slack channel selected but SLACK_WEBHOOK_URL is missing. Falling back to console.")
    NOTIFICATION_CHANNEL = "console"
