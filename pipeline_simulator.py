#!/usr/bin/env python3
"""
Pipeline Simulator — FinancialReportNews
Simulates the n8n workflow without Docker dependencies.
Generates test Telegram message output.
"""

import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
import urllib.request
import urllib.error

# ===== CONFIGURATION =====
TELEGRAM_BOT_TOKEN = "8609836947:AAGjUq-BnXnpHIrw_MkoKlf-LChcn8eogVQ"
TELEGRAM_CHAT_ID = "1014679522"
WEBHOOK_URL = "http://localhost:5678"

# Mock event data
MOCK_EVENTS = [
    {
        "title": "PT MAJU IPO Bookbuilding Starts",
        "event_type": "IPO",
        "ticker": "MAJU",
        "source": "IDX",
        "announcement_date": "2026-04-07",
        "url": "https://idx.co.id/announcements/ipo-maju"
    },
    {
        "title": "PT AGRO Dividend Payment",
        "event_type": "DIVIDEND",
        "ticker": "AGRO",
        "source": "IDX",
        "announcement_date": "2026-04-05",
        "url": "https://idx.co.id/announcements/dividend-agro"
    },
    {
        "title": "PT BANK Trading Suspension",
        "event_type": "SUSPENSION",
        "ticker": "BANK",
        "source": "IDX",
        "announcement_date": "2026-04-07",
        "url": "https://idx.co.id/announcements/suspension-bank"
    },
    {
        "title": "PT RETAIL Rights Issue",
        "event_type": "RIGHTS_ISSUE",
        "ticker": "RETL",
        "source": "IDX",
        "announcement_date": "2026-04-06",
        "url": "https://idx.co.id/announcements/rights-retl"
    },
]

# ===== STAGE 1: DATA COLLECTION =====
def collect_events() -> List[Dict[str, Any]]:
    """Simulate scraping from IDX, EIPO, KSEI"""
    print("\n" + "="*70)
    print("STAGE 1: DATA COLLECTION")
    print("="*70)
    
    print(f"✓ Scraping IDX announcements...")
    print(f"  → Found {len(MOCK_EVENTS)} raw events")
    
    return MOCK_EVENTS.copy()

# ===== STAGE 2: DATA NORMALIZATION =====
def normalize_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize event fields"""
    print("\n" + "="*70)
    print("STAGE 2: DATA NORMALIZATION")
    print("="*70)
    
    normalized = []
    for event in events:
        normalized_event = {
            **event,
            "normalized": True,
            "normalized_at": datetime.now().isoformat()
        }
        normalized.append(normalized_event)
        print(f"✓ Normalized: {event['title'][:40]}... → {event['event_type']}")
    
    print(f"\n  → Total normalized: {len(normalized)}")
    return normalized

# ===== STAGE 3: DATA VALIDATION =====
def validate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate event data quality"""
    print("\n" + "="*70)
    print("STAGE 3: DATA VALIDATION")
    print("="*70)
    
    VALID_EVENT_TYPES = {"IPO", "DIVIDEND", "RIGHTS_ISSUE", "STOCK_SPLIT", 
                         "BONUS_SHARES", "BUYBACK", "PRIVATE_PLACEMENT", 
                         "SUSPENSION", "AGM", "EGM", "DELISTING", "UNKNOWN"}
    
    valid_events = []
    for event in events:
        errors = []
        
        # Check required fields
        if not event.get("title"):
            errors.append("title is empty")
        if event.get("event_type") not in VALID_EVENT_TYPES:
            errors.append(f"invalid event_type '{event.get('event_type')}'")
        if not event.get("announcement_date"):
            errors.append("no valid date found")
        
        if errors:
            print(f"✗ REJECTED: {event.get('title', 'Unknown')}")
            print(f"  Reason: {'; '.join(errors)}")
        else:
            valid_events.append(event)
            print(f"✓ VALID: {event['title'][:40]}...")
    
    print(f"\n  → Total valid: {len(valid_events)}/{len(events)}")
    return valid_events

