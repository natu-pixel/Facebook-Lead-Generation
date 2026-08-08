# Geoapify Business Lead Generator
An automated pipeline designed to discover high-potential local business leads (e.g. active restaurants, bakeries, cafes) that lack a web presence, calculate a proprietary conversion score, and instantly push qualified lead cards to your Telegram Channel.

Created by **Natnael Teferi**

---

## 🚀 Key Features

* **Dual-Search Pipeline**: Uses the **Geoapify Geocoding API** to automatically resolve city boundaries, followed by the **Geoapify Places API** to retrieve target Point of Interests (POIs).
* **Two-Step API Optimization**: Fetches detailed metadata (website, phone, email, opening hours) using the **Place Details API** *only* for non-duplicate leads to preserve your API quota.
* **OSM Scoring Heuristics**: Evaluates target value (out of 100) using OpenStreetMap markers (e.g., available phone numbers, active opening hours, email listings, and established Wikipedia/Wikidata credentials).
* **Deduplication Engine**: Uses a local **SQLite database** (`leads.db`) to ensure the same lead is never saved or messaged twice.
* **Interactive Telegram Bot Listener**: Run `bot_listener.py` to command the search engine directly from Telegram chat/channels via text command structures (e.g., `/search bakery Charlotte`).
* **Lead Qualification Filters**: Excludes national chain franchises (e.g. McDonald's, Starbucks) and closed/defunct businesses automatically.

---

## 🛠️ Installation & Setup

1. **Clone and navigate to the project directory:**
   ```bash
   cd Facebook-Lead-Generation
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your environment variables:**
   Copy `.env.template` to a new file named `.env`:
   ```bash
   cp .env.template .env
   ```
   Open `.env` and fill in your configurations:
   ```env
   # Geoapify API Configuration
   GEOAPIFY_API_KEY=your_geoapify_api_key_here
   USE_MOCK_DATA=false

   # Targeting Settings
   TARGET_COUNTRY=United States
   TARGET_CITIES=Charlotte,Columbus,Indianapolis,Nashville,Tampa
   TARGET_CATEGORY=restaurant

   # Lead Qualification Criteria
   MIN_REVIEWS=20
   MIN_RATING=4.0
   REQUIRE_WEBSITE=false   # Must be false to find businesses without a website
   REQUIRE_PHONE=true      # Must be true to find businesses with outreach phone numbers

   # Notification Configuration
   NOTIFICATION_CHANNEL=telegram
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_CHAT_ID=-100XXXXXXXXXX   # Your Telegram Channel ID
   ```

---

## 💻 How to Run

You can run the pipeline either through the command line or directly from Telegram.

### Option A: Command Line Interface (CLI)

* **Run Live Search** (using `.env` parameters):
  ```bash
  python run.py --live
  ```
* **Run Live Search with Overrides**:
  ```bash
  python run.py --live --category dentist --cities Tampa
  ```
* **Run Mock Dry-Run** (generates offline test leads):
  ```bash
  python run.py --mock
  ```
* **View Database Lead Reports**:
  ```bash
  python run.py --report
  ```
* **Reset Saved Leads Cache**:
  ```bash
  python run.py --clear-db
  ```

---

### Option B: Interactive Telegram Commands

Start the background bot listener daemon:
```bash
python bot_listener.py
```

Now, you can send commands directly to your bot inside Telegram, and it will push the lead cards into your configured channel:

* **`/search <category> <city>`** — Start a live lead query.
  * *Example:* `/search bakery Charlotte`
* **`/mock <category> <city>`** — Run a dry-run test.
  * *Example:* `/mock restaurant Tampa`
* **`/report`** — Display a summary of saved database leads.
* **`/clear`** — Wipe the SQLite lead cache.
* **`/help`** — Show the available commands.

---

## 📈 Lead Scoring Criteria

| Weight | Parameter | Description |
|---|---|---|
| **Base** | `+40 points` | Initial qualification (operational, no website, has phone). |
| **Outreach Phone** | `+15 points` | Contact phone number available in OSM. |
| **Business Email** | `+10 points` | Contact email address listed in OSM. |
| **Opening Hours** | `+15 points` | Active opening times listed (indicates active business). |
| **Established Entity** | `+10 points` | Wikidata or Wikipedia profiles associated with the place. |
| **Franchise Filter** | `-50 points` | Penalty for matching national chains to keep leads local. |

* Leads scoring **`90+`** are flagged as **`☄️ SUPER HOT LEAD`**.
* Leads scoring **`75-89`** are flagged as **`🔥 HOT LEAD`**.
* Leads scoring **`50-74`** are flagged as **`⚡ WARM LEAD`**.
