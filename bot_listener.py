import time
import requests
import sys
import config
import database
import pipeline
import notifier

# Configure stdout to handle UTF-8 printing without crashing on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def send_telegram_reply(chat_id: int, text: str):
    """Sends a markdown message back to the originating Telegram chat."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to reply to Telegram: {str(e)}")

def process_command(chat_id: int, text: str):
    """Parses and executes commands sent to the Telegram bot."""
    text = text.strip()
    if not text.startswith("/"):
        return
        
    parts = text.split(maxsplit=2)
    command = parts[0].lower()
    
    if command == "/help" or command == "/start":
        help_text = (
            "🤖 *Geoapify Lead Generation Bot Help*\n\n"
            "Here are the commands you can use:\n\n"
            "🔍 `/search <category> <city>` - Search live leads in a city. (e.g. `/search bakery Charlotte`)\n"
            "🧪 `/mock <category> <city>` - Run search in Mock Mode. (e.g. `/mock restaurant Charlotte`)\n"
            "📊 `/report` - Show a summary table of all leads currently in the database.\n"
            "🧹 `/clear` - Clear all leads from the database cache.\n"
            "❓ `/help` - Show this help menu."
        )
        send_telegram_reply(chat_id, help_text)
        
    elif command == "/report":
        leads = database.get_all_leads()
        if not leads:
            send_telegram_reply(chat_id, "📭 No leads found in the database.")
            return
            
        report_lines = ["📊 *Database Lead Report* (Top 10):\n"]
        for lead in leads[:10]:
            phone = lead['phone'] or "No phone"
            score = lead['score']
            badge = "☄️" if score >= 90 else ("🔥" if score >= 75 else "⚡")
            report_lines.append(f"{badge} *{lead['name']}* ({score}/100)\n📍 {lead['city']}\n📞 {phone}\n")
            
        report_lines.append(f"\nTotal leads stored: {len(leads)}")
        send_telegram_reply(chat_id, "\n".join(report_lines))
        
    elif command == "/clear":
        database.init_db()
        conn = database.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DROP TABLE IF EXISTS leads")
            conn.commit()
            database.init_db()
            send_telegram_reply(chat_id, "🧹 SQLite database cache has been successfully reset.")
        except Exception as e:
            send_telegram_reply(chat_id, f"❌ Error resetting database: {str(e)}")
        finally:
            conn.close()
            
    elif command in ("/search", "/mock"):
        if len(parts) < 3:
            send_telegram_reply(
                chat_id, 
                f"⚠️ *Format error*.\nUse: `{command} <category> <city>`\nExample: `{command} bakery Charlotte`"
            )
            return
            
        category = parts[1].strip()
        city = parts[2].strip()
        is_mock = command == "/mock"
        
        mode_str = "Mock" if is_mock else "Live"
        send_telegram_reply(
            chat_id, 
            f"🔍 Starting *{mode_str}* search for category `{category}` in `{city}, {config.TARGET_COUNTRY}`...\nLeads will populate shortly."
        )
        
        # Override configuration temporarily to match Telegram input
        original_mock = config.USE_MOCK_DATA
        original_category = config.TARGET_CATEGORY
        original_cities = config.TARGET_CITIES
        original_channel = config.NOTIFICATION_CHANNEL
        original_chat_id = config.TELEGRAM_CHAT_ID
        
        config.USE_MOCK_DATA = is_mock
        config.TARGET_CATEGORY = category
        config.TARGET_CITIES = [city]
        config.NOTIFICATION_CHANNEL = "telegram"
        
        # If a channel is configured in .env, send the lead cards to the channel.
        # Otherwise, send them directly back to the chat where the command was issued.
        if not original_chat_id:
            config.TELEGRAM_CHAT_ID = str(chat_id)
        else:
            config.TELEGRAM_CHAT_ID = original_chat_id
        
        try:
            database.init_db()
            leads = pipeline.run_pipeline()
            
            if not leads:
                send_telegram_reply(chat_id, f"✅ Search finished. No *new* qualified leads found for `{category}` in `{city}`.")
            else:
                send_telegram_reply(chat_id, f"✅ Search finished! Found *{len(leads)}* new qualified leads in `{city}`.")
        except Exception as e:
            send_telegram_reply(chat_id, f"❌ Pipeline execution error: {str(e)}")
        finally:
            # Restore original configuration
            config.USE_MOCK_DATA = original_mock
            config.TARGET_CATEGORY = original_category
            config.TARGET_CITIES = original_cities
            config.NOTIFICATION_CHANNEL = original_channel
            config.TELEGRAM_CHAT_ID = original_chat_id

def main():
    if not config.TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not configured in .env.")
        return
        
    print(f"🤖 Telegram Bot Interactive Listener Started...")
    print(f"Listening for commands: /search, /mock, /report, /clear, /help")
    print("Press Ctrl+C to stop.")
    
    offset = 0
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
    
    # Run long-polling loops
    while True:
        try:
            params = {"offset": offset, "timeout": 20}
            response = requests.get(url, params=params, timeout=25)
            
            if response.status_code != 200:
                print(f"Telegram polling returned status {response.status_code}")
                time.sleep(5)
                continue
                
            data = response.json()
            updates = data.get("result", [])
            
            for update in updates:
                offset = update["update_id"] + 1
                
                # Check normal chat messages and channel posts
                message = update.get("message") or update.get("channel_post")
                if not message:
                    continue
                    
                chat_id = message["chat"]["id"]
                text = message.get("text", "")
                
                if text.startswith("/"):
                    print(f"Received command: {text} from chat {chat_id}")
                    process_command(chat_id, text)
                    
        except KeyboardInterrupt:
            print("\nShutting down bot listener...")
            break
        except Exception as e:
            print(f"Exception in polling loop: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()