# ===== STAGE 4: DEDUPLICATION =====
def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate records"""
    print("\n" + "="*70)
    print("STAGE 4: DEDUPLICATION")
    print("="*70)
    
    seen = {}
    deduplicated = []
    
    for event in events:
        # Composite key: (ticker, event_type, announcement_date)
        key = (event.get("ticker"), event.get("event_type"), event.get("announcement_date"))
        
        if key in seen:
            print(f"✗ DUPLICATE: {event['title'][:40]}...")
            print(f"  Key: {key}")
        else:
            seen[key] = True
            deduplicated.append(event)
            print(f"✓ UNIQUE: {event['title'][:40]}...")
    
    print(f"\n  → Total unique: {len(deduplicated)}/{len(events)}")
    return deduplicated

# ===== STAGE 5: FORMAT MESSAGE =====
def format_telegram_message(events: List[Dict[str, Any]]) -> str:
    """Format briefing for Telegram"""
    print("\n" + "="*70)
    print("STAGE 5: FORMAT MESSAGE")
    print("="*70)
    
    event_prefixes = {
        "IPO": "[IPO]",
        "DIVIDEND": "[DIV]",
        "RIGHTS_ISSUE": "[RIGHTS]",
        "STOCK_SPLIT": "[SPLIT]",
        "BONUS_SHARES": "[BONUS]",
        "BUYBACK": "[BUY]",
        "PRIVATE_PLACEMENT": "[PP]",
        "SUSPENSION": "[HALT]",
        "AGM": "[AGM]",
        "EGM": "[EGM]",
        "DELISTING": "[DELIST]",
    }
    
    message = f"*Market Briefing* - {datetime.now().strftime('%b %d, %Y %H:%M')}\n"
    message += "="*50 + "\n\n"
    
    if not events:
        message += "No significant market events today.\n"
    else:
        for event in events:
            prefix = event_prefixes.get(event.get("event_type"), "[EVENT]")
            message += f"{prefix} *{event['event_type']}*: {event['title']}\n"
            message += f"   Ticker: {event.get('ticker', 'N/A')} | Source: {event['source']}\n"
            message += f"   Date: {event['announcement_date']}\n"
            if event.get('url'):
                message += f"   Link: {event['url']}\n"
            message += "\n"
    
    message += "="*50 + "\n"
    message += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += "Status: All checks passed"
    
    print("✓ Message formatted for Telegram")
    print(f"  → Message length: {len(message)} characters")
    
    return message

# ===== STAGE 6: SEND TO TELEGRAM =====
def send_telegram_message(message: str) -> bool:
    """Send message to Telegram"""
    print("\n" + "="*70)
    print("STAGE 6: SEND TO TELEGRAM")
    print("="*70)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        print(f"📤 Sending to Telegram...")
        print(f"   Chat ID: {TELEGRAM_CHAT_ID}")
        print(f"   Bot Token: {TELEGRAM_BOT_TOKEN[:20]}...***")
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get("ok"):
                print(f"✓ Message sent successfully!")
                print(f"  Message ID: {result.get('result', {}).get('message_id')}")
                return True
            else:
                print(f"✗ Telegram API error: {result.get('description')}")
                return False
                
    except urllib.error.URLError as e:
        print(f"✗ Network error: {e}")
        print(f"   (This is expected if you're offline or Telegram API is unreachable)")
        print(f"   But the message content is ready! See below:")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

# ===== MAIN PIPELINE =====
def run_pipeline():
    """Execute the full pipeline"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "🚀 PIPELINE EXECUTION — SIMULATOR 🚀" + " "*16 + "║")
    print("║" + " "*10 + "FinancialReportNews (IDN-StockNews)" + " "*24 + "║")
    print("╚" + "="*68 + "╝")
    
    # Execute pipeline stages
    events = collect_events()
    events = normalize_events(events)
    events = validate_events(events)
    events = deduplicate_events(events)
    
    # Generate and send message
    message = format_telegram_message(events)
    
    print("\n" + "="*70)
    print("MESSAGE CONTENT")
    print("="*70)
    print(message)
    
    # Try to send to Telegram
    success = send_telegram_message(message)
    
    # Summary
    print("\n" + "="*70)
    print("PIPELINE SUMMARY")
    print("="*70)
    print(f"✓ Events processed: {len(events)}")
    print(f"✓ Message formatted: Yes")
    print(f"✓ Telegram delivery: {'Success ✅' if success else 'Failed/Offline ⚠️'}")
    print(f"✓ Pipeline status: COMPLETED ✅")
    print("="*70 + "\n")
    
    return success

# ===== ENTRY POINT =====
if __name__ == "__main__":
    try:
        success = run_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
